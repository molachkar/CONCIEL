"""
Orchestrator for CONCIEL DATA_BOT Agents
Runs all 3 agents (macro, market, narrative) for specified dates
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DATA_DIR,
    MACRO_STRUCTURED_DIR,
    PROCESSING_CONFIG,
    OUTPUT_CONFIG
)
from agent_macro import MacroAgent
from agent_market import MarketAgent
from agent_narrative import NarrativeAgent


def process_single_date(date: str) -> Dict:
    """
    Run all agents for a single date
    
    Args:
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dictionary with results from all agents
    """
    print(f"\n{'='*60}")
    print(f"📅 PROCESSING DATE: {date}")
    print(f"{'='*60}\n")
    
    results = {
        'date': date,
        'timestamp': datetime.now().isoformat(),
        'agents': {}
    }
    
    # Check if data folder exists
    date_folder = DATA_DIR / date
    if not date_folder.exists():
        print(f"⚠️  Data folder not found: {date_folder}")
        if PROCESSING_CONFIG['skip_missing_data']:
            print(f"⏭️  Skipping {date}")
            return results
        else:
            print(f"❌ Aborting (skip_missing_data=False)")
            return results
    
    # Agent 1: MACRO
    print("\n" + "▶️ " * 20)
    print("RUNNING MACRO AGENT")
    print("▶️ " * 20)
    try:
        macro_agent = MacroAgent()
        macro_result = macro_agent.analyze(date)
        results['agents']['macro'] = macro_result
    except Exception as e:
        print(f"❌ MACRO agent failed: {e}")
        results['agents']['macro'] = None
    
    # Agent 2: MARKET
    print("\n" + "▶️ " * 20)
    print("RUNNING MARKET AGENT")
    print("▶️ " * 20)
    try:
        market_agent = MarketAgent()
        market_result = market_agent.analyze(date)
        results['agents']['market'] = market_result
    except Exception as e:
        print(f"❌ MARKET agent failed: {e}")
        results['agents']['market'] = None
    
    # Agent 3: NARRATIVE
    print("\n" + "▶️ " * 20)
    print("RUNNING NARRATIVE AGENT")
    print("▶️ " * 20)
    try:
        narrative_agent = NarrativeAgent()
        narrative_result = narrative_agent.analyze(date)
        results['agents']['narrative'] = narrative_result
    except Exception as e:
        print(f"❌ NARRATIVE agent failed: {e}")
        results['agents']['narrative'] = None
    
    # Check success
    success_count = sum(1 for r in results['agents'].values() if r is not None)
    total_count = len(results['agents'])
    
    print(f"\n{'='*60}")
    if success_count == total_count:
        print(f"✅ ALL AGENTS COMPLETED ({success_count}/{total_count})")
    elif success_count > 0:
        print(f"⚠️  PARTIAL SUCCESS ({success_count}/{total_count} agents)")
    else:
        print(f"❌ ALL AGENTS FAILED")
    print(f"{'='*60}\n")
    
    # Save combined output
    if OUTPUT_CONFIG['save_combined_output'] and success_count > 0:
        save_combined_output(date, results)
    
    return results


def save_combined_output(date: str, results: Dict) -> bool:
    """
    Save combined output from all agents
    
    Args:
        date: Target date
        results: Combined results dictionary
        
    Returns:
        True if saved successfully
    """
    try:
        output_path = MACRO_STRUCTURED_DIR / f"{date}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Combined output saved: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save combined output: {e}")
        return False


def process_date_range(start_date: str, end_date: str) -> List[Dict]:
    """
    Process a range of dates sequentially
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), inclusive
        
    Returns:
        List of results for each date
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    all_results = []
    current = start_dt
    
    while current <= end_dt:
        date_str = current.strftime("%Y-%m-%d")
        
        # Skip weekends if configured
        if PROCESSING_CONFIG['skip_weekends']:
            if current.weekday() in [5, 6]:  # Saturday, Sunday
                print(f"\n⏭️  Skipping weekend: {date_str}")
                current += timedelta(days=1)
                continue
        
        # Process the date
        result = process_single_date(date_str)
        all_results.append(result)
        
        # Move to next day
        current += timedelta(days=1)
    
    return all_results


