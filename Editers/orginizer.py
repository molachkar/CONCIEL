import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

FOLDER_MAPPING = {
    "economic_calendar_events": "calendar.txt",
    "fundamental_daily_snapshots": "fundamentals.txt",
    "market_technicals_daily": "technicals.txt",
    "deepin_daily_analysis": "calculos.txt",
    "news_daily": "news.txt",
    "reddit_posts_daily": "forums.txt"
}

def parse_date(filename):
    try:
        date_str = filename.replace('.txt', '')
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None

def main():
    base_dir = Path("TEXT/daily_folders")
    output_dir = Path("TEXT/data_by_date")
    
    if not base_dir.exists():
        print(f"Error: {base_dir} not found")
        return
    
    files_by_date = defaultdict(dict)
    
    for source_folder, output_name in FOLDER_MAPPING.items():
        folder_path = base_dir / source_folder
        
        if not folder_path.exists():
            continue
        
        count = 0
        for file in folder_path.glob("*.txt"):
            date = parse_date(file.name)
            if date:
                files_by_date[date][output_name] = file
                count += 1
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sorted_dates = sorted(files_by_date.keys())
    
    if not sorted_dates:
        print("No files found")
        return
    
    total_files = 0
    for date in sorted_dates:
        date_folder = output_dir / date
        date_folder.mkdir(exist_ok=True)
        
        for output_name, source_path in files_by_date[date].items():
            shutil.copy2(source_path, date_folder / output_name)
            total_files += 1
    
    print("Done")

if __name__ == "__main__":
    main()