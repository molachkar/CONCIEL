#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

INPUT_FOLDER = "Fetchers/jsons"
OUTPUT_FOLDER = "TEXT/daily_snapshots"

def parse_date(date_str):
    """Parse various date formats"""
    if not date_str:
        return None
    
    # Clean the date string
    date_str = str(date_str).strip()
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y"  # For economic calendar
    ]
    
    for fmt in formats:
        try:
            # Handle datetime strings by taking only the date part
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            elif " " in date_str and ":" in date_str:
                date_str = date_str.split()[0]
            
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None

def extract_monthly_inflation_data(input_path):
    """Extract monthly inflation and economic indicators to separate file"""
    filepath = input_path / "fundamentals_data.json"
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    inflation_data = {
        "generated_at": datetime.now().isoformat(),
        "data_source": data.get("data_source", "Federal Reserve Economic Data (FRED)"),
        "description": "Monthly inflation and economic indicators",
        "indicators": {}
    }
    
    # Monthly indicators to extract
    monthly_keys = [
        "CPI", "PCE", "PPI", "UNEMPLOYMENT", "NFP", 
        "FEDFUNDS", "M2_MONEY_SUPPLY", "RETAIL_SALES",
        "INDUSTRIAL_PROD", "HOUSING_STARTS"
    ]
    
    for key in monthly_keys:
        if key in data and data[key] is not None:
            inflation_data["indicators"][key] = {
                "data": data[key],
                "end_date": data.get(f"{key}_END_DATE")
            }
    
    # Add calculated indicators
    if "REAL_RATE" in data and data["REAL_RATE"] is not None:
        inflation_data["indicators"]["REAL_RATE"] = {
            "value": data["REAL_RATE"],
            "end_date": data.get("REAL_RATE_END_DATE")
        }
    
    return inflation_data

def extract_market_analysis_30d(input_path):
    """Extract data from market_analysis_30d.json organized by date"""
    filepath = input_path / "market_analysis_30d.json"
    if not filepath.exists():
        print(f"  ! {filepath.name} not found")
        return {}
    
    print(f"  Scanning {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date_data = defaultdict(lambda: {
        "market_data": {},
        "technicals": {}
    })
    
    # Process each instrument
    instruments = data.get("instruments", [])
    
    for instrument_data in instruments:
        instrument = instrument_data.get("instrument")
        if not instrument:
            continue
        
        # Extract 30-day range info (constant for all dates in this instrument)
        thirty_day_range = instrument_data.get("thirty_day_range", {})
        
        # Process market_data (OHLC for each day)
        market_data_list = instrument_data.get("market_data", [])
        for day_data in market_data_list:
            date_str = day_data.get("date")
            date_obj = parse_date(date_str)
            
            if date_obj:
                # Store OHLC data
                date_data[date_obj]["market_data"][f"{instrument}_OPEN"] = day_data.get("open")
                date_data[date_obj]["market_data"][f"{instrument}_HIGH"] = day_data.get("high")
                date_data[date_obj]["market_data"][f"{instrument}_LOW"] = day_data.get("low")
                date_data[date_obj]["market_data"][f"{instrument}_CLOSE"] = day_data.get("close")
                
                # Add 30-day range info to the most recent date only
                if day_data == market_data_list[-1]:
                    date_data[date_obj]["market_data"][f"{instrument}_30D_HIGH"] = thirty_day_range.get("thirty_day_high")
                    date_data[date_obj]["market_data"][f"{instrument}_30D_HIGH_DATE"] = thirty_day_range.get("thirty_day_high_date")
                    date_data[date_obj]["market_data"][f"{instrument}_30D_LOW"] = thirty_day_range.get("thirty_day_low")
                    date_data[date_obj]["market_data"][f"{instrument}_30D_LOW_DATE"] = thirty_day_range.get("thirty_day_low_date")
        
        # Process technicals for each day
        technicals_list = instrument_data.get("technicals", [])
        for day_tech in technicals_list:
            date_str = day_tech.get("date")
            date_obj = parse_date(date_str)
            
            if date_obj:
                # Store all technical indicators
                date_data[date_obj]["technicals"][f"{instrument}_RSI"] = day_tech.get("rsi_value")
                date_data[date_obj]["technicals"][f"{instrument}_RSI_STATUS"] = day_tech.get("rsi_status")
                date_data[date_obj]["technicals"][f"{instrument}_EMA50"] = day_tech.get("ema50_value")
                date_data[date_obj]["technicals"][f"{instrument}_EMA200"] = day_tech.get("ema200_value")
                date_data[date_obj]["technicals"][f"{instrument}_EMA_TREND"] = day_tech.get("ema_trend")
                date_data[date_obj]["technicals"][f"{instrument}_MACD"] = day_tech.get("macd_value")
                date_data[date_obj]["technicals"][f"{instrument}_MACD_SIGNAL"] = day_tech.get("macd_signal")
                date_data[date_obj]["technicals"][f"{instrument}_MACD_HIST"] = day_tech.get("macd_histogram")
                date_data[date_obj]["technicals"][f"{instrument}_STOCH_K"] = day_tech.get("stoch_k_value")
                date_data[date_obj]["technicals"][f"{instrument}_STOCH_D"] = day_tech.get("stoch_d_value")
                date_data[date_obj]["technicals"][f"{instrument}_STOCH_STATUS"] = day_tech.get("stoch_status")
    
    return date_data

