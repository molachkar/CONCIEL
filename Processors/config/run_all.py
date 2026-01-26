import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_DIR, MACRO_STRUCTURED_DIR, PROCESSING_CONFIG, OUTPUT_CONFIG
from agent_macro import MacroAgent
from agent_market import MarketAgent
from agent_narrative import NarrativeAgent

def process_single_date(date: str) -> Dict:
    results = {'date': date, 'timestamp': datetime.now().isoformat(), 'agents': {}}
    date_folder = DATA_DIR / date
    if not date_folder.exists():
        if PROCESSING_CONFIG['skip_missing_data']:
            print(f"Skipping {date}")
            return results
        print(f"Aborting {date}")
        return results
    
    try:
        macro_agent = MacroAgent()
        results['agents']['macro'] = macro_agent.analyze(date)
    except Exception as e:
        print(f"Macro failed: {e}")
        results['agents']['macro'] = None
    
    try:
        market_agent = MarketAgent()
        results['agents']['market'] = market_agent.analyze(date)
    except Exception as e:
        print(f"Market failed: {e}")
        results['agents']['market'] = None
    
    try:
        narrative_agent = NarrativeAgent()
        results['agents']['narrative'] = narrative_agent.analyze(date)
    except Exception as e:
        print(f"Narrative failed: {e}")
        results['agents']['narrative'] = None
    
    success_count = sum(1 for r in results['agents'].values() if r is not None)
    print(f"Completed: {success_count}/3 agents")
    
    if OUTPUT_CONFIG['save_combined_output'] and success_count > 0:
        save_combined_output(date, results)
    
    return results

def save_combined_output(date: str, results: Dict) -> bool:
    try:
        output_path = MACRO_STRUCTURED_DIR / f"{date}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def process_date_range(start_date: str, end_date: str) -> List[Dict]:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    all_results = []
    current = start_dt
    
    while current <= end_dt:
        date_str = current.strftime("%Y-%m-%d")
        if PROCESSING_CONFIG['skip_weekends'] and current.weekday() in [5, 6]:
            print(f"Skipping weekend: {date_str}")
            current += timedelta(days=1)
            continue
        result = process_single_date(date_str)
        all_results.append(result)
        current += timedelta(days=1)
    
    return all_results

def print_summary(results: List[Dict]):
    total_dates = len(results)
    macro_success = sum(1 for r in results if r['agents'].get('macro') is not None)
    market_success = sum(1 for r in results if r['agents'].get('market') is not None)
    narrative_success = sum(1 for r in results if r['agents'].get('narrative') is not None)
    
    print(f"\nTotal dates: {total_dates}")
    print(f"Macro: {macro_success}/{total_dates}")
    print(f"Market: {market_success}/{total_dates}")
    print(f"Narrative: {narrative_success}/{total_dates}")
    
    failed_dates = [r['date'] for r in results if not all(r['agents'].get(agent) for agent in ['macro', 'market', 'narrative'])]
    if failed_dates:
        print(f"\nFailed dates: {', '.join(failed_dates)}")
    else:
        print("\nAll dates processed successfully")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CONCIEL DATA_BOT")
    parser.add_argument('start_date', type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument('end_date', type=str, nargs='?', default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument('--skip-weekends', action='store_true', default=PROCESSING_CONFIG['skip_weekends'])
    parser.add_argument('--skip-missing', action='store_true', default=PROCESSING_CONFIG['skip_missing_data'])
    
    args = parser.parse_args()
    
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format: {args.start_date}")
        return
    
    end_date = args.end_date if args.end_date else args.start_date
    PROCESSING_CONFIG['skip_weekends'] = args.skip_weekends
    PROCESSING_CONFIG['skip_missing_data'] = args.skip_missing
    
    print(f"Processing: {args.start_date} to {end_date}")
    results = process_date_range(args.start_date, end_date)
    print_summary(results)
    print("\ndone")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python run_all.py <start_date> [end_date]")
        print("Example: python run_all.py 2026-01-20")
        result = process_single_date("2026-01-20")
    else:
        main()