def print_summary(results: List[Dict]):
    """
    Print summary of processing results
    
    Args:
        results: List of results from process_date_range
    """
    print("\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print()
    
    total_dates = len(results)
    macro_success = sum(1 for r in results if r['agents'].get('macro') is not None)
    market_success = sum(1 for r in results if r['agents'].get('market') is not None)
    narrative_success = sum(1 for r in results if r['agents'].get('narrative') is not None)
    
    print(f"Total dates processed: {total_dates}")
    print()
    print(f"MACRO agent:     {macro_success}/{total_dates} ({'✅' if macro_success == total_dates else '⚠️'})")
    print(f"MARKET agent:    {market_success}/{total_dates} ({'✅' if market_success == total_dates else '⚠️'})")
    print(f"NARRATIVE agent: {narrative_success}/{total_dates} ({'✅' if narrative_success == total_dates else '⚠️'})")
    print()
    
    # List failed dates
    failed_dates = [
        r['date'] for r in results 
        if not all(r['agents'].get(agent) for agent in ['macro', 'market', 'narrative'])
    ]
    
    if failed_dates:
        print(f"⚠️  Dates with failures:")
        for date in failed_dates:
            print(f"   - {date}")
    else:
        print("✅ All dates processed successfully!")
    
    print()
    print("=" * 60)


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """
    Main entry point for command line usage
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CONCIEL DATA_BOT - Run all agents for specified dates"
    )
    
    parser.add_argument(
        'start_date',
        type=str,
        help="Start date (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        'end_date',
        type=str,
        nargs='?',
        default=None,
        help="End date (YYYY-MM-DD), defaults to start_date"
    )
    
    parser.add_argument(
        '--skip-weekends',
        action='store_true',
        default=PROCESSING_CONFIG['skip_weekends'],
        help="Skip Saturday and Sunday"
    )
    
    parser.add_argument(
        '--skip-missing',
        action='store_true',
        default=PROCESSING_CONFIG['skip_missing_data'],
        help="Skip dates with missing data folders"
    )
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid start_date format: {args.start_date}")
        print(f"   Expected format: YYYY-MM-DD")
        return
    
    # Set end date
    end_date = args.end_date if args.end_date else args.start_date
    
    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid end_date format: {end_date}")
        print(f"   Expected format: YYYY-MM-DD")
        return
    
    # Update config
    PROCESSING_CONFIG['skip_weekends'] = args.skip_weekends
    PROCESSING_CONFIG['skip_missing_data'] = args.skip_missing
    
    print("=" * 60)
    print("🤖 CONCIEL DATA_BOT - ORCHESTRATOR")
    print("=" * 60)
    print()
    print(f"Date range: {args.start_date} to {end_date}")
    print(f"Skip weekends: {args.skip_weekends}")
    print(f"Skip missing data: {args.skip_missing}")
    print()
    
    # Process dates
    results = process_date_range(args.start_date, end_date)
    
    # Print summary
    print_summary(results)
    
    print("\n✅ Processing complete!")


if __name__ == "__main__":
    # If run directly with no args, show usage
    if len(sys.argv) == 1:
        print("=" * 60)
        print("🤖 CONCIEL DATA_BOT - ORCHESTRATOR")
        print("=" * 60)
        print()
        print("Usage:")
        print("  python run_all.py <start_date> [end_date]")
        print()
        print("Examples:")
        print("  python run_all.py 2026-01-20")
        print("  python run_all.py 2026-01-20 2026-01-24")
        print("  python run_all.py 2026-01-01 2026-01-31 --skip-weekends")
        print()
        print("Arguments:")
        print("  start_date        Required: Start date (YYYY-MM-DD)")
        print("  end_date          Optional: End date (YYYY-MM-DD)")
        print("  --skip-weekends   Skip Saturday/Sunday")
        print("  --skip-missing    Skip dates with no data folder")
        print()
        print("=" * 60)
        print()
        
        # Run test
        print("🧪 Running test with 2026-01-20...")
        print()
        result = process_single_date("2026-01-20")
        
    else:
        main()