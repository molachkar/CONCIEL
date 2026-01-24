"""
NARRATIVE AGENT - News & Social Sentiment Analysis
Model: Meta-Llama-3.3-70B (SambaNova)
Files: news.txt, forums.txt
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, Optional

from config import API_KEYS, AGENT_CONFIGS
from base_agent import BaseAgent


class NarrativeAgent(BaseAgent):
    """
    NARRATIVE Agent: Analyzes news headlines and social sentiment
    
    Focus Areas:
    - News headlines: Political events, Fed drama, geopolitical risk
    - Reddit/forum sentiment: Retail positioning, fear/greed indicators
    - Catalyst identification: What could move gold in next 24-48 hours
    - Narrative shifts: Is the story building or fading?
    - Contrarian signals: Extreme sentiment = potential reversal
    """
    
    def __init__(self):
        super().__init__("narrative")
        self.api_key = API_KEYS.get("sambanova", "")
        self.api_endpoint = "https://api.sambanova.ai/v1/chat/completions"
        
        if not self.api_key:
            print("⚠️  WARNING: SambaNova API key not found!")
    
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        """
        Build narrative-specific analysis prompt
        
        Args:
            date: Target date (YYYY-MM-DD)
            today_data: Dictionary of file contents
            memory: Hierarchical memory (or None if first run)
            
        Returns:
            Complete prompt string
        """
        
        # Build memory section
        if memory is None:
            memory_section = """
=== HISTORICAL CONTEXT ===

🆕 This is your FIRST analysis. You have NO historical context yet.
Your output today will become the foundation for tomorrow's memory.
"""
        else:
            memory_section = f"""
=== HISTORICAL CONTEXT (CHRONOLOGICAL: OLD → NEW) ===

LONG-TERM MEMORY (3 weeks ago):
{json.dumps(memory['long_context'], indent=2)}

MEDIUM-TERM MEMORY (Last 2 weeks):
{json.dumps(memory['medium_context'], indent=2)}

RECENT MEMORY (Last 7 days):
{json.dumps(memory['recent_context'], indent=2)}
"""
        
        # Build today's data section
        data_section = f"""
=== TODAY'S NEW DATA ({date}) ===

NEWS HEADLINES:
{today_data.get('news.txt', '[NO DATA]')}

SOCIAL SENTIMENT (Reddit/Forums):
{today_data.get('forums.txt', '[NO DATA]')}
"""
        
        # Build the full prompt
        prompt = f"""You are the NARRATIVE analyst in a gold macro intelligence system.

Your role: Analyze news and social sentiment to identify catalysts, sentiment extremes, and narrative shifts.

{memory_section}

{data_section}

=== YOUR TASK ===

**Focus on these key questions:**

1. **Dominant Narrative**
   - What's the main story driving gold today?
   - Is it Fed policy concerns? Geopolitical risk? Inflation fears? Dollar strength?
   - Is this narrative building momentum or fading?

2. **Retail Sentiment Analysis**
   - Are retail traders (Reddit/forums) bullish or bearish on gold?
   - What's the fear/greed level?
   - Are there signs of extreme positioning (contrarian indicator)?

3. **Catalyst Identification**
   - What specific events could move gold in next 24-48 hours?
   - Are there upcoming Fed speeches, data releases, or geopolitical developments?
   - Which headlines have the most potential market impact?

4. **Geopolitical Risk Assessment**
   - Any war risks, political instability, or crisis developments?
   - Is safe-haven demand elevated or subdued?
   - Are there systemic risks (banking crisis, debt ceiling, etc.)?

5. **Sentiment Shift Detection**
   - Has sentiment changed significantly from yesterday?
   - Is there a narrative reversal in progress?
   - Are contrarian signals appearing? (e.g., extreme bearishness = buy signal)

**Compare to your past analysis:**
- Reference specific dates from your memory
- Identify narrative shifts (e.g., "inflation scare" → "deflation worry")
- Acknowledge if previous catalyst assessment was wrong

