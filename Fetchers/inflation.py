#!/usr/bin/env python3
import json
import requests
import yfinance as yf
import pandas as pd
import investpy
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

FRED_API_KEY = "f4e191ba7125013521aa29b4fbe962ee"
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"
OUTPUT_PATH = "Fetchers/jsons/fundamentals_data.json"

CB_KEYWORDS = [
    'FOMC', 'Minutes', 'Fed', 'Interest Rate Decision',
    'ECB', 'Monetary Policy', 'BOJ', 'BOE', 'MPC',
    'Federal Reserve', 'Bank of Japan', 'Bank of England'
]

def fetch_fred_series_range(series_id: str, start_date: str) -> Optional[List[Dict]]:
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "asc",
        "observation_start": start_date
    }
    
    try:
        response = requests.get(FRED_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        observations = data.get("observations", [])
        results = []
        for obs in observations:
            try:
                val = float(obs["value"])
                results.append({"date": obs["date"], "value": round(val, 2)})
            except (ValueError, KeyError):
                continue
        return results if results else None
    except Exception:
        return None

def fetch_monthly_indicator(series_id: str, name: str) -> Dict:
    start_date = (datetime.now() - relativedelta(months=3)).strftime("%Y-%m-%d")
    data = fetch_fred_series_range(series_id, start_date)
    
    result = {}
    
    if data and len(data) >= 1:
        end_date = data[-1]["date"]
        result[name] = [{"date": d["date"], "value": d["value"]} for d in data]
        result[f"{name}_END_DATE"] = end_date
    else:
        result[name] = None
        result[f"{name}_END_DATE"] = None
    
    return result

def fetch_daily_previous_month(series_id: str, name: str) -> Dict:
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = fetch_fred_series_range(series_id, start_date)
    
    result = {}
    
    if data and len(data) >= 1:
        end_date = data[-1]["date"]
        result[name] = [{"date": d["date"], "value": d["value"]} for d in data]
        result[f"{name}_END_DATE"] = end_date
    else:
        result[name] = None
        result[f"{name}_END_DATE"] = None
    
    return result

def fetch_weekly_previous_month(series_id: str, name: str) -> Dict:
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = fetch_fred_series_range(series_id, start_date)
    
    result = {}
    
    if data and len(data) >= 1:
        end_date = data[-1]["date"]
        result[name] = [{"date": d["date"], "value": d["value"]} for d in data]
        result[f"{name}_END_DATE"] = end_date
    else:
        result[name] = None
        result[f"{name}_END_DATE"] = None
    
    return result

def fetch_real_interest_rate() -> Dict:
    start_date = (datetime.now() - relativedelta(months=14)).strftime("%Y-%m-%d")
    treasury_data = fetch_fred_series_range("DGS10", start_date)
    cpi_data = fetch_fred_series_range("CPIAUCSL", start_date)
    
    result = {}
    
    if treasury_data and cpi_data and len(treasury_data) >= 1 and len(cpi_data) >= 13:
        current_10y = treasury_data[-1]["value"]
        
        cpi_values = [d["value"] for d in cpi_data]
        current_cpi = cpi_values[-1]
        prev_year_cpi = cpi_values[-13]
        cpi_yoy_curr = ((current_cpi - prev_year_cpi) / prev_year_cpi) * 100
        
        real_rate_curr = current_10y - cpi_yoy_curr
        result["REAL_RATE"] = round(real_rate_curr, 2)
        result["REAL_RATE_END_DATE"] = treasury_data[-1]["date"]
    else:
        result["REAL_RATE"] = None
        result["REAL_RATE_END_DATE"] = None
    
    return result

def fetch_gold_etf_flows() -> Dict:
    result = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    try:
        gld = yf.Ticker("GLD")
        gld_hist = gld.history(start=start_date, end=end_date)
        
        if not gld_hist.empty:
            gld_30d = [{"date": idx.strftime("%Y-%m-%d"), "close": round(row["Close"], 2), "volume": int(row["Volume"])} 
                       for idx, row in gld_hist.iterrows()]
            result["GLD"] = gld_30d
            result["GLD_END_DATE"] = gld_hist.index[-1].strftime("%Y-%m-%d")
        else:
            result["GLD"] = None
            result["GLD_END_DATE"] = None
    except Exception:
        result["GLD"] = None
        result["GLD_END_DATE"] = None
    
    try:
        iau = yf.Ticker("IAU")
        iau_hist = iau.history(start=start_date, end=end_date)
        
        if not iau_hist.empty:
            iau_30d = [{"date": idx.strftime("%Y-%m-%d"), "close": round(row["Close"], 2), "volume": int(row["Volume"])} 
                       for idx, row in iau_hist.iterrows()]
            result["IAU"] = iau_30d
            result["IAU_END_DATE"] = iau_hist.index[-1].strftime("%Y-%m-%d")
        else:
            result["IAU"] = None
            result["IAU_END_DATE"] = None
    except Exception:
        result["IAU"] = None
        result["IAU_END_DATE"] = None
    
    return result

def fetch_treasury_curve() -> Dict:
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    result = {}
    
    data_2y = fetch_fred_series_range("DGS2", start_date)
    if data_2y:
        result["TREASURY_2Y"] = data_2y
        result["TREASURY_2Y_END_DATE"] = data_2y[-1]["date"]
    else:
        result["TREASURY_2Y"] = None
        result["TREASURY_2Y_END_DATE"] = None
    
    data_5y = fetch_fred_series_range("DGS5", start_date)
    if data_5y:
        result["TREASURY_5Y"] = data_5y
        result["TREASURY_5Y_END_DATE"] = data_5y[-1]["date"]
    else:
        result["TREASURY_5Y"] = None
        result["TREASURY_5Y_END_DATE"] = None
    
    data_30y = fetch_fred_series_range("DGS30", start_date)
    if data_30y:
        result["TREASURY_30Y"] = data_30y
        result["TREASURY_30Y_END_DATE"] = data_30y[-1]["date"]
    else:
        result["TREASURY_30Y"] = None
        result["TREASURY_30Y_END_DATE"] = None
    
    return result

def fetch_central_bank_minutes() -> Dict:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    from_str = start_date.strftime('%d/%m/%Y')
    to_str = end_date.strftime('%d/%m/%Y')
    
    try:
        df = investpy.economic_calendar(
            countries=['united states', 'euro zone', 'japan', 'united kingdom'],
            importances=['high'],
            from_date=from_str,
            to_date=to_str
        )
        
        if df.empty:
            return {"CENTRAL_BANK_EVENTS": None}
        
        cb_events = []
        for _, row in df.iterrows():
            event_name = str(row.get('event', ''))
            
            if any(keyword.lower() in event_name.lower() for keyword in CB_KEYWORDS):
                cb_events.append({
                    'date': str(row.get('date', '')),
                    'time': str(row.get('time', '')),
                    'currency': str(row.get('currency', '')),
                    'event': event_name,
                    'actual': str(row.get('actual', '')) if pd.notna(row.get('actual')) else '',
                    'forecast': str(row.get('forecast', '')) if pd.notna(row.get('forecast')) else '',
                    'previous': str(row.get('previous', '')) if pd.notna(row.get('previous')) else ''
                })
        
        cb_events.sort(key=lambda x: x['date'], reverse=True)
        cb_events = cb_events[:2]
        
        return {"CENTRAL_BANK_EVENTS": cb_events if cb_events else None}
        
    except Exception:
        return {"CENTRAL_BANK_EVENTS": None}

def fetch_gpr_index() -> Dict:
    try:
        df = pd.read_excel(GPR_URL, sheet_name=0)
        
        if df.empty:
            return {
                "GPR_PREVIOUS": None,
                "GPR_ACTUAL": None,
                "GPR_CHANGE_PCT": None
            }
        
        last_two = df.tail(2)
        
        gpr_col = None
        for col in df.columns:
            if 'GPR' in str(col).upper() and 'THREAT' not in str(col).upper() and 'ACT' not in str(col).upper():
                gpr_col = col
                break
        
        if gpr_col is None:
            return {
                "GPR_PREVIOUS": None,
                "GPR_ACTUAL": None,
                "GPR_CHANGE_PCT": None
            }
        
        values = last_two[gpr_col].tolist()
        
        if len(values) >= 2:
            gpr_previous = round(float(values[0]), 2)
            gpr_actual = round(float(values[1]), 2)
            gpr_change_pct = round(((gpr_actual - gpr_previous) / gpr_previous) * 100, 2)
            
            return {
                "GPR_PREVIOUS": gpr_previous,
                "GPR_ACTUAL": gpr_actual,
                "GPR_CHANGE_PCT": gpr_change_pct
            }
        else:
            return {
                "GPR_PREVIOUS": None,
                "GPR_ACTUAL": None,
                "GPR_CHANGE_PCT": None
            }
            
    except Exception:
        return {
            "GPR_PREVIOUS": None,
            "GPR_ACTUAL": None,
            "GPR_CHANGE_PCT": None
        }

def calculate_etf_flows() -> Dict:
    result = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    try:
        gld = yf.Ticker("GLD")
        gld_hist = gld.history(start=start_date, end=end_date)
        
        if not gld_hist.empty and len(gld_hist) >= 30:
            volumes = gld_hist['Volume'].tolist()
            vol_7d_recent = sum(volumes[-7:]) / 7
            vol_7d_prior = sum(volumes[-14:-7]) / 7
            vol_30d_recent = sum(volumes[-30:]) / 30
            vol_30d_prior = sum(volumes[-60:-30]) / 30 if len(volumes) >= 60 else vol_30d_recent
            
            result["GLD_7D_FLOW_PCT"] = round(((vol_7d_recent - vol_7d_prior) / vol_7d_prior) * 100, 2) if vol_7d_prior > 0 else 0
            result["GLD_30D_FLOW_PCT"] = round(((vol_30d_recent - vol_30d_prior) / vol_30d_prior) * 100, 2) if vol_30d_prior > 0 else 0
            result["GLD_CURRENT_PRICE"] = round(gld_hist['Close'].tolist()[-1], 2)
        else:
            result["GLD_7D_FLOW_PCT"] = None
            result["GLD_30D_FLOW_PCT"] = None
            result["GLD_CURRENT_PRICE"] = None
    except:
        result["GLD_7D_FLOW_PCT"] = None
        result["GLD_30D_FLOW_PCT"] = None
        result["GLD_CURRENT_PRICE"] = None
    
    try:
        iau = yf.Ticker("IAU")
        iau_hist = iau.history(start=start_date, end=end_date)
        
        if not iau_hist.empty and len(iau_hist) >= 30:
            volumes = iau_hist['Volume'].tolist()
            vol_7d_recent = sum(volumes[-7:]) / 7
            vol_7d_prior = sum(volumes[-14:-7]) / 7
            vol_30d_recent = sum(volumes[-30:]) / 30
            vol_30d_prior = sum(volumes[-60:-30]) / 30 if len(volumes) >= 60 else vol_30d_recent
            
            result["IAU_7D_FLOW_PCT"] = round(((vol_7d_recent - vol_7d_prior) / vol_7d_prior) * 100, 2) if vol_7d_prior > 0 else 0
            result["IAU_30D_FLOW_PCT"] = round(((vol_30d_recent - vol_30d_prior) / vol_30d_prior) * 100, 2) if vol_30d_prior > 0 else 0
            result["IAU_CURRENT_PRICE"] = round(iau_hist['Close'].tolist()[-1], 2)
        else:
            result["IAU_7D_FLOW_PCT"] = None
            result["IAU_30D_FLOW_PCT"] = None
            result["IAU_CURRENT_PRICE"] = None
    except:
        result["IAU_7D_FLOW_PCT"] = None
        result["IAU_30D_FLOW_PCT"] = None
        result["IAU_CURRENT_PRICE"] = None
    
    return result

def collect_fundamentals() -> Dict:
    fundamentals = {
        "collection_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "FRED + Investing.com + Iacoviello GPR + Yahoo Finance"
    }
    
    fundamentals["DAILY"] = {}
    fundamentals["DAILY"].update(fetch_daily_previous_month("DGS10", "TREASURY_10Y"))
    fundamentals["DAILY"].update(fetch_daily_previous_month("BAMLH0A0HYM2", "HY_CREDIT_SPREAD"))
    fundamentals["DAILY"].update(fetch_gold_etf_flows())
    fundamentals["DAILY"].update(fetch_treasury_curve())
    
    fundamentals["WEEKLY"] = {}
    fundamentals["WEEKLY"].update(fetch_weekly_previous_month("ICSA", "JOBLESS_CLAIMS"))
    
    fundamentals["MONTHLY"] = {}
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("CPIAUCSL", "CPI"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("PCEPI", "PCE"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("PPIACO", "PPI"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("UNRATE", "UNEMPLOYMENT"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("PAYEMS", "NFP"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("FEDFUNDS", "FEDFUNDS"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("M2SL", "M2_MONEY_SUPPLY"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("RSAFS", "RETAIL_SALES"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("INDPRO", "INDUSTRIAL_PROD"))
    fundamentals["MONTHLY"].update(fetch_monthly_indicator("HOUST", "HOUSING_STARTS"))
    
    fundamentals["CALCULATED"] = {}
    fundamentals["CALCULATED"].update(fetch_real_interest_rate())
    fundamentals["CALCULATED"].update(fetch_central_bank_minutes())
    fundamentals["CALCULATED"].update(fetch_gpr_index())
    fundamentals["CALCULATED"].update(calculate_etf_flows())
    
    return fundamentals

def main():
    fundamentals = collect_fundamentals()
    
    with open(OUTPUT_PATH, "w") as f:
        json.dump(fundamentals, f, indent=2)
    
    print("Done")

if __name__ == "__main__":
    main()