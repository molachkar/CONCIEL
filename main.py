import subprocess
import sys
from datetime import datetime
from pathlib import Path
import os

SCRIPTS = {
    "INFLATION": "Fetchers/inflation.py",
    "ECO CALENDER": "Fetchers/eco calender.py",
    "MARKET DATA": "Fetchers/market00.py",
    "DEEP ANALYST": "Fetchers/deep00.py",
    "NEWS": "Fetchers/news.py",
    "REDDIT": "Fetchers/reddit.py",
    "SPLITER": "Editers/spliter.py",
    "ORGINIZER": "Editers/orginizer.py",
}

TIMEOUT_SECONDS = 300

def run_script(name, script_path):
    """Run a single Python script with minimal output"""

    path_obj = Path(script_path)
    if not path_obj.exists():
        print(f"ERROR: {name} - Script not found at {script_path}")
        return False
    
    try:

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=Path.cwd(),
            encoding='utf-8',
            errors='replace',
            env=env
        )

        if result.returncode != 0:
            print(f"ERROR: {name} failed")
            if result.stderr:
                print(result.stderr)
            return False
        
        print(f"{name} done")
        return True
            
    except subprocess.TimeoutExpired:
        print(f"ERROR: {name} timeout")
        return False
    except Exception as e:
        print(f"ERROR: {name} - {str(e)}")
        return False

def verify_all_scripts():
    """Verify all scripts exist before running"""
    all_exist = True
    for name, script_path in SCRIPTS.items():
        path_obj = Path(script_path)
        if not path_obj.exists():
            print(f"ERROR: {name} not found at {script_path}")
            all_exist = False
    
    return all_exist

def main():
    print(f"\nData Collection Runner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not verify_all_scripts():
        sys.exit(1)
    
    results = {}

    for name, script_path in SCRIPTS.items():
        success = run_script(name, script_path)
        results[name] = success

        if not success:
            break
    
    print("\n" + "="*60)
    
    successful = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for name, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {successful}/{len(SCRIPTS)} completed")
    print("="*60)
    
    if failed == 0:
        print("All scripts completed successfully\n")
        sys.exit(0)
    else:
        print("Some scripts failed\n")
        sys.exit(1)

if __name__ == "__main__":
    main()