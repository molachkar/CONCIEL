#!/usr/bin/env python3
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path

SCRIPTS = {
    "fundamentals": {
        "script": "fundamentals.py",
        "outputs": ["fundamentals_data.json"]
    },
    "calendar": {
        "script": "enocomic calender mo.py",
        "outputs": ["data/economic_calendar_investpy.json"]
    },
    "market_data": {
        "script": "marketechnicals.py",
        "outputs": ["market_analysis.json", "xauusd_30d.json"]
    },
    "news_sentiment": {
        "script": "newsentiment.py",
        "outputs": ["data/news_sentiment_layer.json"]
    },
    "social_sentiment": {
        "script": "social media.py",
        "outputs": ["data/reddit_sentiment.json"]
    }
}

OUTPUT_FOLDER = "jsons"
TIMEOUT_SECONDS = 300

def setup_output_folder():
    output_path = Path(OUTPUT_FOLDER)
    output_path.mkdir(exist_ok=True)
    print(f"Output folder: {output_path.absolute()}\n")
    return output_path

def copy_files_to_jsons(output_files, output_folder):
    copied = []
    for output_file in output_files:
        source = Path(output_file)
        if source.exists():
            destination = output_folder / source.name
            shutil.copy2(source, destination)
            print(f"  Copied: {source.name} -> jsons/")
            copied.append(source.name)
        else:
            print(f"  Not found: {output_file}")
    return copied

def run_script(name, config, output_folder):
    script_path = config["script"]
    output_files = config["outputs"]
    
    print("="*60)
    print(f"Running: {name}")
    print(f"Script: {script_path}")
    print("="*60)
    
    if not Path(script_path).exists():
        print(f"ERROR: Script not found: {script_path}\n")
        return False, []
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS
        )
        
        print(result.stdout)
        
        if result.stderr:
            print(f"stderr: {result.stderr}")
        
        if result.returncode != 0:
            print(f"ERROR: Script exited with code {result.returncode}\n")
            return False, []
        
        print("\nCopying output files:")
        copied = copy_files_to_jsons(output_files, output_folder)
        
        if copied:
            print(f"SUCCESS: {len(copied)} file(s) copied\n")
            return True, copied
        else:
            print("WARNING: No output files found\n")
            return False, []
            
    except subprocess.TimeoutExpired:
        print(f"ERROR: Script timed out after {TIMEOUT_SECONDS} seconds\n")
        return False, []
    except Exception as e:
        print(f"ERROR: {str(e)}\n")
        return False, []

def main():
    print("\n" + "="*60)
    print("DATA COLLECTION ORCHESTRATOR - SEQUENTIAL MODE")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scripts: {len(SCRIPTS)}")
    print("="*60 + "\n")
    
    output_folder = setup_output_folder()
    
    results = {}
    
    for name, config in SCRIPTS.items():
        success, copied_files = run_script(name, config, output_folder)
        results[name] = {
            "success": success,
            "files": copied_files
        }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    successful = [k for k, v in results.items() if v["success"]]
    failed = [k for k, v in results.items() if not v["success"]]
    
    print(f"\nSuccessful: {len(successful)}/{len(SCRIPTS)}")
    for name in successful:
        files = results[name]["files"]
        print(f"  {name}: {len(files)} file(s)")
    
    if failed:
        print(f"\nFailed: {len(failed)}/{len(SCRIPTS)}")
        for name in failed:
            print(f"  {name}")
    
    print(f"\nAll outputs in: {output_folder.absolute()}")
    print("="*60 + "\n")
    
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()