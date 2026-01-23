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
    """Parse date from filename, handling both date files and special files like monthly_data"""
    # Skip non-date files
    if filename == 'monthly_data.txt':
        return None
    
    try:
        date_str = filename.replace('.txt', '')
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None

def copy_monthly_data(base_dir, output_dir):
    """Copy monthly_data.txt to a separate location for reference"""
    fundamentals_folder = base_dir / "fundamental_daily_snapshots"
    monthly_file = fundamentals_folder / "monthly_data.txt"
    
    if monthly_file.exists():
        # Create a reference folder for monthly data
        monthly_dir = output_dir / "_monthly_reference"
        monthly_dir.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(monthly_file, monthly_dir / "monthly_fundamentals.txt")
        print(f"Copied monthly reference data to {monthly_dir}")
        return True
    return False

def main():
    base_dir = Path("TEXT/daily_folders")
    output_dir = Path("TEXT/data_by_date")
    
    if not base_dir.exists():
        print(f"Error: {base_dir} not found")
        return
    
    # First, handle monthly data separately
    print("Step 1: Handling monthly reference data")
    copy_monthly_data(base_dir, output_dir)
    print("")
    
    # Then organize daily data
    print("Step 2: Organizing daily data by date")
    files_by_date = defaultdict(dict)
    
    for source_folder, output_name in FOLDER_MAPPING.items():
        folder_path = base_dir / source_folder
        
        if not folder_path.exists():
            continue
        
        count = 0
        for file in folder_path.glob("*.txt"):
            date = parse_date(file.name)
            if date:  # Only process files with valid dates
                files_by_date[date][output_name] = file
                count += 1
        
        if count > 0:
            print(f"  {source_folder}: {count} files")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sorted_dates = sorted(files_by_date.keys())
    
    if not sorted_dates:
        print("No daily files found")
        return
    
    print(f"\nStep 3: Creating date folders ({sorted_dates[0]} to {sorted_dates[-1]})")
    total_files = 0
    total_folders = 0
    
    for date in sorted_dates:
        date_folder = output_dir / date
        date_folder.mkdir(exist_ok=True)
        
        for output_name, source_path in files_by_date[date].items():
            shutil.copy2(source_path, date_folder / output_name)
            total_files += 1
        
        total_folders += 1
    
    print(f"\nCompleted:")
    print(f"  Created {total_folders} date folders")
    print(f"  Copied {total_files} files")
    print(f"  Output directory: {output_dir}")

if __name__ == "__main__":
    main()