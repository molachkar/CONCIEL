import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_OUTPUT_DIR, MEMORY_CONFIG

class MemoryManager:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.output_dir = AGENT_OUTPUT_DIR / agent_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.recent_days = MEMORY_CONFIG['recent_days']
        self.medium_days = MEMORY_CONFIG['medium_days']
        self.long_days = MEMORY_CONFIG['long_days']
        self.total_window = MEMORY_CONFIG['total_window']
    
    def load_agent_output(self, date: str) -> Optional[Dict]:
        output_path = self.output_dir / f"{date}.json"
        if not output_path.exists():
            return None
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def build_hierarchical_memory(self, target_date: str) -> Dict:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_30_ago = target_dt - timedelta(days=self.total_window)
        day_24_ago = target_dt - timedelta(days=self.recent_days + self.medium_days)
        day_7_ago = target_dt - timedelta(days=self.recent_days)
        return {"long_context": self._build_long_context(day_30_ago, day_24_ago), "medium_context": self._build_medium_context(day_24_ago, day_7_ago), "recent_context": self._build_recent_context(day_7_ago, target_dt)}
    
    def _build_long_context(self, start_date: datetime, end_date: datetime) -> Dict:
        days = []
        current = start_date
        while current < end_date:
            date_str = current.strftime("%Y-%m-%d")
            output = self.load_agent_output(date_str)
            if output and "analysis" in output and "regime" in output["analysis"]:
                days.append({"date": date_str, "regime": output["analysis"]["regime"]})
            current += timedelta(days=1)
        return {"description": f"Days 1-{self.long_days} (oldest, regime labels only)", "span": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", "days": days}
    
    def _build_medium_context(self, start_date: datetime, end_date: datetime) -> Dict:
        weeks = []
        current_week_start = start_date
        while current_week_start < end_date:
            current_week_end = min(current_week_start + timedelta(days=7), end_date)
            week_summary = self._compress_week(current_week_start, current_week_end)
            if week_summary:
                weeks.append(week_summary)
            current_week_start = current_week_end
        return {"description": f"Days {self.long_days+1}-{self.long_days+self.medium_days} (middle period, weekly summaries)", "span": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", "weeks": weeks}
    
    def _compress_week(self, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        week_outputs = []
        current = start_date
        while current < end_date:
            date_str = current.strftime("%Y-%m-%d")
            output = self.load_agent_output(date_str)
            if output:
                week_outputs.append(output)
            current += timedelta(days=1)
        if not week_outputs:
            return None
        regimes = [o["analysis"]["regime"] for o in week_outputs if "analysis" in o and "regime" in o["analysis"]]
        most_common_regime = max(set(regimes), key=regimes.count) if regimes else "UNKNOWN"
        return {"period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", "regime": most_common_regime, "key_data": self._compress_data_snapshots(week_outputs), "conclusion": self._compress_reasoning(week_outputs)}
    
    def _compress_data_snapshots(self, outputs: List[Dict]) -> str:
        data_points = []
        for output in outputs:
            if "data_snapshot" in output and output["data_snapshot"]:
                first_key = list(output["data_snapshot"].keys())[0]
                data_points.append(output["data_snapshot"][first_key])
        if len(data_points) >= 2:
            return f"{data_points[0]} → {data_points[-1]}"
        return data_points[0] if data_points else "No data available"
    
    def _compress_reasoning(self, outputs: List[Dict]) -> str:
        reasoning_list = [output["analysis"]["reasoning"] for output in outputs if "analysis" in output and "reasoning" in output["analysis"]]
        return reasoning_list[-1] if reasoning_list else "No analysis available"
    
    def _build_recent_context(self, start_date: datetime, end_date: datetime) -> Dict:
        days = []
        current = start_date
        while current < end_date:
            date_str = current.strftime("%Y-%m-%d")
            output = self.load_agent_output(date_str)
            if output:
                days.append({"date": date_str, "data_snapshot": output.get("data_snapshot", {}), "analysis": output.get("analysis", {})})
            current += timedelta(days=1)
        return {"description": f"Days {self.long_days+self.medium_days+1}-{self.total_window} (last {self.recent_days} days, full detail)", "span": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", "days": days}
    
    def is_first_run(self, target_date: str) -> bool:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        yesterday = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.load_agent_output(yesterday) is None
    
    def get_memory_summary(self, target_date: str) -> str:
        if self.is_first_run(target_date):
            return "First run - no historical memory"
        memory = self.build_hierarchical_memory(target_date)
        long_days = len(memory["long_context"]["days"])
        medium_weeks = len(memory["medium_context"]["weeks"])
        recent_days = len(memory["recent_context"]["days"])
        return f"Memory loaded: {long_days} long days, {medium_weeks} medium weeks, {recent_days} recent days"

def build_hierarchical_memory(agent_name: str, target_date: str) -> Dict:
    manager = MemoryManager(agent_name)
    return manager.build_hierarchical_memory(target_date)

def get_memory_summary(agent_name: str, target_date: str) -> str:
    manager = MemoryManager(agent_name)
    return manager.get_memory_summary(target_date)

if __name__ == "__main__":
    test_agent = "macro"
    test_date = "2026-01-24"
    manager = MemoryManager(test_agent)
    if manager.is_first_run(test_date):
        print("First run (no prior data)")
    else:
        memory = manager.build_hierarchical_memory(test_date)
        print(f"Long: {len(memory['long_context']['days'])} days")
        print(f"Medium: {len(memory['medium_context']['weeks'])} weeks")
        print(f"Recent: {len(memory['recent_context']['days'])} days")
    print(get_memory_summary(test_agent, test_date))
    print("\ndone")