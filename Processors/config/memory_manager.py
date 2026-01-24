"""
Memory Manager for CONCIEL DATA_BOT Agents
Builds hierarchical temporal memory: OLD → NEW
Three-tier compression: Labels → Summaries → Full Detail
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_OUTPUT_DIR, MEMORY_CONFIG


class MemoryManager:
    """
    Manages hierarchical memory for agents across 30-day windows
    
    Memory Structure:
    - Long context (days 1-9): Regime labels only
    - Medium context (days 10-23): Weekly summaries  
    - Recent context (days 24-30): Full detail
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize memory manager for specific agent
        
        Args:
            agent_name: Name of agent ('macro', 'market', 'narrative')
        """
        self.agent_name = agent_name
        self.output_dir = AGENT_OUTPUT_DIR / agent_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory window configuration
        self.recent_days = MEMORY_CONFIG['recent_days']      # 7
        self.medium_days = MEMORY_CONFIG['medium_days']      # 14
        self.long_days = MEMORY_CONFIG['long_days']          # 9
        self.total_window = MEMORY_CONFIG['total_window']    # 30
    
    
    def load_agent_output(self, date: str) -> Optional[Dict]:
        """
        Load agent's output for a specific date
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Dictionary with agent's output, or None if not found
        """
        output_path = self.output_dir / f"{date}.json"
        
        if not output_path.exists():
            return None
        
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Failed to load {output_path}: {e}")
            return None
    
    
    def build_hierarchical_memory(self, target_date: str) -> Dict:
        """
        Build three-tier hierarchical memory for target date
        
        Args:
            target_date: Date to build memory for (YYYY-MM-DD)
            
        Returns:
            Dictionary with long, medium, and recent context
        """
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        
        # Calculate date boundaries
        day_30_ago = target_dt - timedelta(days=self.total_window)
        day_24_ago = target_dt - timedelta(days=self.recent_days + self.medium_days)
        day_7_ago = target_dt - timedelta(days=self.recent_days)
        
        # Build each tier
        long_context = self._build_long_context(day_30_ago, day_24_ago)
        medium_context = self._build_medium_context(day_24_ago, day_7_ago)
        recent_context = self._build_recent_context(day_7_ago, target_dt)
        
        return {
            "long_context": long_context,
            "medium_context": medium_context,
            "recent_context": recent_context
        }
    
    
    def _build_long_context(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Build long-term context (days 1-9): Regime labels only
        
        Args:
            start_date: Start of long window
            end_date: End of long window
            
        Returns:
            Dictionary with oldest regime labels
        """
        days = []
        current = start_date
        
        while current < end_date:
            date_str = current.strftime("%Y-%m-%d")
            output = self.load_agent_output(date_str)
            
            if output and "analysis" in output and "regime" in output["analysis"]:
                days.append({
                    "date": date_str,
                    "regime": output["analysis"]["regime"]
                })
            
            current += timedelta(days=1)
        
        return {
            "description": f"Days 1-{self.long_days} (oldest, regime labels only)",
            "span": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "days": days
        }
    
    
    def _build_medium_context(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Build medium-term context (days 10-23): Weekly summaries
        
        Args:
            start_date: Start of medium window
            end_date: End of medium window
            
        Returns:
            Dictionary with weekly summaries
        """
        weeks = []
        
        # Split into 7-day chunks
        current_week_start = start_date
        
        while current_week_start < end_date:
            current_week_end = min(current_week_start + timedelta(days=7), end_date)
            
            week_summary = self._compress_week(current_week_start, current_week_end)
            
            if week_summary:
                weeks.append(week_summary)
            
            current_week_start = current_week_end
        
        return {
            "description": f"Days {self.long_days+1}-{self.long_days+self.medium_days} (middle period, weekly summaries)",
            "span": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "weeks": weeks
        }
    
    
    def _compress_week(self, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """
        Compress a week's worth of outputs into a summary
        
        Args:
            start_date: Week start
            end_date: Week end
            
        Returns:
            Dictionary with compressed week summary
        """
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
        
        # Extract most common regime
        regimes = [o["analysis"]["regime"] for o in week_outputs if "analysis" in o and "regime" in o["analysis"]]
        most_common_regime = max(set(regimes), key=regimes.count) if regimes else "UNKNOWN"
        
        # Compress data snapshots
        key_data = self._compress_data_snapshots(week_outputs)
        
        # Compress reasoning
        conclusion = self._compress_reasoning(week_outputs)
        
        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "regime": most_common_regime,
            "key_data": key_data,
            "conclusion": conclusion
        }
    
    
    def _compress_data_snapshots(self, outputs: List[Dict]) -> str:
        """
        Compress multiple data snapshots into one line
        
        Args:
            outputs: List of agent outputs
            
        Returns:
            Compressed string summary
        """
        # Extract key data points (customize per agent)
        data_points = []
        
        for output in outputs:
            if "data_snapshot" in output:
                snapshot = output["data_snapshot"]
                # Get first value from snapshot (simplified)
                if snapshot:
                    first_key = list(snapshot.keys())[0]
                    data_points.append(snapshot[first_key])
        
        # Return first and last (before/after)
        if len(data_points) >= 2:
            return f"{data_points[0]} → {data_points[-1]}"
        elif data_points:
            return data_points[0]
        else:
            return "No data available"
    
    
    def _compress_reasoning(self, outputs: List[Dict]) -> str:
        """
        Compress multiple reasoning strings into one sentence
        
        Args:
            outputs: List of agent outputs
            
        Returns:
            Compressed reasoning string
        """
        reasoning_list = []
        
        for output in outputs:
            if "analysis" in output and "reasoning" in output["analysis"]:
                reasoning_list.append(output["analysis"]["reasoning"])
        
        if not reasoning_list:
            return "No analysis available"
        
        # Return the last (most recent) reasoning as summary
        return reasoning_list[-1]
    
    
    def _build_recent_context(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Build recent context (days 24-30): Full detail
        
        Args:
            start_date: Start of recent window
            end_date: End of recent window (today)
            
        Returns:
            Dictionary with full recent outputs
        """
        days = []
        current = start_date
        
        while current < end_date:
            date_str = current.strftime("%Y-%m-%d")
            output = self.load_agent_output(date_str)
            
            if output:
                # Include full output
                days.append({
                    "date": date_str,
                    "data_snapshot": output.get("data_snapshot", {}),
                    "analysis": output.get("analysis", {})
                })
            
            current += timedelta(days=1)
        
        return {
            "description": f"Days {self.long_days+self.medium_days+1}-{self.total_window} (last {self.recent_days} days, full detail)",
            "span": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "days": days
        }
    
    
    def is_first_run(self, target_date: str) -> bool:
        """
        Check if this is the first analysis (no memory exists)
        
        Args:
            target_date: Date to check
            
        Returns:
            True if no prior outputs exist
        """
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        yesterday = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Check if yesterday's output exists
        return self.load_agent_output(yesterday) is None
    
    
    def get_memory_summary(self, target_date: str) -> str:
        """
        Get human-readable summary of memory status
        
        Args:
            target_date: Date to check memory for
            
        Returns:
            Summary string
        """
        if self.is_first_run(target_date):
            return "🆕 First run - no historical memory"
        
        memory = self.build_hierarchical_memory(target_date)
        
        long_days = len(memory["long_context"]["days"])
        medium_weeks = len(memory["medium_context"]["weeks"])
        recent_days = len(memory["recent_context"]["days"])
        
        return f"📊 Memory loaded: {long_days} long days, {medium_weeks} medium weeks, {recent_days} recent days"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_hierarchical_memory(agent_name: str, target_date: str) -> Dict:
    """
    Convenience function to build memory for an agent
    
    Args:
        agent_name: Name of agent
        target_date: Date to build memory for
        
    Returns:
        Hierarchical memory dictionary
    """
    manager = MemoryManager(agent_name)
    return manager.build_hierarchical_memory(target_date)


def get_memory_summary(agent_name: str, target_date: str) -> str:
    """
    Get memory summary for an agent
    
    Args:
        agent_name: Name of agent
        target_date: Date to check
        
    Returns:
        Summary string
    """
    manager = MemoryManager(agent_name)
    return manager.get_memory_summary(target_date)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MEMORY MANAGER TEST")
    print("=" * 60)
    print()
    
    # Test with a sample date
    test_agent = "macro"
    test_date = "2026-01-24"
    
    manager = MemoryManager(test_agent)
    
    print(f"Agent: {test_agent}")
    print(f"Target date: {test_date}")
    print()
    
    # Check if first run
    if manager.is_first_run(test_date):
        print("🆕 This would be the first run (no prior data)")
    else:
        print("📊 Building hierarchical memory...")
        print()
        
        memory = manager.build_hierarchical_memory(test_date)
        
        print("LONG CONTEXT:")
        print(f"  {memory['long_context']['description']}")
        print(f"  Span: {memory['long_context']['span']}")
        print(f"  Days found: {len(memory['long_context']['days'])}")
        print()
        
        print("MEDIUM CONTEXT:")
        print(f"  {memory['medium_context']['description']}")
        print(f"  Span: {memory['medium_context']['span']}")
        print(f"  Weeks found: {len(memory['medium_context']['weeks'])}")
        print()
        
        print("RECENT CONTEXT:")
        print(f"  {memory['recent_context']['description']}")
        print(f"  Span: {memory['recent_context']['span']}")
        print(f"  Days found: {len(memory['recent_context']['days'])}")
        print()
    
    print(get_memory_summary(test_agent, test_date))
    print()
    print("=" * 60)