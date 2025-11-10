# utils.py
import pandas as pd
import numpy as np
import re, math
from datetime import datetime

# ==== Parsowanie i normalizacja danych ====

def detect_week_cols(columns):
    kw_cols = []
    for c in columns:
        if isinstance(c, str):
            s = c.strip()
            if re.match(r'^KW\s*\d{1,2}/\d{2}$', s):
                kw_cols.append(c)
    # fallback (inne formaty)
    for c in columns:
        if isinstance(c, str):
            s = c.strip()
            if re.match(r'^\d{4}[-_/]W?\d{1,2}$', s) or re.match(r'^\d{1,2}[-_/]\d{4}$', s):
                kw_cols.append(c)
    return list(dict.fromkeys(kw_cols))

def kw_from_date(date):
    if pd.isna(date): return None
    y, w, _ = date.isocalendar()
    return f"KW {int(w):02d}/{str(y)[-2:]}"

def all_ordered_weeks(weeks):
    def parse_kw(s):
        m = re.match(r'KW\s*(\d{1,2})/(\d{2,4})', s)
        if not m:
            return (9999,99)
        week = int(m.group(1))
        yy = m.group(2)
        year = int(yy) if len(yy)==4 else (2000+int(yy))
        return (year, week)
    return sorted(set(weeks), key=parse_kw)

def normalize_forecast(forecast_df):
    cols = list(forecast_df.columns)
    week_cols = [c for c in cols if isinstance(c,str) and re.match(r'^KW\s*\d{1,2}/\d{2}$', c.strip())]
    if not week_cols:
        week_cols = detect_week_cols(cols)
    df = forecast_df.copy()
    if 'Materialnummer' not in df.columns:
        for alt in ['numer indeksu','Material number','Material','Index','IndexNo','Materialnr','Materialnummer ']:
            if alt in df.columns:
                df = df.rename(columns={alt:'Materialnummer'})
                break
    df['Materialnummer'] = df['Materialnummer'].astype(str)
    for c in week_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(' ', '').str.replace(',','.'), errors='coerce').fillna(0.0)
    grouped = df.groupby('Materialnummer')[week_cols].sum()
    forecast_map = {}
    for mat, row in grouped.iterrows():
        inner = {c.strip(): float(row[c]) for c in week_cols if float(row[c])!=0.0}
        if inner:
            forecast_map[mat] = inner
    all_weeks = all_ordered_weeks(week_cols)
    return forecast_map, all_weeks

def normalize_stock(stock_df):
    df = stock_df.copy()
    # Mapowanie kolumn PL -> standard
    ren = {}
    for c in df.columns:
        low = c.lower()
        if low == 'numer indeksu' or low=='materialnummer':
            ren[c] = 'Materialnummer'
        elif low=='itemcode':
            ren[c] = 'ItemCode'
        elif 'magazynie' in low:
            ren[c] = 'Stock'
        elif 'data dostawy' in low:
            ren[c] = 'DeliveryDate'
        elif 'zlecenia' in low:
            ren[c] = 'OrderDate'
        elif 'zamówione' in low:
            ren[c] = 'Ordered'
        elif 'potwierdzone' in low:
            ren[c] = 'Confirmed'
        elif low=='nazwa':
            ren[c] = 'Type'
        elif 'dostępne' in low:
            ren[c] = 'Available'
        elif 'docnum' in low:
            ren[c] = 'DocNum'
        elif low.strip()=='jm':
            ren[c] = 'UoM'
    df = df.rename(columns=ren)
    # Typy
    for col in ['Materialnummer','ItemCode','Type','UoM']:
        if col in df.columns:
            df[col] = df[col].astype(str)
    for col in ['Stock','Ordered','Confirmed','Available']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    for col in ['DeliveryDate','OrderDate']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
    # Startowy stan
    init_stock = df.groupby('Materialnummer')['Stock'].max().to_dict() if 'Stock' in df.columns and 'Materialnummer' in df.columns else {}
    # Map Material -> ItemCode
    itemcode_map = df.groupby('Materialnummer')['ItemCode'].agg(lambda s: s.mode().iat[0] if not s.mode().empty else None).to_dict() if 'ItemCode' in df.columns else {}
    # Dostawy tygodniowe
    if 'DeliveryDate' in df.columns:
        df['KW'] = df['DeliveryDate'].apply(kw_from_date)
    incoming = []
    for _, r in df.iterrows():
        mat = r.get('Materialnummer')
        kw = r.get('KW')
        typ = r.get('Type','').upper() if isinstance(r.get('Type'), str) else ''
        val = 0.0
        if typ == 'ZP':
            val = float(r.get('Ordered',0.0))
        elif typ in ('ZS','OR','PO'):
            val = float(r.get('Confirmed',0.0))
        else:
            conf = float(r.get('Confirmed',0.0))
            ordv = float(r.get('Ordered',0.0))
            val = conf if conf>0 else ordv
        if pd.notna(kw) and mat and val and val>0:
            incoming.append((mat, kw, val))
    inc_df = pd.DataFrame(incoming, columns=['Materialnummer','KW','Qty'])
    incoming_map = {}
    if not inc_df.empty:
        inc_df = inc_df.groupby(['Materialnummer','KW'])['Qty'].sum().reset_index()
        for mat, group in inc_df.groupby('Materialnummer'):
            incoming_map[mat] = {kw: float(qty) for kw, qty in zip(group['KW'], group['Qty'])}
    return init_stock, incoming_map, itemcode_map

def union_weeks(*maps):
    weeks = set()
    for m in maps:
        for inner in m.values():
            weeks.update(inner.keys())
    return all_ordered_weeks(weeks)

