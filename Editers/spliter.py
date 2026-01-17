import json
import os
import argparse
from datetime import datetime
from collections import defaultdict

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

def process_fundamentals_json(data, output_dir):
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
    
    # Only write files for dates that have more than just collection_info
    for date, content in sorted(date_data.items()):
        if len(content) > 1:  # More than just collection_info
            file_path = os.path.join(folder_path, f"{date}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
    
    files_created = sum(1 for content in date_data.values() if len(content) > 1)
    print(f"Created {files_created} JSON files in {folder_name}")
    return date_data

def process_economic_calendar_json(data, output_dir):
    folder_name = "economic_calendar_events"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    date_events = defaultdict(list)
    
    for event in data.get("events", []):
        date = parse_date(event["date"])
        if date:
            date_events[date].append(event)
    
    # Only write files for dates that have events
    for date, events in sorted(date_events.items()):
        if events:  # Only if there are events
            file_path = os.path.join(folder_path, f"{date}.json")
            content = {
                "date": date,
                "total_events": len(events),
                "events": sorted(events, key=lambda x: x.get("time", ""))
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(date_events)} JSON files in {folder_name}")
    return date_events

def process_market_analysis_json(data, output_dir):
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
    
    # Only write files for dates that have instruments
    for date, content in sorted(date_data.items()):
        if content["instruments"]:  # Only if there are instruments
            file_path = os.path.join(folder_path, f"{date}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
    
    files_created = sum(1 for content in date_data.values() if content["instruments"])
    print(f"Created {files_created} JSON files in {folder_name}")
    return date_data

def process_news_json(data, output_dir):
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
    
    # Only write files for dates that have headlines
    for date, content in sorted(date_news.items()):
        if content["headlines"]:  # Only if there are headlines
            content["headlines"] = sorted(content["headlines"], key=lambda x: x.get("time", ""))
            content["total_headlines"] = len(content["headlines"])
            
            categories = defaultdict(int)
            for h in content["headlines"]:
                categories[h.get("category", "unknown")] += 1
            content["by_category"] = dict(categories)
            
            file_path = os.path.join(folder_path, f"{date}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
    
    files_created = sum(1 for content in date_news.values() if content["headlines"])
    print(f"Created {files_created} JSON files in {folder_name}")
    return date_news

def process_reddit_json(data, output_dir):
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
    
    # Only write files for dates that have posts
    for date, content in sorted(date_posts.items()):
        if content["posts"]:  # Only if there are posts
            content["posts"] = sorted(content["posts"], key=lambda x: x.get("time", ""))
            content["total_posts"] = len(content["posts"])
            
            sources = defaultdict(int)
            for p in content["posts"]:
                sources[p.get("source", "unknown")] += 1
            content["by_subreddit"] = dict(sources)
            
            file_path = os.path.join(folder_path, f"{date}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
    
    files_created = sum(1 for content in date_posts.values() if content["posts"])
    print(f"Created {files_created} JSON files in {folder_name}")
    return date_posts

def convert_economic_calendar_to_txt(json_folder, txt_folder):
    os.makedirs(txt_folder, exist_ok=True)
    
    for filename in os.listdir(json_folder):
        if not filename.endswith('.json'):
            continue
            
        date = filename.replace('.json', '')
        json_path = os.path.join(json_folder, filename)
        txt_path = os.path.join(txt_folder, f"{date}.txt")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Skip if no events
        if not data.get("events"):
            continue
        
        lines = [f"=== ECONOMIC EVENTS: {date} ===", ""]
        
        for event in data.get("events", []):
            time = event.get("time", "")
            name = event.get("event", "").replace(" ", "_").upper()[:25]
            actual = event.get("actual", "")
            forecast = event.get("forecast", "") or "-----"
            previous = event.get("previous", "")
            currency = event.get("currency", "")
            
            status = ""
            if actual and forecast and forecast != "-----":
                try:
                    act_val = float(actual.replace("%", "").replace("K", "").replace("M", "").replace("B", ""))
                    fc_val = float(forecast.replace("%", "").replace("K", "").replace("M", "").replace("B", ""))
                    if act_val > fc_val:
                        status = "BEAT↑"
                    elif act_val < fc_val:
                        status = "MISS↓"
                    else:
                        status = "MEET"
                except:
                    status = "MEET"
            
            line = f"{time}|{name}|{actual}|FC:{forecast}|PV:{previous}|{currency}"
            if status:
                line += f"|{status}"
            lines.append(line)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

def convert_fundamentals_to_txt(json_folder, txt_folder):
    os.makedirs(txt_folder, exist_ok=True)
    
    for filename in os.listdir(json_folder):
        if not filename.endswith('.json'):
            continue
            
        date = filename.replace('.json', '')
        json_path = os.path.join(json_folder, filename)
        txt_path = os.path.join(txt_folder, f"{date}.txt")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        lines = [f"=== FUNDAMENTALS: {date} ===", ""]
        has_content = False
        
        if "TREASURY_10Y" in data:
            lines.append("RATES:")
            for entry in data["TREASURY_10Y"]:
                lines.append(f"T10Y:{entry.get('value')}%")
            has_content = True
        
        if "HY_CREDIT_SPREAD" in data:
            for entry in data["HY_CREDIT_SPREAD"]:
                lines.append(f"HY_SPREAD:{entry.get('value')}%")
            has_content = True
        
        if has_content:
            lines.append("")
        
        if "GLD" in data:
            lines.append("GOLD_ETFS:")
            for entry in data["GLD"]:
                close = entry.get('close', 0)
                vol = entry.get('volume', 0)
                lines.append(f"GLD:${close}|VOL:{vol/1000000:.2f}M")
            has_content = True
        
        if "IAU" in data:
            for entry in data["IAU"]:
                close = entry.get('close', 0)
                vol = entry.get('volume', 0)
                lines.append(f"IAU:${close}|VOL:{vol/1000000:.2f}M")
            has_content = True
        
        if has_content and ("JOBLESS_CLAIMS" in data or "CPI" in data or "UNEMPLOYMENT" in data):
            lines.append("")
        
        if "JOBLESS_CLAIMS" in data:
            lines.append("LABOR:")
            for entry in data["JOBLESS_CLAIMS"]:
                lines.append(f"CLAIMS:{int(entry.get('value', 0))}K")
            has_content = True
        
        if "CPI" in data:
            for entry in data["CPI"]:
                lines.append(f"CPI:{entry.get('value')}")
            has_content = True
        
        if "UNEMPLOYMENT" in data:
            for entry in data["UNEMPLOYMENT"]:
                lines.append(f"UNEMPLOYMENT:{entry.get('value')}%")
            has_content = True
        
        # Only write if there's actual content
        if has_content:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

def convert_market_analysis_to_txt(json_folder, txt_folder):
    os.makedirs(txt_folder, exist_ok=True)
    
    for filename in os.listdir(json_folder):
        if not filename.endswith('.json'):
            continue
            
        date = filename.replace('.json', '')
        json_path = os.path.join(json_folder, filename)
        txt_path = os.path.join(txt_folder, f"{date}.txt")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Skip if no instruments
        if not data.get("instruments"):
            continue
        
        lines = [f"=== MARKET ANALYSIS: {date} ===", ""]
        
        for instrument_name, instrument_data in data.get("instruments", {}).items():
            desc = instrument_data.get("description", "")
            lines.append(f"{instrument_name}({desc})")
            
            market = instrument_data.get("market_data", {})
            if market:
                o = market.get('open', 0)
                h = market.get('high', 0)
                l = market.get('low', 0)
                c = market.get('close', 0)
                lines.append(f"O:{o}|H:{h}|L:{l}|C:{c}")
            
            tech = instrument_data.get("technicals", {})
            if tech:
                rsi = tech.get('rsi_value', 0)
                rsi_st = tech.get('rsi_status', 'N')
                e50 = tech.get('ema50_value', 0)
                e200 = tech.get('ema200_value', 0)
                trend = tech.get('ema_trend', 'N')
                macd = tech.get('macd_value', 0)
                signal = tech.get('macd_signal', 0)
                stk = tech.get('stoch_k_value', 0)
                
                lines.append(f"RSI:{rsi:.1f}({rsi_st})|E50:{e50:.2f}|E200:{e200:.2f}|TREND:{trend}")
                
                macd_dir = ">" if macd > signal else "<"
                lines.append(f"MACD:{macd:.2f}{macd_dir}{signal:.2f}|STK:{stk:.1f}")
            
            lines.append("")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

def convert_news_to_txt(json_folder, txt_folder):
    os.makedirs(txt_folder, exist_ok=True)
    
    for filename in os.listdir(json_folder):
        if not filename.endswith('.json'):
            continue
            
        date = filename.replace('.json', '')
        json_path = os.path.join(json_folder, filename)
        txt_path = os.path.join(txt_folder, f"{date}.txt")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Skip if no headlines
        if not data.get("headlines"):
            continue
        
        source = data.get("source", "")
        lines = [f"=== NEWS: {date} ({source}) ===", ""]
        
        by_category = defaultdict(list)
        for headline in data.get("headlines", []):
            category = headline.get("category", "unknown")
            by_category[category].append(headline)
        
        for category, headlines in sorted(by_category.items()):
            lines.append(f"{category.upper()}({len(headlines)}):")
            for h in headlines[:5]:
                time = h.get("time", "")[:5]
                title = h.get("title", "")[:60]
                ticker = h.get("ticker", "")
                lines.append(f"{time}|{title}|{ticker}")
            lines.append("")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

def convert_reddit_to_txt(json_folder, txt_folder):
    os.makedirs(txt_folder, exist_ok=True)
    
    for filename in os.listdir(json_folder):
        if not filename.endswith('.json'):
            continue
            
        date = filename.replace('.json', '')
        json_path = os.path.join(json_folder, filename)
        txt_path = os.path.join(txt_folder, f"{date}.txt")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Skip if no posts
        if not data.get("posts"):
            continue
        
        lines = [f"=== REDDIT: {date} ===", ""]
        
        for post in data.get("posts", [])[:10]:
            time = post.get("time", "")[:5]
            title = post.get("title", "")[:70]
            source = post.get("source", "")
            lines.append(f"{time}|{title}|{source}")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

def organize_json_files(output_dir):
    print("Step 1: Organizing JSON files by date")
    print("")
    
    input_files = {
        "Fetchers/jsons/economic_calendar.json": process_economic_calendar_json,
        "Fetchers/jsons/fundamentals_data.json": process_fundamentals_json,
        "Fetchers/jsons/market_analysis_30d.json": process_market_analysis_json,
        "Fetchers/jsons/news_30days.json": process_news_json,
        "Fetchers/jsons/reddit_news.json": process_reddit_json
    }
    
    for file_path, processor_func in input_files.items():
        if os.path.exists(file_path):
            print(f"Processing {os.path.basename(file_path)}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            processor_func(data, output_dir)
        else:
            print(f"File not found: {file_path}")
    
    print("")

def convert_to_txt(json_base_dir, txt_base_dir):
    print("Step 2: Converting JSON to optimized TXT")
    print("")
    
    conversions = [
        ("economic_calendar_events", convert_economic_calendar_to_txt),
        ("fundamental_daily_snapshots", convert_fundamentals_to_txt),
        ("market_analysis_daily", convert_market_analysis_to_txt),
        ("news_daily", convert_news_to_txt),
        ("reddit_posts_daily", convert_reddit_to_txt)
    ]
    
    for folder_name, converter_func in conversions:
        json_folder = os.path.join(json_base_dir, folder_name)
        txt_folder = os.path.join(txt_base_dir, folder_name)
        
        if os.path.exists(json_folder):
            print(f"Converting {folder_name} to TXT")
            converter_func(json_folder, txt_folder)
            
            print(f"Deleting JSON files in {folder_name}")
            for filename in os.listdir(json_folder):
                if filename.endswith('.json'):
                    json_path = os.path.join(json_folder, filename)
                    os.remove(json_path)
        else:
            print(f"Folder not found: {json_folder}")
    
    print("")

def main():
    parser = argparse.ArgumentParser(description='Organize and optimize market data files')
    parser.add_argument('--json-only', action='store_true', help='Only create JSON files')
    parser.add_argument('--txt-only', action='store_true', help='Only create TXT files')
    args = parser.parse_args()
    
    base_dir = "TEXT/daily_folders"
    json_dir = base_dir
    txt_dir = base_dir
    
    print("Starting data organization")
    print("")
    
    if not args.txt_only:
        organize_json_files(json_dir)
    
    if not args.json_only:
        convert_to_txt(json_dir, txt_dir)
    
    print("Done")

if __name__ == "__main__":
    main()