def extract_fundamentals_data(input_path):
    """Extract fundamentals data organized by date"""
    filepath = input_path / "fundamentals_data.json"
    if not filepath.exists():
        print(f"  ! {filepath.name} not found")
        return {}
    
    print(f"  Scanning {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date_data = defaultdict(lambda: {"fundamentals": {}})
    
    # Daily metrics with history
    daily_keys = ["TREASURY_10Y", "HY_CREDIT_SPREAD"]
    
    for key in daily_keys:
        if key in data and isinstance(data[key], list):
            for entry in data[key]:
                date = entry.get("date")
                if date:
                    date_obj = parse_date(date)
                    if date_obj:
                        date_data[date_obj]["fundamentals"][key] = entry.get("value")
    
    # GLD and IAU (have close and volume)
    for etf in ["GLD", "IAU"]:
        if etf in data and isinstance(data[etf], list):
            for entry in data[etf]:
                date = entry.get("date")
                if date:
                    date_obj = parse_date(date)
                    if date_obj:
                        date_data[date_obj]["fundamentals"][f"{etf}_CLOSE"] = entry.get("close")
                        date_data[date_obj]["fundamentals"][f"{etf}_VOLUME"] = entry.get("volume")
    
    # Weekly metrics
    if "JOBLESS_CLAIMS" in data and isinstance(data["JOBLESS_CLAIMS"], list):
        for entry in data["JOBLESS_CLAIMS"]:
            date = entry.get("date")
            if date:
                date_obj = parse_date(date)
                if date_obj:
                    date_data[date_obj]["fundamentals"]["JOBLESS_CLAIMS"] = entry.get("value")
    
    # Monthly metrics - show all available data up to each date
    monthly_keys = [
        "CPI", "PCE", "PPI", "UNEMPLOYMENT", "NFP", 
        "FEDFUNDS", "M2_MONEY_SUPPLY", "RETAIL_SALES",
        "INDUSTRIAL_PROD", "HOUSING_STARTS"
    ]
    
    for key in monthly_keys:
        if key in data and isinstance(data[key], list) and data[key]:
            # For each monthly indicator, add complete history up to end_date
            end_date_str = data.get(f"{key}_END_DATE")
            if end_date_str:
                end_date_obj = parse_date(end_date_str)
                if end_date_obj:
                    # Add the full monthly array to the end date
                    date_data[end_date_obj]["fundamentals"][key] = data[key]
    
    # Calculated indicators (single values with end dates)
    if "REAL_RATE" in data and data["REAL_RATE"] is not None:
        end_date = data.get("REAL_RATE_END_DATE")
        if end_date:
            date_obj = parse_date(end_date)
            if date_obj:
                date_data[date_obj]["fundamentals"]["REAL_RATE"] = data["REAL_RATE"]
    
    return date_data

def extract_economic_calendar(input_path):
    """Extract economic calendar events organized by date"""
    filepath = input_path / "economic_calendar.json"
    if not filepath.exists():
        print(f"  ! {filepath.name} not found")
        return {}
    
    print(f"  Scanning {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date_data = defaultdict(lambda: {"economic_events": []})
    
    if "events" in data:
        for event in data["events"]:
            date_str = event.get("date")
            if date_str:
                date_obj = parse_date(date_str)
                if date_obj:
                    date_data[date_obj]["economic_events"].append({
                        "time": event.get("time"),
                        "currency": event.get("currency"),
                        "event": event.get("event"),
                        "actual": event.get("actual"),
                        "forecast": event.get("forecast"),
                        "previous": event.get("previous")
                    })
    
    return date_data

def extract_news_data(input_path):
    """Extract news data organized by date"""
    filepath = input_path / "news_30days.json"
    if not filepath.exists():
        print(f"  ! {filepath.name} not found")
        return {}
    
    print(f"  Scanning {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date_data = defaultdict(lambda: {"news": []})
    
    if "headlines" in data:
        for article in data["headlines"]:
            time = article.get("time")
            if time:
                date_obj = parse_date(time)
                if date_obj:
                    date_data[date_obj]["news"].append({
                        "category": article.get("category"),
                        "title": article.get("title"),
                        "ticker": article.get("ticker")
                    })
    
    return date_data

def extract_reddit_data(input_path):
    """Extract reddit data organized by date"""
    filepath = input_path / "reddit_news.json"
    if not filepath.exists():
        print(f"  ! {filepath.name} not found")
        return {}
    
    print(f"  Scanning {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date_data = defaultdict(lambda: {"reddit": []})
    
    if "posts" in data:
        for post in data["posts"]:
            time = post.get("time")
            if time:
                date_obj = parse_date(time)
                if date_obj:
                    date_data[date_obj]["reddit"].append({
                        "title": post.get("title"),
                        "source": post.get("source")
                    })
    
    return date_data

def merge_date_data(all_extractions):
    """Merge data from all sources by date"""
    merged = defaultdict(lambda: {
        "market_data": {},
        "technicals": {},
        "fundamentals": {},
        "economic_events": [],
        "news": [],
        "reddit": []
    })
    
    for extraction in all_extractions:
        for date_obj, data in extraction.items():
            for category, content in data.items():
                if isinstance(content, dict):
                    merged[date_obj][category].update(content)
                elif isinstance(content, list):
                    merged[date_obj][category].extend(content)
    
    return merged

def clean_snapshot_data(data):
    """Remove empty sections from snapshot data"""
    cleaned = {}
    
    for key, value in data.items():
        # Keep dictionaries only if they have content
        if isinstance(value, dict):
            if value:  # Non-empty dict
                cleaned[key] = value
        # Keep lists only if they have content
        elif isinstance(value, list):
            if value:  # Non-empty list
                cleaned[key] = value
        # Keep other values as-is
        else:
            cleaned[key] = value
    
    return cleaned

def main():
    print("\n" + "="*60)
    print("ENHANCED DAILY SNAPSHOT GENERATOR")
    print("="*60 + "\n")
    
    input_path = Path(INPUT_FOLDER)
    if not input_path.exists():
        print(f"ERROR: {INPUT_FOLDER} folder not found")
        return
    
    output_path = Path(OUTPUT_FOLDER)
    output_path.mkdir(exist_ok=True)
    
    # Generate inflation data file first
    print("Generating inflation_data.json...\n")
    inflation_data = extract_monthly_inflation_data(input_path)
    if inflation_data and inflation_data["indicators"]:
        inflation_file = output_path / "inflation_data.json"
        with open(inflation_file, 'w', encoding='utf-8') as f:
            json.dump(inflation_data, f, indent=2, ensure_ascii=False)
        print(f"✓ inflation_data.json created\n")
    else:
        print("! No monthly inflation data found\n")
    
    # Extract all data from various sources
    print("Extracting data from all sources...\n")
    
    market_analysis_data = extract_market_analysis_30d(input_path)
    fundamentals_data = extract_fundamentals_data(input_path)
    economic_calendar_data = extract_economic_calendar(input_path)
    news_data = extract_news_data(input_path)
    reddit_data = extract_reddit_data(input_path)
    
    # Merge all data by date
    print("\nMerging data by date...")
    all_extractions = [
        market_analysis_data,
        fundamentals_data,
        economic_calendar_data,
        news_data,
        reddit_data
    ]
    
    date_data = merge_date_data(all_extractions)
    
    if not date_data:
        print("ERROR: No data found in any files")
        return
    
    # Get date range
    all_dates = sorted(date_data.keys())
    oldest_date = all_dates[0]
    newest_date = all_dates[-1]
    
    print(f"\nDate range found:")
    print(f"  Oldest: {oldest_date}")
    print(f"  Newest: {newest_date}")
    print(f"  Total days with data: {len(all_dates)}")
    print("\n" + "="*60)
    
    # Calculate the cutoff date (30 days ago from today)
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=30)
    
    # Delete old snapshot files (older than 30 days)
    print("\nCleaning old snapshots...\n")
    deleted_count = 0
    for snapshot_file in output_path.glob("snapshot_*.json"):
        try:
            # Extract date from filename: snapshot_2025-11-07.json
            date_str = snapshot_file.stem.replace("snapshot_", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            if file_date < cutoff_date:
                snapshot_file.unlink()
                deleted_count += 1
                print(f"✗ Deleted: {snapshot_file.name}")
        except (ValueError, IndexError):
            continue
    
    if deleted_count == 0:
        print("No old snapshots to delete")
    
    # Generate snapshots only for the last 30 days
    print("\nGenerating daily snapshots (last 30 days)...\n")
    
    current_date = max(cutoff_date, oldest_date)  # Start from cutoff or oldest available
    snapshot_count = 0
    
    while current_date <= newest_date:
        if current_date in date_data:
            # Clean the data to remove empty sections
            cleaned_data = clean_snapshot_data(date_data[current_date])
            
            # Only create snapshot if there's actual data
            if cleaned_data:
                snapshot = {
                    "date": current_date.isoformat(),
                    "snapshot_generated_at": datetime.now().isoformat(),
                    "data": cleaned_data
                }
                
                # Save snapshot
                filename = f"snapshot_{current_date.isoformat()}.json"
                filepath = output_path / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, indent=2, ensure_ascii=False)
                
                snapshot_count += 1
                print(f"✓ {filename}")
        
        current_date += timedelta(days=1)
    
    print("\n" + "="*60)
    print(f"Deleted {deleted_count} old snapshots (older than 30 days)")
    print(f"Generated {snapshot_count} daily snapshots (last 30 days)")
    print(f"Generated 1 inflation data file")
    print(f"Output folder: {OUTPUT_FOLDER}/")
    print("="*60)
    print("FINISHED\n")

if __name__ == "__main__":
    main()