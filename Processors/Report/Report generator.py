import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.append(str(Path(__file__).parent.parent / "config"))
from config_report import MACRO_STRUCTURED_DIR, get_report_path, CHARS_PER_PAGE

sys.path.append(str(Path(__file__).parent))
from report_agent import MacroReportAgent, MarketReportAgent, NarrativeReportAgent


def get_available_dates() -> List[Path]:
    if not MACRO_STRUCTURED_DIR.exists():
        return []
    json_files = list(MACRO_STRUCTURED_DIR.glob("*.json"))
    json_files.sort()
    return json_files


def parse_date_range(args: List[str]) -> Tuple[str, str]:
    if len(args) >= 3:
        return args[1], args[2]
    elif len(args) == 2:
        return args[1], args[1]
    else:
        return None, None


def filter_files_by_range(json_files: List[Path], start_date: str, end_date: str) -> List[Path]:
    if not start_date or not end_date:
        return json_files
    filtered = []
    for file_path in json_files:
        date_str = file_path.stem
        if start_date <= date_str <= end_date:
            filtered.append(file_path)
    return filtered


def compile_final_report(agent_outputs: List[str], start_date: str, end_date: str, num_days: int) -> str:
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    
    header = f"""GOLD MARKET INTELLIGENCE REPORT
Analysis Period: {start_date} to {end_date} ({num_days} days)
Generation Date: {gen_time}

"""
    
    divider = "\n\n" + "="*70 + "\n\n"
    footer = "\n\n" + "="*70 + "\nEND OF REPORT\n" + "="*70 + "\n"
    
    return header + agent_outputs[0] + divider + agent_outputs[1] + divider + agent_outputs[2] + footer


def main():
    print("GOLD MARKET INTELLIGENCE REPORT GENERATOR\n")
    
    if not MACRO_STRUCTURED_DIR.exists():
        print(f"ERROR: Data directory not found: {MACRO_STRUCTURED_DIR}")
        return 1
    
    start_date, end_date = parse_date_range(sys.argv)
    json_files = get_available_dates()
    
    if not json_files:
        print(f"No JSON files found in {MACRO_STRUCTURED_DIR}")
        return 1
    
    if start_date and end_date:
        json_files = filter_files_by_range(json_files, start_date, end_date)
        if not json_files:
            print(f"No files in range {start_date} to {end_date}")
            return 1
    else:
        start_date = json_files[0].stem
        end_date = json_files[-1].stem
    
    num_days = len(json_files)
    
    print(f"Date range: {start_date} to {end_date}")
    print(f"Files: {num_days}")
    print(f"Output: {get_report_path(start_date, end_date).name}\n")
    
    agent1 = MacroReportAgent()
    agent2 = MarketReportAgent()
    agent3 = NarrativeReportAgent()
    
    print("Loading data")
    all_data = []
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_data.append(json.load(f))
        except Exception as e:
            print(f"Warning: Failed to load {file_path.name}")
    
    if not all_data:
        print("Failed to load data files")
        return 1
    
    all_data.sort(key=lambda x: x.get('date', ''))
    print(f"Loaded {len(all_data)} days\n")
    
    agent_outputs = []
    
    try:
        print("Agent 1: Macro regime analysis")
        output1 = agent1.generate(all_data, [], start_date, end_date)
        agent_outputs.append(output1)
        
        print("\nAgent 2: Market technical analysis")
        output2 = agent2.generate(all_data, agent_outputs, start_date, end_date)
        agent_outputs.append(output2)
        
        print("\nAgent 3: Narrative synthesis")
        output3 = agent3.generate(all_data, agent_outputs, start_date, end_date)
        agent_outputs.append(output3)
        
    except Exception as e:
        print(f"\nERROR: Generation failed: {e}")
        return 1
    
    print("\nCompiling report")
    final_report = compile_final_report(agent_outputs, start_date, end_date, num_days)
    
    report_path = get_report_path(start_date, end_date)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
        print(f"Saved: {report_path}")
    except Exception as e:
        print(f"ERROR: Save failed: {e}")
        return 1
    
    total_chars = len(final_report)
    pages = total_chars / CHARS_PER_PAGE
    print(f"\nComplete")
    print(f"Length: {total_chars:,} chars")
    print(f"Pages: ~{pages:.1f}\n")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)