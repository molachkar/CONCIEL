"""
Base Agent Class for CONCIEL DATA_BOT
Shared functionality: file loading, memory, validation, saving
All agents (macro, market, narrative) inherit from this
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DATA_DIR, 
    MONTHLY_REF_DIR, 
    AGENT_OUTPUT_DIR,
    AGENT_CONFIGS,
    VALIDATION_CONFIG
)
from memory_manager import MemoryManager


class BaseAgent:
    """
    Base class for all CONCIEL agents
    
    Handles:
    - Loading daily data files
    - Loading monthly reference data
    - Building hierarchical memory
    - Validating outputs
    - Saving results
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize base agent
        
        Args:
            agent_name: Name of agent ('macro', 'market', 'narrative')
        """
        if agent_name not in AGENT_CONFIGS:
            raise ValueError(f"Unknown agent: {agent_name}. Valid: {list(AGENT_CONFIGS.keys())}")
        
        self.name = agent_name
        self.config = AGENT_CONFIGS[agent_name]
        self.memory_manager = MemoryManager(agent_name)
        
        # Create output directory
        self.output_dir = AGENT_OUTPUT_DIR / agent_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ {self.name.upper()} agent initialized")
        print(f"   Model: {self.config['model']}")
        print(f"   Files: {', '.join(self.config['files'])}")
        print(f"   Temperature: {self.config['temperature']}")
    
    
    def load_today_data(self, date: str) -> Dict[str, str]:
        """
        Load all required data files for target date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary mapping filename -> file content
            
        Raises:
            FileNotFoundError: If required files are missing
        """
        data = {}
        date_folder = DATA_DIR / date
        
        if not date_folder.exists():
            raise FileNotFoundError(f"Data folder not found: {date_folder}")
        
        # Load each required file
        for filename in self.config['files']:
            file_path = date_folder / filename
            
            if not file_path.exists():
                print(f"⚠️  Missing file: {file_path}")
                data[filename] = f"[FILE NOT FOUND: {filename}]"
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    data[filename] = content
                    print(f"   📄 Loaded {filename} ({len(content)} chars)")
            except Exception as e:
                print(f"⚠️  Error reading {filename}: {e}")
                data[filename] = f"[ERROR READING FILE: {e}]"
        
        return data
    
    
    def load_monthly_data(self) -> Optional[str]:
        """
        Load monthly reference data (for macro agent only)
        
        Returns:
            Monthly data content, or None if not applicable/not found
        """
        if not self.config.get('uses_monthly_data', False):
            return None
        
        monthly_file = MONTHLY_REF_DIR / "monthly_fundamentals.txt"
        
        if not monthly_file.exists():
            print(f"⚠️  Monthly data not found: {monthly_file}")
            return None
        
        try:
            with open(monthly_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   📊 Loaded monthly data ({len(content)} chars)")
                return content
        except Exception as e:
            print(f"⚠️  Error reading monthly data: {e}")
            return None
    
    
    def load_memory(self, date: str) -> Optional[Dict]:
        """
        Build hierarchical memory for target date
        
        Args:
            date: Target date (YYYY-MM-DD)
            
        Returns:
            Hierarchical memory dict, or None if first run
        """
        try:
            if self.memory_manager.is_first_run(date):
                print(f"   🆕 First run - no historical memory")
                return None
            
            memory = self.memory_manager.build_hierarchical_memory(date)
            summary = self.memory_manager.get_memory_summary(date)
            print(f"   {summary}")
            
            return memory
            
        except Exception as e:
            print(f"⚠️  Memory loading failed: {e}")
            return None
    
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        """
        Build prompt for LLM (must be implemented by subclass)
        
        Args:
            date: Target date
            today_data: Today's data files
            memory: Historical memory (or None)
            
        Returns:
            Prompt string
        """
        raise NotImplementedError("Subclass must implement build_prompt()")
    
    
    def call_llm(self, prompt: str) -> str:
        """
        Call LLM API (must be implemented by subclass)
        
        Args:
            prompt: Full prompt text
            
        Returns:
            LLM response (should be JSON)
        """
        raise NotImplementedError("Subclass must implement call_llm()")
    
    
    def validate_output(self, output: Dict) -> bool:
        """
        Validate agent output structure
        
        Args:
            output: Parsed JSON output from LLM
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required top-level keys
            required_keys = ['metadata', 'data_snapshot', 'analysis']
            for key in required_keys:
                if key not in output:
                    print(f"❌ Missing required key: {key}")
                    return False
            
            # Validate metadata
            metadata = output['metadata']
            if metadata.get('agent') != self.name:
                print(f"❌ Agent mismatch: expected {self.name}, got {metadata.get('agent')}")
                return False
            
            # Validate analysis
            analysis = output['analysis']
            
            if VALIDATION_CONFIG['require_regime_label']:
                if 'regime' not in analysis:
                    print(f"❌ Missing regime label")
                    return False
            
            if VALIDATION_CONFIG['require_confidence_score']:
                if 'confidence' not in analysis:
                    print(f"❌ Missing confidence score")
                    return False
                
                confidence = analysis['confidence']
                if not (VALIDATION_CONFIG['min_confidence'] <= confidence <= VALIDATION_CONFIG['max_confidence']):
                    print(f"❌ Invalid confidence: {confidence}")
                    return False
            
            if VALIDATION_CONFIG['require_key_drivers']:
                if 'key_drivers' not in analysis:
                    print(f"❌ Missing key_drivers")
                    return False
                
                num_drivers = len(analysis['key_drivers'])
                if num_drivers < VALIDATION_CONFIG['min_key_drivers']:
                    print(f"❌ Too few key drivers: {num_drivers}")
                    return False
                if num_drivers > VALIDATION_CONFIG['max_key_drivers']:
                    print(f"❌ Too many key drivers: {num_drivers}")
                    return False
            
            print(f"   ✅ Output validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False
    
    
    def save_output(self, date: str, output: Dict) -> bool:
        """
        Save agent output to JSON file
        
        Args:
            date: Target date (YYYY-MM-DD)
            output: Validated output dictionary
            
        Returns:
            True if saved successfully
        """
        try:
            output_path = self.output_dir / f"{date}.json"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            print(f"   💾 Saved to {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save output: {e}")
            return False
    
    
    def analyze(self, date: str) -> Optional[Dict]:
        """
        Main analysis pipeline
        
        Args:
            date: Target date (YYYY-MM-DD)
            
        Returns:
            Agent output dictionary, or None if failed
        """
        print(f"\n{'='*60}")
        print(f"🤖 {self.name.upper()} AGENT - {date}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Load today's data
            print("\n📂 Loading today's data...")
            today_data = self.load_today_data(date)
            
            # Step 2: Load monthly data (if applicable)
            monthly_data = self.load_monthly_data()
            if monthly_data:
                today_data['monthly_fundamentals.txt'] = monthly_data
            
        except FileNotFoundError as e:
            print(f"❌ Data loading failed: {e}")
            return None
        
        try:
            # Step 3: Load memory
            print("\n🧠 Loading memory...")
            memory = self.load_memory(date)
            
        except Exception as e:
            print(f"⚠️  Memory loading error (continuing with None): {e}")
            memory = None
        
        try:
            # Step 4: Build prompt
            print("\n📝 Building prompt...")
            prompt = self.build_prompt(date, today_data, memory)
            print(f"   Prompt length: {len(prompt)} chars")
            
            # Step 5: Call LLM
            print("\n🤖 Calling LLM...")
            response = self.call_llm(prompt)
            print(f"   Response length: {len(response)} chars")
            
            # Step 6: Parse JSON
            print("\n🔍 Parsing response...")
            output = json.loads(response)
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Raw response (first 500 chars):\n{response[:500]}")
            return None
        except Exception as e:
            print(f"❌ LLM processing failed: {e}")
            return None
        
        try:
            # Step 7: Validate output
            print("\n✅ Validating output...")
            if not self.validate_output(output):
                print(f"❌ Validation failed")
                return None
            
            # Step 8: Save output
            print("\n💾 Saving output...")
            if not self.save_output(date, output):
                print(f"❌ Save failed")
                return None
            
            print(f"\n{'='*60}")
            print(f"✅ {self.name.upper()} AGENT COMPLETED SUCCESSFULLY")
            print(f"{'='*60}\n")
            
            return output
            
        except Exception as e:
            print(f"❌ Post-processing failed: {e}")
            return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_agent_status(agent_name: str, date: str) -> str:
    """
    Check if agent has already processed a date
    
    Args:
        agent_name: Name of agent
        date: Date to check
        
    Returns:
        Status string
    """
    output_path = AGENT_OUTPUT_DIR / agent_name / f"{date}.json"
    
    if output_path.exists():
        return f"✅ Already processed"
    else:
        return f"⏳ Not yet processed"


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BASE AGENT TEST")
    print("=" * 60)
    print()
    
    # Test initialization
    try:
        test_agent = BaseAgent("macro")
        print(f"\n✅ BaseAgent initialized successfully")
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
    
    # Test data loading
    test_date = "2026-01-20"
    print(f"\n📊 Testing data loading for {test_date}...")
    
    try:
        data = test_agent.load_today_data(test_date)
        print(f"✅ Loaded {len(data)} files")
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
    
    print("\n" + "=" * 60)