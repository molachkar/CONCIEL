import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

FOLDER_MAPPING = {
    "economic_calendar_events": "calendar.txt",
    "fundamental_daily_snapshots": "fundamentals.txt",
    "market_technicals_daily": "technicals.txt",
    "news_daily": "news.txt",
    "reddit_posts_daily": "forums.txt"
}

def parse_date(filename):
    try:
        date_str = filename.replace('.txt', '')
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%d-%m-%Y')
    except ValueError:
        return None

def main():
    base_dir = Path("TEXT/daily_folders")
    output_dir = Path("TEXT/data_by_date")
    
    if not base_dir.exists():
        print(f"Error: {base_dir} not found")
        return
    
    files_by_date = defaultdict(dict)
    
    print("Scanning folders...")
    
    for source_folder, output_name in FOLDER_MAPPING.items():
        folder_path = base_dir / source_folder
        
        if not folder_path.exists():
            print(f"Skipping {source_folder} (not found)")
            continue
        
        count = 0
        for file in folder_path.glob("*.txt"):
            date = parse_date(file.name)
            if date:
                files_by_date[date][output_name] = file
                count += 1
        
        print(f"{source_folder}: {count} files")
    
    print(f"\nCreating {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sorted_dates = sorted(files_by_date.keys(), 
                         key=lambda d: datetime.strptime(d, '%d-%m-%Y'))
    
    total_files = 0
    print(f"\nProcessing {len(sorted_dates)} dates (oldest to newest):\n")
    
    for date in sorted_dates:
        date_folder = output_dir / date
        date_folder.mkdir(exist_ok=True)
        
        file_names = []
        for output_name, source_path in files_by_date[date].items():
            shutil.copy2(source_path, date_folder / output_name)
            file_names.append(output_name.replace('.txt', ''))
            total_files += 1
        
        print(f"{date}: {', '.join(sorted(file_names))}")
    
    print(f"\nDone: {len(sorted_dates)} folders, {total_files} files")
    print(f"Output: {output_dir}")

if __name__ == "__main__":
    main()