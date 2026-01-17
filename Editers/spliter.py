import json
import os
from datetime import datetime
from collections import defaultdict
from pathlib import Path

def parse_date(date_str):
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.split()[0] if ' ' in date_str else date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None

def process_fundamentals(data, output_dir):
    folder_name = "fundamental_daily_snapshots"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    date_data = defaultdict(lambda: {
        "collection_info": {
            "source": data.get("data_source", ""),
            "original_collection_date": data.get("collection_date", "")
        }
    })
    
    for key, value in data.items():
        if key.startswith("#") or key in ["collection_date", "data_source"]:
            continue
            
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            for entry in value:
                if "date" in entry:
                    date = parse_date(entry["date"])
                    if date:
                        if key not in date_data[date]:
                            date_data[date][key] = []
                        date_data[date][key].append(entry)
        elif key.endswith("_END_DATE"):
            continue
    
    for date, content in sorted(date_data.items()):
        file_path = os.path.join(folder_path, f"{date}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(date_data)} files in {folder_name}")

def process_economic_calendar(data, output_dir):
    folder_name = "economic_calendar_events"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    date_events = defaultdict(list)
    
    for event in data.get("events", []):
        date = parse_date(event["date"])
        if date:
            date_events[date].append(event)
    
    for date, events in sorted(date_events.items()):
        file_path = os.path.join(folder_path, f"{date}.json")
        content = {
            "date": date,
            "total_events": len(events),
            "events": sorted(events, key=lambda x: x.get("time", ""))
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(date_events)} files in {folder_name}")

def process_market_analysis(data, output_dir):
    folder_name = "market_analysis_daily"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    date_data = defaultdict(lambda: {
        "analysis_info": {
            "generated_at": data.get("generated_at", ""),
            "period_days": data.get("period_days", 30)
        },
        "instruments": {}
    })
    
    for instrument_data in data.get("instruments", []):
        instrument_name = instrument_data.get("instrument", "")
        
        for market_entry in instrument_data.get("market_data", []):
            date = parse_date(market_entry["date"])
            if date:
                if instrument_name not in date_data[date]["instruments"]:
                    date_data[date]["instruments"][instrument_name] = {
                        "description": instrument_data.get("description", ""),
                        "market_data": {},
                        "technicals": {}
                    }
                date_data[date]["instruments"][instrument_name]["market_data"] = market_entry
        
        for tech_entry in instrument_data.get("technicals", []):
            date = parse_date(tech_entry["date"])
            if date:
                if instrument_name not in date_data[date]["instruments"]:
                    date_data[date]["instruments"][instrument_name] = {
                        "description": instrument_data.get("description", ""),
                        "market_data": {},
                        "technicals": {}
                    }
                date_data[date]["instruments"][instrument_name]["technicals"] = tech_entry
    
    for date, content in sorted(date_data.items()):
        file_path = os.path.join(folder_path, f"{date}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(date_data)} files in {folder_name}")

def process_news(data, output_dir):
    folder_name = "news_daily"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    date_news = defaultdict(lambda: {
        "source": data.get("source", ""),
        "headlines": []
    })
    
    for headline in data.get("headlines", []):
        date = parse_date(headline["time"])
        if date:
            date_news[date]["headlines"].append(headline)
    
    for date, content in sorted(date_news.items()):
        content["headlines"] = sorted(content["headlines"], key=lambda x: x.get("time", ""))
        content["total_headlines"] = len(content["headlines"])
        
        categories = defaultdict(int)
        for h in content["headlines"]:
            categories[h.get("category", "unknown")] += 1
        content["by_category"] = dict(categories)
        
        file_path = os.path.join(folder_path, f"{date}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(date_news)} files in {folder_name}")

def process_reddit(data, output_dir):
    folder_name = "reddit_posts_daily"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    date_posts = defaultdict(lambda: {
        "fetch_info": {
            "fetch_time": data.get("fetch_time", ""),
            "total_fetched": data.get("total_fetched", 0),
            "total_filtered": data.get("total_filtered", 0)
        },
        "posts": []
    })
    
    for post in data.get("posts", []):
        date = parse_date(post["time"])
        if date:
            date_posts[date]["posts"].append(post)
    
    for date, content in sorted(date_posts.items()):
        content["posts"] = sorted(content["posts"], key=lambda x: x.get("time", ""))
        content["total_posts"] = len(content["posts"])
        
        sources = defaultdict(int)
        for p in content["posts"]:
            sources[p.get("source", "unknown")] += 1
        content["by_subreddit"] = dict(sources)
        
        file_path = os.path.join(folder_path, f"{date}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(date_posts)} files in {folder_name}")

def main():
    input_files = {
        "Fetchers/jsons/economic_calendar.json": process_economic_calendar,
        "Fetchers/jsons/fundamentals_data.json": process_fundamentals,
        "Fetchers/jsons/market_analysis_30d.json": process_market_analysis,
        "Fetchers/jsons/news_30days.json": process_news,
        "Fetchers/jsons/reddit_news.json": process_reddit
    }
    
    output_dir = "TEXT/daily_folders"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Starting data organization")
    print("")
    
    for file_path, processor_func in input_files.items():
        if os.path.exists(file_path):
            print(f"Processing {os.path.basename(file_path)}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            processor_func(data, output_dir)
        else:
            print(f"File not found: {file_path}")
    
    print("")
    print("Done")

if __name__ == "__main__":
    main()