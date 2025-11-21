#!/usr/bin/env python3
import json
import requests
import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

FRED_API_KEY = "f4e191ba7125013521aa29b4fbe962ee"
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

def fetch_fred_series_range(series_id: str, start_date: str) -> Optional[List[Dict]]:
    """Fetch FRED series data from a start date to present."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
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
    """Fetch current and previous month for monthly indicators."""
    start_date = (datetime.now() - relativedelta(months=3)).strftime("%Y-%m-%d")
    data = fetch_fred_series_range(series_id, start_date)
    
    result = {}
    
    if data and len(data) >= 2:
        result[f"{name}_CURR"] = data[0]["value"]
        result[f"{name}_PREV"] = data[1]["value"]
        result[f"{name}_CURR_DATE"] = data[0]["date"]
        result[f"{name}_PREV_DATE"] = data[1]["date"]
    elif data and len(data) == 1:
        result[f"{name}_CURR"] = data[0]["value"]
        result[f"{name}_CURR_DATE"] = data[0]["date"]
    else:
        result[f"{name}_CURR"] = None
        result[f"{name}_PREV"] = None
    
    return result

def fetch_daily_previous_month(series_id: str, name: str) -> Dict:
    """Fetch all values from previous 30 days for daily frequency indicators."""
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = fetch_fred_series_range(series_id, start_date)
    
    result = {}
    
    if data and len(data) >= 2:
        result[f"{name}_CURR"] = data[0]["value"]
        result[f"{name}_PREV"] = data[1]["value"]
        result[f"{name}_CURR_DATE"] = data[0]["date"]
        result[f"{name}_PREV_DATE"] = data[1]["date"]
        result[f"{name}_LAST_30_DAYS"] = [{"date": d["date"], "value": d["value"]} for d in data]
    elif data and len(data) == 1:
        result[f"{name}_CURR"] = data[0]["value"]
        result[f"{name}_CURR_DATE"] = data[0]["date"]
        result[f"{name}_LAST_30_DAYS"] = [{"date": data[0]["date"], "value": data[0]["value"]}]
    else:
        result[f"{name}_CURR"] = None
        result[f"{name}_PREV"] = None
        result[f"{name}_LAST_30_DAYS"] = None
    
    return result

def fetch_weekly_previous_month(series_id: str, name: str) -> Dict:
    """Fetch all values from previous 30 days for weekly frequency indicators."""
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = fetch_fred_series_range(series_id, start_date)
    
    result = {}
    
    if data and len(data) >= 2:
        result[f"{name}_CURR"] = data[0]["value"]
        result[f"{name}_PREV"] = data[1]["value"]
        result[f"{name}_CURR_DATE"] = data[0]["date"]
        result[f"{name}_PREV_DATE"] = data[1]["date"]
        result[f"{name}_LAST_30_DAYS"] = [{"date": d["date"], "value": d["value"]} for d in data]
    elif data and len(data) == 1:
        result[f"{name}_CURR"] = data[0]["value"]
        result[f"{name}_CURR_DATE"] = data[0]["date"]
        result[f"{name}_LAST_30_DAYS"] = [{"date": data[0]["date"], "value": data[0]["value"]}]
    else:
        result[f"{name}_CURR"] = None
        result[f"{name}_PREV"] = None
        result[f"{name}_LAST_30_DAYS"] = None
    
    return result

def fetch_real_interest_rate() -> Dict:
    """Calculate real interest rate (Treasury 10Y - CPI YoY)."""
    start_date = (datetime.now() - relativedelta(months=14)).strftime("%Y-%m-%d")
    treasury_data = fetch_fred_series_range("DGS10", start_date)
    cpi_data = fetch_fred_series_range("CPIAUCSL", start_date)
    
    result = {}
    
    if treasury_data and cpi_data and len(treasury_data) >= 1 and len(cpi_data) >= 13:
        current_10y = treasury_data[0]["value"]
        
        cpi_values = [d["value"] for d in cpi_data]
        current_cpi = cpi_values[0]
        prev_year_cpi = cpi_values[12]
        cpi_yoy_curr = ((current_cpi - prev_year_cpi) / prev_year_cpi) * 100
        
        real_rate_curr = current_10y - cpi_yoy_curr
        result["REAL_RATE_CURR"] = round(real_rate_curr, 2)
    else:
        result["REAL_RATE_CURR"] = None
    
    return result

def fetch_gold_etf_flows() -> Dict:
    """Fetch GLD and IAU net asset values as proxy for institutional flows."""
    result = {}
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        gld = yf.Ticker("GLD")
        gld_hist = gld.history(start=start_date, end=end_date)
        
        if not gld_hist.empty:
            gld_latest = gld_hist.iloc[-1]
            gld_prev = gld_hist.iloc[-2] if len(gld_hist) > 1 else None
            
            result["GLD_PRICE_CURR"] = round(gld_latest["Close"], 2)
            result["GLD_VOLUME_CURR"] = int(gld_latest["Volume"])
            result["GLD_DATE_CURR"] = gld_latest.name.strftime("%Y-%m-%d")
            
            if gld_prev is not None:
                result["GLD_PRICE_PREV"] = round(gld_prev["Close"], 2)
                result["GLD_VOLUME_PREV"] = int(gld_prev["Volume"])
                result["GLD_DATE_PREV"] = gld_prev.name.strftime("%Y-%m-%d")
            
            gld_30d = [{"date": idx.strftime("%Y-%m-%d"), "close": round(row["Close"], 2), "volume": int(row["Volume"])} 
                       for idx, row in gld_hist.iterrows()]
            result["GLD_LAST_30_DAYS"] = gld_30d
    except Exception:
        result["GLD_PRICE_CURR"] = None
        result["GLD_VOLUME_CURR"] = None
    
    try:
        iau = yf.Ticker("IAU")
        iau_hist = iau.history(start=start_date, end=end_date)
        
        if not iau_hist.empty:
            iau_latest = iau_hist.iloc[-1]
            iau_prev = iau_hist.iloc[-2] if len(iau_hist) > 1 else None
            
            result["IAU_PRICE_CURR"] = round(iau_latest["Close"], 2)
            result["IAU_VOLUME_CURR"] = int(iau_latest["Volume"])
            result["IAU_DATE_CURR"] = iau_latest.name.strftime("%Y-%m-%d")
            
            if iau_prev is not None:
                result["IAU_PRICE_PREV"] = round(iau_prev["Close"], 2)
                result["IAU_VOLUME_PREV"] = int(iau_prev["Volume"])
                result["IAU_DATE_PREV"] = iau_prev.name.strftime("%Y-%m-%d")
            
            iau_30d = [{"date": idx.strftime("%Y-%m-%d"), "close": round(row["Close"], 2), "volume": int(row["Volume"])} 
                       for idx, row in iau_hist.iterrows()]
            result["IAU_LAST_30_DAYS"] = iau_30d
    except Exception:
        result["IAU_PRICE_CURR"] = None
        result["IAU_VOLUME_CURR"] = None
    
    return result

def collect_fundamentals() -> Dict:
    """Collect all fundamental economic indicators."""
    print("Collecting fundamental economic data...")
    
    fundamentals = {
        "collection_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "Federal Reserve Economic Data (FRED) + Yahoo Finance"
    }
    
    # ===== DAILY FREQUENCY INDICATORS =====
    print("\n[DAILY FREQUENCY]")
    fundamentals.update(fetch_daily_previous_month("DGS10", "TREASURY_10Y"))
    fundamentals.update(fetch_daily_previous_month("BAMLH0A0HYM2", "HY_CREDIT_SPREAD"))
    fundamentals.update(fetch_gold_etf_flows())
    
    # ===== WEEKLY FREQUENCY INDICATORS =====
    print("[WEEKLY FREQUENCY]")
    fundamentals.update(fetch_weekly_previous_month("ICSA", "JOBLESS_CLAIMS"))
    
    # ===== MONTHLY FREQUENCY INDICATORS =====
    print("[MONTHLY FREQUENCY]")
    fundamentals.update(fetch_monthly_indicator("CPIAUCSL", "CPI"))
    fundamentals.update(fetch_monthly_indicator("PCEPI", "PCE"))
    fundamentals.update(fetch_monthly_indicator("PPIACO", "PPI"))
    fundamentals.update(fetch_monthly_indicator("UNRATE", "UNEMPLOYMENT"))
    fundamentals.update(fetch_monthly_indicator("PAYEMS", "NFP"))
    fundamentals.update(fetch_monthly_indicator("FEDFUNDS", "FEDFUNDS"))
    fundamentals.update(fetch_monthly_indicator("M2SL", "M2_MONEY_SUPPLY"))
    fundamentals.update(fetch_monthly_indicator("RSAFS", "RETAIL_SALES"))
    fundamentals.update(fetch_monthly_indicator("INDPRO", "INDUSTRIAL_PROD"))
    fundamentals.update(fetch_monthly_indicator("HOUST", "HOUSING_STARTS"))
    
    # ===== CALCULATED INDICATORS =====
    print("[CALCULATED INDICATORS]")
    fundamentals.update(fetch_real_interest_rate())
    
    print("\nCollection complete.")
    
    return fundamentals

def main():
    print("=" * 60)
    print("FUNDAMENTALS DATA COLLECTION")
    print("=" * 60)
    
    fundamentals = collect_fundamentals()
    
    output = json.dumps(fundamentals, indent=2)
    
    print("\n" + "=" * 60)
    print("DATA SAVED")
    print("=" * 60)
    
    output_file = "jsons/fundamentals_data.json"
    with open(output_file, "w") as f:
        f.write(output)
    
    print(f"\nFile: {output_file}")

if __name__ == "__main__":
    main()