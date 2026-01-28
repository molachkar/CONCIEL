import json
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import API_KEYS, AGENT_CONFIGS, DATA_DIR, MONTHLY_REF_DIR, MONTHLY_DATA_FILE
from base_agent import BaseAgent

class MacroAgent(BaseAgent):
    def __init__(self):
        super().__init__("macro")
        self.api_key = API_KEYS.get("cerebras", "")
        self.api_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.fundamentals_cache = {}
    
    def analyze(self, date: str) -> Optional[Dict]:
        """Override analyze to handle forward-fill and monthly context"""
        try:
            # Load today's files
            today_data = super().load_today_data(date)
            
            # Load and update monthly data
            monthly_data = super().load_monthly_data()
            if monthly_data:
                today_data['monthly_data.txt'] = monthly_data
                # Check if monthly data was updated and update reference file if needed
                self.update_monthly_reference_if_new(date, monthly_data)
            
            # Forward-fill fundamentals if needed
            today_data = self.forward_fill_fundamentals(date, today_data)
            
            # Extract monthly context for reminder
            monthly_context = self.extract_monthly_context(monthly_data)
            
            # Check minimum data requirements
            has_fundamentals = today_data.get('fundamentals.txt') and today_data['fundamentals.txt'].strip() not in ['N/A', '', 'No data', '[ERROR']
            
            if not has_fundamentals:
                print(f"⚠️  MACRO AGENT: Skipping {date} - no fundamentals data available")
                return None
            
            # Load memory
            memory = super().load_memory(date)
            
            # Build prompt with monthly context
            prompt = self.build_prompt(date, today_data, memory, monthly_context)
            
            # Call LLM
            llm_response = self.call_llm(prompt)
            
            # Parse and validate
            result = json.loads(llm_response)
            
            # Validate output
            if not super().validate_output(result):
                print(f"❌ MACRO AGENT: {date} - Output validation failed")
                return None
            
            # Save output
            if not super().save_output(date, result):
                print(f"❌ MACRO AGENT: {date} - Failed to save output")
                return None
            
            print(f"✅ MACRO AGENT: {date} completed")
            return result
            
        except Exception as e:
            print(f"❌ MACRO AGENT ERROR on {date}: {e}")
            return None
    
    def extract_monthly_context(self, monthly_data: Optional[str]) -> str:
        """Extract key monthly metrics (CPI, PCE, PPI) and their dates"""
        if not monthly_data:
            return "No monthly data available"
        
        context_parts = []
        
        # Look for CPI
        cpi_match = re.search(r'CPI[:\s]+([0-9.]+)%?\s*.*?(\d{4}-\d{2}-\d{2})?', monthly_data, re.IGNORECASE)
        if cpi_match:
            cpi_val = cpi_match.group(1)
            cpi_date = cpi_match.group(2) if cpi_match.group(2) else "date unknown"
            context_parts.append(f"CPI: {cpi_val}% (as of {cpi_date})")
        
        # Look for PCE
        pce_match = re.search(r'PCE[:\s]+([0-9.]+)%?\s*.*?(\d{4}-\d{2}-\d{2})?', monthly_data, re.IGNORECASE)
        if pce_match:
            pce_val = pce_match.group(1)
            pce_date = pce_match.group(2) if pce_match.group(2) else "date unknown"
            context_parts.append(f"PCE: {pce_val}% (as of {pce_date})")
        
        # Look for PPI
        ppi_match = re.search(r'PPI[:\s]+([0-9.]+)%?\s*.*?(\d{4}-\d{2}-\d{2})?', monthly_data, re.IGNORECASE)
        if ppi_match:
            ppi_val = ppi_match.group(1)
            ppi_date = ppi_match.group(2) if ppi_match.group(2) else "date unknown"
            context_parts.append(f"PPI: {ppi_val}% (as of {ppi_date})")
        
        if context_parts:
            return " | ".join(context_parts)
        else:
            return "Monthly data present but format unrecognized"
    
    def update_monthly_reference_if_new(self, date: str, monthly_data: str):
        """Update monthly reference file if new data detected"""
        try:
            monthly_file = MONTHLY_REF_DIR / MONTHLY_DATA_FILE
            
            # If file doesn't exist, create it
            if not monthly_file.exists():
                MONTHLY_REF_DIR.mkdir(parents=True, exist_ok=True)
                with open(monthly_file, 'w') as f:
                    f.write(monthly_data)
                print(f"✅ MACRO AGENT: Created monthly reference file")
                return
            
            # Read existing
            with open(monthly_file, 'r') as f:
                existing_data = f.read()
            
            # If different, update
            if monthly_data.strip() != existing_data.strip():
                with open(monthly_file, 'w') as f:
                    f.write(monthly_data)
                print(f"✅ MACRO AGENT: Updated monthly reference file on {date}")
        
        except Exception as e:
            print(f"⚠️  MACRO AGENT: Could not update monthly reference: {e}")
    
    def forward_fill_fundamentals(self, date: str, today_data: Dict) -> Dict:
        """Forward-fill missing fundamental metrics from most recent available data"""
        fundamentals = today_data.get('fundamentals.txt', '').strip()
        
        # If fundamentals exist and look complete, cache and return
        if fundamentals and 'T10Y' in fundamentals and len(fundamentals) > 50 and not fundamentals.startswith('[ERROR'):
            self.fundamentals_cache[date] = fundamentals
            return today_data
        
        # Missing or incomplete - try forward-fill
        print(f"⚠️  MACRO AGENT: {date} - fundamentals incomplete, attempting forward-fill...")
        
        # Look back up to 7 days
        current_date = datetime.strptime(date, "%Y-%m-%d")
        for days_back in range(1, 8):
            lookback_date = (current_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            # Check cache first
            if lookback_date in self.fundamentals_cache:
                filled_data = self.fundamentals_cache[lookback_date]
                today_data['fundamentals.txt'] = f"""=== FORWARD-FILLED from {lookback_date} ===
(Market holiday/weekend - using previous available data)

{filled_data}

=== END FORWARD-FILL ==="""
                print(f"✅ MACRO AGENT: Forward-filled from {lookback_date} ({days_back} days back)")
                return today_data
            
            # Try loading from file
            try:
                lookback_path = DATA_DIR / lookback_date / 'fundamentals.txt'
                if lookback_path.exists():
                    with open(lookback_path, 'r') as f:
                        filled_data = f.read().strip()
                    
                    if filled_data and 'T10Y' in filled_data and len(filled_data) > 50 and not filled_data.startswith('[ERROR'):
                        self.fundamentals_cache[lookback_date] = filled_data
                        today_data['fundamentals.txt'] = f"""=== FORWARD-FILLED from {lookback_date} ===
(Market holiday/weekend - using previous available data)

{filled_data}

=== END FORWARD-FILL ==="""
                        print(f"✅ MACRO AGENT: Forward-filled from {lookback_date} ({days_back} days back)")
                        return today_data
            
            except Exception:
                continue
        
        print(f"❌ MACRO AGENT: Could not forward-fill {date} - no valid data in last 7 days")
        return today_data
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict], monthly_context: str) -> str:
        memory_section = "First analysis - no historical context." if memory is None else f"MEMORY:\n{json.dumps(memory, indent=2)}"
        
        is_forward_filled = 'FORWARD-FILLED' in today_data.get('fundamentals.txt', '')
        forward_fill_note = ""
        if is_forward_filled:
            forward_fill_note = "\n⚠️ NOTE: Fundamentals data is FORWARD-FILLED from previous day (weekend/holiday).\n"
        
        return f"""MACRO analyst for gold intelligence system.

{memory_section}

🔔 MONTHLY CONTEXT (include in EVERY data_snapshot):
{monthly_context}

{forward_fill_note}TODAY'S DATA ({date}):
Calendar: {today_data.get('calendar.txt', 'N/A')}
Fundamentals: {today_data.get('fundamentals.txt', 'N/A')}
Monthly: {today_data.get('monthly_data.txt', 'N/A')}

CRITICAL INSTRUCTIONS:

1. MONTHLY CONTEXT: Include in data_snapshot EVERY day as "monthly_context": "{monthly_context}"
2. REAL RATE: T10Y - CPI_YoY (>1.5% bearish gold, <0% bullish gold)
3. FED POLICY: Analyze FEDFUNDS and calendar events

Return ONLY valid JSON (NO confidence score):
{{"metadata":{{"agent":"macro","date":"{date}","timestamp":"{datetime.now().isoformat()}","model":"Qwen-235B"}},"data_snapshot":{{"economic_events":"...","rates":"T10Y: X.XX%, FEDFUNDS: X.XX%","inflation":"CPI YoY: X.XX%","real_rate":"calculation shown","monthly_context":"{monthly_context}"}},"analysis":{{"regime":"RISK_ON/RISK_OFF/NEUTRAL","trend":"dovish/hawkish/neutral","key_drivers":["..."],"reasoning":"...","risk_factors":["..."]}},"memory_references":{{"compared_to":[],"corrections":[]}}}}"""
    
    def call_llm(self, prompt: str) -> str:
        if not self.api_key:
            raise Exception("Cerebras API key not configured")
        
        try:
            response = requests.post(
                self.api_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3.3-70b",
                    "messages": [
                        {"role": "system", "content": "Financial analyst. Respond ONLY with valid JSON. NO confidence scores."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.config['temperature'],
                    "max_tokens": self.config['max_tokens']
                },
                timeout=60
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            return content.replace('```json', '').replace('```', '').strip()
        
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise

if __name__ == "__main__":
    agent = MacroAgent()
    result = agent.analyze("2026-01-20")
    
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed")
    
    print("\ndone")