**Regime Assessment:**
- RISK_ON_NARRATIVE: Optimism, complacency, "Goldilocks economy" story
- RISK_OFF_NARRATIVE: Fear, crisis mode, safe-haven demand elevated
- NEUTRAL_NARRATIVE: Mixed signals, no clear dominant story
- BULLISH_SENTIMENT: Retail very bullish (possible contrarian sell signal)
- BEARISH_SENTIMENT: Retail very bearish (possible contrarian buy signal)

=== OUTPUT FORMAT (STRICT JSON) ===

Return ONLY valid JSON (no markdown fences, no explanation):

{{
  "metadata": {{
    "agent": "narrative",
    "date": "{date}",
    "timestamp": "{datetime.now().isoformat()}",
    "model": "Meta-Llama-3.3-70B"
  }},
  
  "data_snapshot": {{
    "dominant_story": "1 sentence summary of main narrative",
    "sentiment": "Retail bullish/bearish/neutral, fear/greed level",
    "catalysts": "Key upcoming events or risks",
    "geopolitical": "Any major geopolitical developments"
  }},
  
  "analysis": {{
    "regime": "RISK_ON_NARRATIVE or RISK_OFF_NARRATIVE or NEUTRAL_NARRATIVE or BULLISH_SENTIMENT or BEARISH_SENTIMENT",
    "trend": "Descriptive trend label (e.g., FED_INDEPENDENCE_CRISIS, INFLATION_SCARE_FADING, SAFE_HAVEN_BID)",
    "key_drivers": [
      "DRIVER_1",
      "DRIVER_2",
      "DRIVER_3"
    ],
    "reasoning": "2-3 sentence explanation focusing on narrative momentum and sentiment positioning",
    "confidence": 0.85,
    "risk_factors": [
      "What could shift the narrative",
      "Contrarian signals to watch"
    ]
  }},
  
  "memory_references": {{
    "compared_to": [
      "YYYY-MM-DD: Brief summary of what you assessed then",
      "YYYY-MM-DD: Another key reference point"
    ],
    "corrections": [
      "If you were wrong before, acknowledge it and explain why"
    ]
  }}
}}

**CRITICAL RULES:**
- Return ONLY the JSON object, nothing else
- No markdown code fences (```json)
- No explanatory text before or after
- All strings must use double quotes
- Confidence must be a number between 0.0 and 1.0
- Regime must be one of: RISK_ON_NARRATIVE, RISK_OFF_NARRATIVE, NEUTRAL_NARRATIVE, BULLISH_SENTIMENT, BEARISH_SENTIMENT
"""
        
        return prompt
    
    
    def call_llm(self, prompt: str) -> str:
        """
        Call SambaNova API with Meta-Llama-3.3-70B
        
        Args:
            prompt: Complete prompt string
            
        Returns:
            LLM response text (should be JSON)
            
        Raises:
            Exception: If API call fails
        """
        
        if not self.api_key:
            raise Exception("SambaNova API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "Meta-Llama-3.3-70B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a narrative and sentiment analyst. You respond ONLY with valid JSON, no markdown fences, no explanations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.config['temperature'],
            "max_tokens": self.config['max_tokens']
        }
        
        try:
            print(f"   🌐 Calling SambaNova API...")
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            # Extract message content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # Clean up any markdown fences if present
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                return content
            else:
                raise Exception("Unexpected API response format")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("NARRATIVE AGENT TEST")
    print("=" * 60)
    print()
    
    agent = NarrativeAgent()
    
    # Test with a real date
    test_date = "2026-01-20"
    
    print(f"\n🧪 Testing full analysis pipeline for {test_date}...")
    print()
    
    result = agent.analyze(test_date)
    
    if result:
        print("\n" + "=" * 60)
        print("📊 ANALYSIS RESULT")
        print("=" * 60)
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ Analysis failed")
    
    print("\n" + "=" * 60)