#!/usr/bin/env python3
import json
import requests
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
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
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
        print(f"Warning: Only 1 data point found for {series_id}")
    else:
        result[f"{name}_CURR"] = None
        result[f"{name}_PREV"] = None
        print(f"Warning: No data found for {series_id}")
    
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

def collect_fundamentals() -> Dict:
    """Collect all fundamental economic indicators."""
    print("=" * 60)
    print("Collecting fundamental economic data...")
    print("=" * 60)
    
    fundamentals = {
        "collection_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "Federal Reserve Economic Data (FRED)"
    }
    
    # Core Inflation Indicators
    print("\n Fetching CPI (Consumer Price Index)...")
    fundamentals.update(fetch_monthly_indicator("CPIAUCSL", "CPI"))
    
    print("Fetching PCE (Personal Consumption Expenditures)...")
    fundamentals.update(fetch_monthly_indicator("PCEPI", "PCE"))
    
    print("Fetching PPI (Producer Price Index)...")
    fundamentals.update(fetch_monthly_indicator("PPIACO", "PPI"))
    
    # Labor Market
    print("Fetching Unemployment Rate...")
    fundamentals.update(fetch_monthly_indicator("UNRATE", "UNEMPLOYMENT"))
    
    print("Fetching NFP (Nonfarm Payrolls)...")
    fundamentals.update(fetch_monthly_indicator("PAYEMS", "NFP"))
    
    print("Fetching Initial Jobless Claims (weekly data, last 30 days)...")
    fundamentals.update(fetch_daily_previous_month("ICSA", "JOBLESS_CLAIMS"))
    
    # Interest Rates
    print("Fetching Treasury 10Y Yield...")
    fundamentals.update(fetch_daily_previous_month("DGS10", "TREASURY_10Y"))
    
    print("Fetching Fed Funds Rate...")
    fundamentals.update(fetch_monthly_indicator("FEDFUNDS", "FEDFUNDS"))
    
    print("Calculating Real Interest Rate...")
    fundamentals.update(fetch_real_interest_rate())
    
    # Economic Activity
    print("Fetching M2 Money Supply...")
    fundamentals.update(fetch_monthly_indicator("M2SL", "M2_MONEY_SUPPLY"))
    
    print("Fetching Retail Sales...")
    fundamentals.update(fetch_monthly_indicator("RSAFS", "RETAIL_SALES"))
    
    print("Fetching Industrial Production Index...")
    fundamentals.update(fetch_monthly_indicator("INDPRO", "INDUSTRIAL_PROD"))
    
    print(" Fetching Housing Starts...")
    fundamentals.update(fetch_monthly_indicator("HOUST", "HOUSING_STARTS"))
    
    return fundamentals

def main():
    print("\n" + "=" * 60)
    print("FUNDAMENTALS DATA COLLECTION SCRIPT")
    print("=" * 60)
    
    fundamentals = collect_fundamentals()
    
    output = json.dumps(fundamentals, indent=2)
    
    print("\n" + "=" * 60)
    print("DATA COLLECTION COMPLETE")
    print("=" * 60)
    print(output)
    
    output_file = "fundamentals_data.json"
    with open(output_file, "w") as f:
        f.write(output)
    
    print(f"\n Data saved to: {output_file}")

if __name__ == "__main__":
    main()