import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_DIR, MONTHLY_REF_DIR, AGENT_OUTPUT_DIR, AGENT_CONFIGS, VALIDATION_CONFIG
from memory_manager import MemoryManager

class BaseAgent:
    def __init__(self, agent_name: str):
        if agent_name not in AGENT_CONFIGS:
            raise ValueError(f"Unknown agent: {agent_name}")
        self.name = agent_name
        self.config = AGENT_CONFIGS[agent_name]
        self.memory_manager = MemoryManager(agent_name)
        self.output_dir = AGENT_OUTPUT_DIR / agent_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_today_data(self, date: str) -> Dict[str, str]:
        data = {}
        date_folder = DATA_DIR / date
        if not date_folder.exists():
            raise FileNotFoundError(f"Data folder not found: {date_folder}")
        for filename in self.config['files']:
            file_path = date_folder / filename
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data[filename] = f.read()
            except Exception as e:
                data[filename] = f"[ERROR: {e}]"
        return data
    
    def load_monthly_data(self) -> Optional[str]:
        if not self.config.get('uses_monthly_data', False):
            return None
        monthly_file = MONTHLY_REF_DIR / "monthly_fundamentals.txt"
        if not monthly_file.exists():
            return None
        try:
            with open(monthly_file, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return None
    
    def load_memory(self, date: str) -> Optional[Dict]:
        try:
            if self.memory_manager.is_first_run(date):
                return None
            return self.memory_manager.build_hierarchical_memory(date)
        except:
            return None
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        raise NotImplementedError("Subclass must implement build_prompt()")
    
    def call_llm(self, prompt: str) -> str:
        raise NotImplementedError("Subclass must implement call_llm()")
    
    def validate_output(self, output: Dict) -> bool:
        try:
            required_keys = ['metadata', 'data_snapshot', 'analysis']
            if not all(key in output for key in required_keys):
                return False
            if output['metadata'].get('agent') != self.name:
                return False
            analysis = output['analysis']
            if VALIDATION_CONFIG['require_regime_label'] and 'regime' not in analysis:
                return False
            if VALIDATION_CONFIG['require_confidence_score']:
                if 'confidence' not in analysis:
                    return False
                confidence = analysis['confidence']
                if not (VALIDATION_CONFIG['min_confidence'] <= confidence <= VALIDATION_CONFIG['max_confidence']):
                    return False
            if VALIDATION_CONFIG['require_key_drivers']:
                if 'key_drivers' not in analysis:
                    return False
                num_drivers = len(analysis['key_drivers'])
                if not (VALIDATION_CONFIG['min_key_drivers'] <= num_drivers <= VALIDATION_CONFIG['max_key_drivers']):
                    return False
            return True
        except:
            return False
    
    def save_output(self, date: str, output: Dict) -> bool:
        try:
            output_path = self.output_dir / f"{date}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False
    
    def analyze(self, date: str) -> Optional[Dict]:
        try:
            today_data = self.load_today_data(date)
            monthly_data = self.load_monthly_data()
            if monthly_data:
                today_data['monthly_fundamentals.txt'] = monthly_data
            memory = self.load_memory(date)
            prompt = self.build_prompt(date, today_data, memory)
            response = self.call_llm(prompt)
            output = json.loads(response)
            if not self.validate_output(output):
                return None
            if not self.save_output(date, output):
                return None
            return output
        except Exception as e:
            print(f"Analysis failed: {e}")
            return None

def get_agent_status(agent_name: str, date: str) -> str:
    output_path = AGENT_OUTPUT_DIR / agent_name / f"{date}.json"
    return "Already processed" if output_path.exists() else "Not yet processed"

if __name__ == "__main__":
    test_agent = BaseAgent("macro")
    data = test_agent.load_today_data("2026-01-20")
    print(f"Loaded {len(data)} files")
    print("\ndone")