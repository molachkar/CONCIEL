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
    """Process all agents for a single date with minimal output"""
    results = {
        'date': date,
        'timestamp': datetime.now().isoformat(),
        'agents': {}
    }
    
    date_folder = DATA_DIR / date
    if not date_folder.exists():
        if PROCESSING_CONFIG['skip_missing_data']:
            return results
        return results
    
    # Process macro agent (output is handled by agent itself)
    try:
        macro_agent = MacroAgent()
        results['agents']['macro'] = macro_agent.analyze(date)
    except Exception:
        results['agents']['macro'] = None
    
    # Process market agent (output is handled by agent itself)
    try:
        market_agent = MarketAgent()
        results['agents']['market'] = market_agent.analyze(date)
    except Exception:
        results['agents']['market'] = None
    
    # Process narrative agent (output is handled by agent itself)
    try:
        narrative_agent = NarrativeAgent()
        results['agents']['narrative'] = narrative_agent.analyze(date)
    except Exception:
        results['agents']['narrative'] = None
    
    # Save combined output silently
    success_count = sum(1 for r in results['agents'].values() if r is not None)
    if OUTPUT_CONFIG['save_combined_output'] and success_count > 0:
        save_combined_output(date, results)
    
    return results

def save_combined_output(date: str, results: Dict) -> bool:
    """Save combined output without printing"""
    try:
        output_path = MACRO_STRUCTURED_DIR / f"{date}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def process_date_range(start_date: str, end_date: str) -> List[Dict]:
    """Process date range with minimal header output"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    all_results = []
    current = start_dt
    
    # Only show header for multi-day processing
    if start_date != end_date:
        print(f"\nProcessing {start_date} to {end_date}\n")
    
    while current <= end_dt:
        date_str = current.strftime("%Y-%m-%d")
        result = process_single_date(date_str)
        all_results.append(result)
        current += timedelta(days=1)
    
    return all_results

def print_summary(results: List[Dict]):
    """Print concise summary"""
    total_dates = len(results)
    macro_success = sum(1 for r in results if r['agents'].get('macro') is not None)
    market_success = sum(1 for r in results if r['agents'].get('market') is not None)
    narrative_success = sum(1 for r in results if r['agents'].get('narrative') is not None)
    
    # Only print summary for multi-day runs
    if total_dates > 1:
        print(f"\n{'='*50}")
        print(f"SUMMARY: {total_dates} dates processed")
        print(f"{'='*50}")
        print(f"Macro:     {macro_success}/{total_dates}")
        print(f"Market:    {market_success}/{total_dates}")
        print(f"Narrative: {narrative_success}/{total_dates}")
        
        failed_dates = [
            r['date'] for r in results 
            if not any(r['agents'].get(agent) for agent in ['macro', 'market', 'narrative'])
        ]
        
        if failed_dates:
            print(f"\nFailed dates ({len(failed_dates)}): {', '.join(failed_dates)}")
        
        print(f"{'='*50}\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CONCIEL Processors - Run all agents")
    parser.add_argument('start_date', type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument('end_date', type=str, nargs='?', default=None, help="End date (YYYY-MM-DD), defaults to start_date")
    parser.add_argument('--skip-missing', action='store_true', default=PROCESSING_CONFIG['skip_missing_data'], help="Skip dates with missing data")
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format: {args.start_date}")
        print("Use format: YYYY-MM-DD")
        return
    
    end_date = args.end_date if args.end_date else args.start_date
    
    # Update config based on args
    PROCESSING_CONFIG['skip_missing_data'] = args.skip_missing
    
    results = process_date_range(args.start_date, end_date)
    print_summary(results)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python run_all.py <start_date> [end_date]")
        print("\nExamples:")
        print("  python run_all.py 2026-01-20")
        print("  python run_all.py 2026-01-20 2026-01-31")
        print("\nRunning test with 2026-01-20...\n")
        result = process_single_date("2026-01-20")
    else:
        main()