# ==== Symulacje ====

def simulate_item(initial_stock, forecast_dict, incoming_dict, week_sequence):
    stock = float(initial_stock or 0.0)
    detail = []
    min_stock = stock
    first_shortage_week = None
    for kw in week_sequence:
        demand = float(forecast_dict.get(kw, 0.0))
        income = float(incoming_dict.get(kw, 0.0))
        stock = stock + income - demand
        if stock < min_stock:
            min_stock = stock
        shortage = -stock if stock < 0 else 0.0
        if shortage>0 and first_shortage_week is None:
            first_shortage_week = kw
        detail.append({'KW': kw, 'Forecast': demand, 'Incoming': income, 'StockAfter': stock, 'Shortage': shortage})
    return detail, min_stock, first_shortage_week

def simulate_all(init_stock_map, forecast_map, incoming_map, week_sequence):
    results = {}
    for mat in sorted(set(list(forecast_map.keys()) + list(init_stock_map.keys()) + list(incoming_map.keys()))):
        init = float(init_stock_map.get(mat, 0.0))
        fdict = forecast_map.get(mat, {})
        idict = incoming_map.get(mat, {})
        detail, min_stock, first_short = simulate_item(init, fdict, idict, week_sequence)
        total_forecast = sum(fdict.get(kw,0.0) for kw in week_sequence)
        total_incoming = sum(idict.get(kw,0.0) for kw in week_sequence)
        results[mat] = {
            'InitialStock': init,
            'TotalForecast': total_forecast,
            'TotalIncoming': total_incoming,
            'MinStock': min_stock,
            'FirstShortageWeek': first_short,
            'Detail': detail
        }
    return results

def build_summary(results, itemcode_map=None, batch_map=None):
    rows = []
    for mat, data in results.items():
        required = max(0.0, -data['MinStock'])
        b = batch_map.get(mat) if batch_map else None
        proposed = math.ceil(required / b) * b if (b and b>0 and required>0) else required
        rows.append({
            'Materialnummer': mat,
            'ItemCode': (itemcode_map or {}).get(mat, None),
            'StartStock': round(float(data['InitialStock']),2),
            'SumForecast': round(float(data['TotalForecast']),2),
            'SumIncoming': round(float(data['TotalIncoming']),2),
            'MinStock': round(float(data['MinStock']),2),
            'RequiredReplenishment': round(required,2),
            'ProposedProduction': round(proposed,2),
            'BatchSize': b if b else None,
            'FirstShortageWeek': data['FirstShortageWeek'],
            'Status': 'DEFICYT' if required>0 else 'OK'
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(['Status','ProposedProduction'], ascending=[True, False]).reset_index(drop=True)
    return df

def compute_batch_sizes(stock_df):
    batch_map = {}
    if stock_df is None or stock_df.empty:
        return batch_map
    df = stock_df.copy()
    if 'nazwa' in df.columns and 'Zamówione' in df.columns and 'numer indeksu' in df.columns:
        for mat, group in df.groupby('numer indeksu'):
            vals = [int(v) for v in group.loc[group['nazwa'].str.upper()=='ZP', 'Zamówione'] if v>0]
            if len(vals)>=1:
                g = 0
                for v in vals:
                    g = math.gcd(g, v)
                if g < 10 and len(vals) > 0:
                    from collections import Counter
                    g = Counter(vals).most_common(1)[0][0]
                batch_map[str(mat)] = g if g>0 else None
    return batch_map

def simulate_with_extra(results, week_sequence, extra_map):
    tobe = {}
    for mat, data in results.items():
        base_forecast = {row['KW']: row['Forecast'] for row in data['Detail']}
        base_incoming = {row['KW']: row['Incoming'] for row in data['Detail']}
        extra = extra_map.get(mat)
        if extra:
            kw, qty = extra
            base_incoming[kw] = base_incoming.get(kw,0.0) + qty
        detail, min_stock, first_short = simulate_item(data['InitialStock'], base_forecast, base_incoming, week_sequence)
        tobe[mat] = {
            'Detail': detail,
            'MinStock': min_stock,
            'FirstShortageWeek': first_short
        }
    return tobe

def export_report(summary_df, results, tobe, path):
    with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        ws = writer.sheets['Summary']
        ws.autofilter(0,0, summary_df.shape[0], summary_df.shape[1]-1)
        # Szczegóły dla każdego indeksu (AS-IS i TO-BE)
        for mat, data in results.items():
            df_as_is = pd.DataFrame(data['Detail'])
            df_to_be = pd.DataFrame(tobe.get(mat,{}).get('Detail',[]))
            # StockBefore (czytelność)
            def compute_before(initial, detail):
                before = []
                stock = initial
                for row in detail:
                    before.append(stock)
                    stock = stock + row['Incoming'] - row['Forecast']
                return before
            df_as_is.insert(1, 'StockBefore', compute_before(data['InitialStock'], data['Detail']))
            if not df_to_be.empty:
                df_to_be.insert(1, 'StockBefore', compute_before(data['InitialStock'], tobe[mat]['Detail']))
            # Arkusz
            sn = str(mat)[:31]
            base_sn = sn
            i = 1
            while sn in writer.sheets:
                sn = (base_sn[:28] + f"_{i}")[:31]
                i += 1
            df_as_is.to_excel(writer, sheet_name=sn, index=False, startrow=0)
            ws2 = writer.sheets[sn]
            ws2.write(0, len(df_as_is.columns)+1, '--- TO-BE ---')
            if not df_to_be.empty:
                df_to_be.to_excel(writer, sheet_name=sn, index=False, startrow=0, startcol=len(df_as_is.columns)+2)
    return path
