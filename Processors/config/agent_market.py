"""
MARKET AGENT - Technical Analysis & Volatility Regime Detection
Model: DeepSeek-R1-Distill-Llama-70B (Cerebras)
Files: technicals.txt, calculos.txt
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, Optional

from config import API_KEYS, AGENT_CONFIGS
from base_agent import BaseAgent


class MarketAgent(BaseAgent):
    """
    MARKET Agent: Analyzes price action, technical indicators, volatility
    
    Focus Areas:
    - Price action: OHLCV for Gold, SPX, VIX, DXY
    - Technical indicators: EMAs, RSI, MACD, Bollinger, Stoch, ADX
    - Volatility regime: Low vol vs high vol environment
    - Advanced analytics: Hurst exponent, volume profile
    - Cross-asset correlations: Gold vs DXY, Gold vs SPX
    """
    
    def __init__(self):
        super().__init__("market")
        self.api_key = API_KEYS.get("cerebras", "")
        self.api_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        
        if not self.api_key:
            print("⚠️  WARNING: Cerebras API key not found!")
    
    
    def build_prompt(self, date: str, today_data: Dict, memory: Optional[Dict]) -> str:
        """
        Build market-specific analysis prompt
        
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

TECHNICAL INDICATORS:
{today_data.get('technicals.txt', '[NO DATA]')}

ADVANCED CALCULATIONS:
{today_data.get('calculos.txt', '[NO DATA]')}
"""
        
        # Build the full prompt
        prompt = f"""You are the MARKET analyst in a gold macro intelligence system.

Your role: Analyze price action, technical indicators, and volatility regime to assess gold's market structure.

{memory_section}

{data_section}

=== YOUR TASK ===

**Focus on these key questions:**

1. **Price Action & Trend**
   - Is gold trending (strong directional move) or mean-reverting (range-bound)?
   - Are we at key support/resistance levels?
   - What's the current price relative to EMAs (20, 50, 200)?

2. **Momentum Analysis**
   - RSI: Oversold (<30), neutral, or overbought (>70)?
   - MACD: Bullish crossover, bearish crossover, or neutral?
   - ADX: Strong trend (>25) or weak trend (<20)?
   - Stochastic: Oversold, neutral, or overbought?

3. **Volatility Regime**
   - What's the current volatility state? (Low vol = complacency, high vol = fear)
   - Bollinger Band width: Expanding (volatility increasing) or contracting (squeeze)?
   - VIX: Low (<15), medium (15-25), or high (>25)?

4. **Market Structure**
   - Hurst exponent: Trending (>0.5) or mean-reverting (<0.5)?
   - Volume profile: Above or below average?
   - Support/resistance zones being tested?

5. **Cross-Asset Signals**
   - DXY (Dollar): Rising = gold headwind, falling = gold tailwind
   - SPX: Risk-on (equities up) or risk-off (equities down)?
   - Gold/DXY correlation: Normal inverse or decoupling?

**Compare to your past analysis:**
- Reference specific dates from your memory
- Identify regime shifts (e.g., trending → mean-reverting, low vol → high vol)
- Acknowledge if previous trend assessment was wrong

**Regime Assessment:**
- BREAKOUT: Strong momentum, trend confirmed, volatility expanding
- BREAKDOWN: Momentum failing, support broken, trend reversal
- CONSOLIDATION: Range-bound, low momentum, waiting for catalyst
- RISK_ON: Equities strong, VIX low, gold as alternative asset compressed
- RISK_OFF: Equities weak, VIX high, gold as safe haven bid

=== OUTPUT FORMAT (STRICT JSON) ===

Return ONLY valid JSON (no markdown fences, no explanation):

{{
  "metadata": {{
    "agent": "market",
    "date": "{date}",
    "timestamp": "{datetime.now().isoformat()}",
    "model": "deepseek-r1-distill-llama-70b"
  }},
  
  "data_snapshot": {{
    "price_action": "Gold $X,XXX, +/- X%, at EMA20/50/200",
    "momentum": "RSI XX, MACD bullish/bearish, ADX XX",
    "volatility": "VIX XX, Bollinger width expanding/contracting",
    "cross_assets": "DXY XXX (+/-X%), SPX XXX (+/-X%)"
  }},
  
  "analysis": {{
    "regime": "BREAKOUT or BREAKDOWN or CONSOLIDATION or RISK_ON or RISK_OFF",
    "trend": "Descriptive trend label (e.g., BULL_MOMENTUM, BEAR_REVERSAL, RANGE_BOUND)",
    "key_drivers": [
      "DRIVER_1",
      "DRIVER_2",
      "DRIVER_3"
    ],
    "reasoning": "2-3 sentence explanation focusing on price action, momentum, and volatility regime",
    "confidence": 0.85,
    "risk_factors": [
      "Key support/resistance levels to watch",
      "What could trigger regime shift"
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
- Regime must be one of: BREAKOUT, BREAKDOWN, CONSOLIDATION, RISK_ON, RISK_OFF
"""
        
        return prompt
    
    
    def call_llm(self, prompt: str) -> str:
        """
        Call Cerebras API with DeepSeek model
        
        Args:
            prompt: Complete prompt string
            
        Returns:
            LLM response text (should be JSON)
            
        Raises:
            Exception: If API call fails
        """
        
        if not self.api_key:
            raise Exception("Cerebras API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-r1-distill-llama-70b",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a technical market analyst. You respond ONLY with valid JSON, no markdown fences, no explanations."
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
            print(f"   🌐 Calling Cerebras API...")
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
    print("MARKET AGENT TEST")
    print("=" * 60)
    print()
    
    agent = MarketAgent()
    
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