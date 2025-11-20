#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

def load_json_file(filepath: str) -> Any:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def parse_date(date_str: str) -> str:
    """Parse various date formats and return YYYY-MM-DD"""
    if not date_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
        "%m/%d/%Y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.split('T')[0] if 'T' in date_str else date_str.split(' ')[0], fmt.split('T')[0])
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    return None

def extract_dates_from_calendar(data: Any) -> Dict[str, List[Any]]:
    dates = defaultdict(list)
    if not data or 'events' not in data:
        return dates
    
    for event in data['events']:
        date_str = event.get('date', '')
        date = parse_date(date_str)
        if date:
            dates[date].append({
                'type': 'calendar_event',
                'data': event
            })
    
    return dates

def extract_dates_from_fundamentals(data: Dict) -> Dict[str, List[Any]]:
    dates = defaultdict(list)
    if not data:
        return dates
    
    # Handle date-specific fundamental data
    date_fields = [
        ('CPI_CURR_DATE', 'CPI_CURR', 'CPI'),
        ('PCE_CURR_DATE', 'PCE_CURR', 'PCE'),
        ('UNEMPLOYMENT_CURR_DATE', 'UNEMPLOYMENT_CURR', 'UNEMPLOYMENT'),
        ('NFP_CURR_DATE', 'NFP_CURR', 'NFP'),
        ('M2_MONEY_SUPPLY_CURR_DATE', 'M2_MONEY_SUPPLY_CURR', 'M2_MONEY_SUPPLY'),
        ('RETAIL_SALES_CURR_DATE', 'RETAIL_SALES_CURR', 'RETAIL_SALES'),
        ('INDUSTRIAL_PROD_CURR_DATE', 'INDUSTRIAL_PROD_CURR', 'INDUSTRIAL_PROD'),
        ('HOUSING_STARTS_CURR_DATE', 'HOUSING_STARTS_CURR', 'HOUSING_STARTS'),
        ('FEDFUNDS_CURR_DATE', 'FEDFUNDS_CURR', 'FEDFUNDS')
    ]
    
    for date_field, value_field, name in date_fields:
        if date_field in data and value_field in data:
            date = parse_date(data[date_field])
            if date:
                dates[date].append({
                    'type': f'fundamental_{name}',
                    'data': {
                        'indicator': name,
                        'value': data[value_field],
                        'date': date
                    }
                })
    
    # Handle TREASURY_10Y_LAST_30_DAYS
    if 'TREASURY_10Y_LAST_30_DAYS' in data and isinstance(data['TREASURY_10Y_LAST_30_DAYS'], list):
        for item in data['TREASURY_10Y_LAST_30_DAYS']:
            date = parse_date(item.get('date'))
            if date:
                dates[date].append({
                    'type': 'fundamental_TREASURY_10Y',
                    'data': item
                })
    
    return dates

def extract_dates_from_market(data: Any) -> Dict[str, List[Any]]:
    dates = defaultdict(list)
    if not data or not isinstance(data, list):
        return dates
    
    now = datetime.now()
    
    for item in data:
        if not isinstance(item, dict):
            continue
        
        # Current market snapshot goes to today
        if 'timestamp' in item:
            timestamp = item.get('timestamp', '')
            date = parse_date(timestamp)
            if date:
                dates[date].append({
                    'type': 'market_snapshot_current',
                    'data': item
                })
        
        # Weekly support/resistance goes to 7 days ago
        if 'support_resistance' in item and 'weekly' in item['support_resistance']:
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            dates[week_ago].append({
                'type': 'market_weekly_sr',
                'data': {
                    'instrument': item.get('instrument'),
                    'weekly_support_resistance': item['support_resistance']['weekly']
                }
            })
    
    return dates

def extract_dates_from_xauusd(data: Any) -> Dict[str, List[Any]]:
    dates = defaultdict(list)
    if not data or not isinstance(data, list):
        return dates
    
    for candle in data:
        if isinstance(candle, dict) and 'time' in candle:
            date = parse_date(candle['time'])
            if date:
                dates[date].append({
                    'type': 'xauusd_ohlcv',
                    'data': candle
                })
    
    return dates

def extract_dates_from_news(data: Any) -> Dict[str, List[Any]]:
    dates = defaultdict(list)
    if not data:
        return dates
    
    # Handle all timeframes
    for timeframe in ['30D', '7D', '24H']:
        if timeframe in data and 'raw_headlines' in data[timeframe]:
            for article in data[timeframe]['raw_headlines']:
                time_str = article.get('time', '')
                date = parse_date(time_str)
                if date:
                    dates[date].append({
                        'type': 'news_headline',
                        'data': article
                    })
    
    return dates

def extract_dates_from_reddit(data: Any) -> Dict[str, List[Any]]:
    dates = defaultdict(list)
    if not data:
        return dates
    
    # Handle all timeframes
    for timeframe in ['30D', '7D', '24H']:
        if timeframe in data and 'posts' in data[timeframe]:
            for post in data[timeframe]['posts']:
                time_str = post.get('time', '')
                date = parse_date(time_str)
                if date:
                    dates[date].append({
                        'type': 'reddit_post',
                        'data': post
                    })
    
    return dates

def organize_by_date(jsons_folder: str = "jsons") -> Dict[str, Any]:
    all_dates = defaultdict(lambda: {
        'calendar': [],
        'fundamentals': [],
        'market': [],
        'xauusd_ohlcv': [],
        'news': [],
        'reddit': []
    })
    
    files = {
        'calendar': 'economic_calendar_investpy.json',
        'fundamentals': 'fundamentals_data.json',
        'market': 'market_analysis.json',
        'xauusd': 'xauusd_30d.json',
        'news': 'news_sentiment_layer.json',
        'reddit': 'reddit_sentiment.json'
    }
    
    for file_type, filename in files.items():
        filepath = os.path.join(jsons_folder, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping...")
            continue
        
        data = load_json_file(filepath)
        if data is None:
            continue
        
        date_items = {}
        
        if file_type == 'calendar':
            date_items = extract_dates_from_calendar(data)
        elif file_type == 'fundamentals':
            date_items = extract_dates_from_fundamentals(data)
        elif file_type == 'market':
            date_items = extract_dates_from_market(data)
        elif file_type == 'xauusd':
            date_items = extract_dates_from_xauusd(data)
        elif file_type == 'news':
            date_items = extract_dates_from_news(data)
        elif file_type == 'reddit':
            date_items = extract_dates_from_reddit(data)
        
        for date, items in date_items.items():
            for item in items:
                item_type = item['type']
                
                if 'calendar' in item_type:
                    all_dates[date]['calendar'].append(item['data'])
                elif 'fundamental' in item_type:
                    all_dates[date]['fundamentals'].append(item['data'])
                elif 'market' in item_type:
                    all_dates[date]['market'].append(item['data'])
                elif 'xauusd' in item_type:
                    all_dates[date]['xauusd_ohlcv'].append(item['data'])
                elif 'news' in item_type:
                    all_dates[date]['news'].append(item['data'])
                elif 'reddit' in item_type:
                    all_dates[date]['reddit'].append(item['data'])
    
    return dict(all_dates)

def categorize_by_timeframe(organized_data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)
    
    result = {
        'last_30_days': {},
        'older_data': {}
    }
    
    for date_str, data in organized_data.items():
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            if date_obj >= one_month_ago:
                result['last_30_days'][date_str] = data
            else:
                result['older_data'][date_str] = data
        except ValueError:
            result['older_data'][date_str] = data
    
    return result

def save_organized_data(organized_data: Dict[str, Any], output_path: str = "organized_data.json"):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(organized_data, f, indent=2, ensure_ascii=False)
    print(f"Organized data saved to {output_path}")

def main():
    print("Starting data organization...")
    
    organized = organize_by_date("jsons")
    
    categorized = categorize_by_timeframe(organized)
    
    save_organized_data(categorized, "organized_data.json")
    
    print(f"\nSummary:")
    print(f"Last 30 days: {len(categorized['last_30_days'])} dates")
    print(f"Older data: {len(categorized['older_data'])} dates")
    
    # Show sample of what's in each date
    if categorized['last_30_days']:
        sample_date = list(categorized['last_30_days'].keys())[0]
        sample_data = categorized['last_30_days'][sample_date]
        print(f"\nSample date {sample_date}:")
        for key, items in sample_data.items():
            if items:
                print(f"  {key}: {len(items)} items")

if __name__ == "__main__":
    main()