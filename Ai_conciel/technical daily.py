#!/usr/bin/env python3
"""
Technical Snapshot Bot - XAU/USD Intraday Analysis
Generates optimized technical file for AI trading council
Timeframe: H1 (1-Hour) from trading day start to current moment
"""

import json
from datetime import datetime, timedelta, time
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
import ta
import MetaTrader5 as mt5
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
REPORTS_DIR = Path("Ai_conciel/reports")  # Edit this path as needed
# ============================================================================


def round_to_2_decimals(value) -> Optional[float]:
    """Round value to 2 decimals, handle None/NaN."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), 2)


def initialize_mt5() -> bool:
    """Initialize MT5 connection."""
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return False
    
    account_info = mt5.account_info()
    if account_info is None:
        print("❌ Terminal authorization failed. Ensure:")
        print("  1. MetaTrader 5 is running")
        print("  2. You are logged in")
        print("  3. AutoTrading is enabled")
        mt5.shutdown()
        return False
    
    print(f"✅ Connected to account: {account_info.login}")
    print(f"✅ Server: {account_info.server}")
    return True


def get_trading_day_start() -> datetime:
    """
    Get the start of today's trading session.
    XAU/USD trades 24h, but we consider day start as 00:00 UTC.
    """
    now = datetime.now()
    return datetime.combine(now.date(), time(0, 0))


def fetch_intraday_data(symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Fetch H1 data from today's trading start to now.
    Returns: (full_df with 200+ bars for indicators, today_df for analysis)
    """
    now = datetime.now()
    day_start = get_trading_day_start()
    
    # Fetch extended data for indicator calculation (200+ bars)
    extended_start = now - timedelta(days=15)  # ~300 H1 bars
    
    rates = mt5.copy_rates_range(
        symbol,
        TIMEFRAME,
        extended_start,
        now
    )
    
    if rates is None or len(rates) == 0:
        print(f"❌ Failed to fetch data for {symbol}")
        return None, None
    
    df_full = pd.DataFrame(rates)
    df_full['time'] = pd.to_datetime(df_full['time'], unit='s')
    df_full = df_full[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    
    # Filter today's data only for output
    df_today = df_full[df_full['time'] >= day_start].copy()
    
    print(f"✅ Fetched {len(df_full)} H1 bars total")
    print(f"✅ Today's data: {len(df_today)} bars (from {day_start.strftime('%H:%M')} to now)")
    
    return df_full, df_today


def calculate_technicals(df_full: pd.DataFrame) -> Dict:
    """Calculate technical indicators on full dataset."""
    close = df_full['close']
    high = df_full['high']
    low = df_full['low']
    volume = df_full['tick_volume']
    
    # RSI (14)
    rsi_indicator = ta.momentum.RSIIndicator(close, window=14)
    rsi = rsi_indicator.rsi()
    
    # EMA 50, 200
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()
    
    # MACD
    macd_indicator = ta.trend.MACD(close)
    macd_line = macd_indicator.macd()
    macd_signal = macd_indicator.macd_signal()
    
    # ATR (14)
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    
    return {
        'rsi': rsi,
        'ema50': ema50,
        'ema200': ema200,
        'macd': macd_line,
        'macd_signal': macd_signal,
        'atr': atr,
        'volume': volume
    }


def get_current_technicals(df_full: pd.DataFrame, indicators: Dict) -> Dict:
    """Get latest technical values."""
    current_idx = len(df_full) - 1
    current_price = df_full['close'].iloc[-1]
    
    rsi_val = indicators['rsi'].iloc[current_idx]
    ema50_val = indicators['ema50'].iloc[current_idx]
    ema200_val = indicators['ema200'].iloc[current_idx]
    macd_val = indicators['macd'].iloc[current_idx]
    signal_val = indicators['macd_signal'].iloc[current_idx]
    atr_val = indicators['atr'].iloc[current_idx]
    
    # RSI status
    if rsi_val >= 70:
        rsi_status = "Overbought"
    elif rsi_val <= 30:
        rsi_status = "Oversold"
    else:
        rsi_status = "Neutral"
    
    # EMA trend
    if not pd.isna(ema50_val) and not pd.isna(ema200_val):
        if current_price > ema50_val > ema200_val:
            ema_trend = "Strong Bullish"
        elif current_price > ema50_val:
            ema_trend = "Bullish"
        elif current_price < ema50_val < ema200_val:
            ema_trend = "Strong Bearish"
        else:
            ema_trend = "Bearish"
    else:
        ema_trend = "Insufficient data"
    
    # MACD status
    if not pd.isna(macd_val) and not pd.isna(signal_val):
        macd_status = "Bullish" if macd_val > signal_val else "Bearish"
    else:
        macd_status = "Unknown"
    
    return {
        'current_price': round_to_2_decimals(current_price),
        'rsi': round_to_2_decimals(rsi_val),
        'rsi_status': rsi_status,
        'ema50': round_to_2_decimals(ema50_val),
        'ema200': round_to_2_decimals(ema200_val),
        'ema_trend': ema_trend,
        'macd': round_to_2_decimals(macd_val),
        'macd_signal': round_to_2_decimals(signal_val),
        'macd_status': macd_status,
        'atr': round_to_2_decimals(atr_val)
    }


def calculate_fibonacci_levels(df_today: pd.DataFrame) -> Dict:
    """
    Calculate Fibonacci retracement from today's low to current high.
    """
    day_low = df_today['low'].min()
    day_high = df_today['high'].max()
    current_price = df_today['close'].iloc[-1]
    
    diff = day_high - day_low
    
    fib_levels = {
        '0.0% (Low)': round_to_2_decimals(day_low),
        '23.6%': round_to_2_decimals(day_low + diff * 0.236),
        '38.2%': round_to_2_decimals(day_low + diff * 0.382),
        '50.0%': round_to_2_decimals(day_low + diff * 0.500),
        '61.8%': round_to_2_decimals(day_low + diff * 0.618),
        '78.6%': round_to_2_decimals(day_low + diff * 0.786),
        '100% (High)': round_to_2_decimals(day_high)
    }
    
    return fib_levels


def detect_support_resistance(df_today: pd.DataFrame, num_levels: int = 3) -> Dict:
    """
    Detect key support and resistance levels from today's price action.
    Uses swing highs/lows.
    """
    highs = df_today['high'].values
    lows = df_today['low'].values
    
    # Simple method: find local maxima and minima
    resistance_levels = []
    support_levels = []
    
    for i in range(1, len(highs) - 1):
        # Resistance: local high
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            resistance_levels.append(highs[i])
        
        # Support: local low
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            support_levels.append(lows[i])
    
    # Sort and get top N
    resistance_levels = sorted(set(resistance_levels), reverse=True)[:num_levels]
    support_levels = sorted(set(support_levels))[:num_levels]
    
    return {
        'resistance': [round_to_2_decimals(r) for r in resistance_levels],
        'support': [round_to_2_decimals(s) for s in support_levels]
    }


def detect_order_blocks(df_today: pd.DataFrame) -> Dict:
    """
    Detect bullish and bearish order blocks (simplified).
    Order block = last opposite candle before strong move.
    """
    bullish_ob = []
    bearish_ob = []
    
    for i in range(1, len(df_today) - 1):
        current = df_today.iloc[i]
        next_candle = df_today.iloc[i + 1]
        
        # Bullish OB: bearish candle followed by strong bullish move
        if current['close'] < current['open']:  # Bearish candle
            if next_candle['close'] > next_candle['open']:  # Next is bullish
                move = next_candle['close'] - next_candle['open']
                if move > (current['open'] - current['close']) * 1.5:
                    bullish_ob.append({
                        'level': round_to_2_decimals(current['low']),
                        'time': str(current['time'])
                    })
        
        # Bearish OB: bullish candle followed by strong bearish move
        if current['close'] > current['open']:  # Bullish candle
            if next_candle['close'] < next_candle['open']:  # Next is bearish
                move = next_candle['open'] - next_candle['close']
                if move > (current['close'] - current['open']) * 1.5:
                    bearish_ob.append({
                        'level': round_to_2_decimals(current['high']),
                        'time': str(current['time'])
                    })
    
    # Get most recent
    bullish_ob = bullish_ob[-2:] if bullish_ob else []
    bearish_ob = bearish_ob[-2:] if bearish_ob else []
    
    return {
        'bullish': bullish_ob,
        'bearish': bearish_ob
    }


def detect_fair_value_gaps(df_today: pd.DataFrame) -> Dict:
    """
    Detect Fair Value Gaps (FVG/Imbalances).
    FVG = gap between candles where price moved too fast.
    """
    bullish_fvg = []
    bearish_fvg = []
    
    for i in range(2, len(df_today)):
        candle_1 = df_today.iloc[i - 2]
        candle_2 = df_today.iloc[i - 1]
        candle_3 = df_today.iloc[i]
        
        # Bullish FVG: gap between low of candle 3 and high of candle 1
        if candle_3['low'] > candle_1['high']:
            bullish_fvg.append({
                'top': round_to_2_decimals(candle_3['low']),
                'bottom': round_to_2_decimals(candle_1['high']),
                'time': str(candle_3['time'])
            })
        
        # Bearish FVG: gap between high of candle 3 and low of candle 1
        if candle_3['high'] < candle_1['low']:
            bearish_fvg.append({
                'top': round_to_2_decimals(candle_1['low']),
                'bottom': round_to_2_decimals(candle_3['high']),
                'time': str(candle_3['time'])
            })
    
    # Get most recent
    bullish_fvg = bullish_fvg[-2:] if bullish_fvg else []
    bearish_fvg = bearish_fvg[-2:] if bearish_fvg else []
    
    return {
        'bullish': bullish_fvg,
        'bearish': bearish_fvg
    }


def calculate_volume_profile(df_today: pd.DataFrame) -> Dict:
    """Calculate volume analysis for today."""
    total_volume = df_today['tick_volume'].sum()
    avg_volume = df_today['tick_volume'].mean()
    current_volume = df_today['tick_volume'].iloc[-1]
    
    volume_status = "High" if current_volume > avg_volume * 1.2 else "Normal" if current_volume > avg_volume * 0.8 else "Low"
    
    return {
        'total': int(total_volume),
        'average': int(avg_volume),
        'current': int(current_volume),
        'status': volume_status
    }


def generate_technical_snapshot(symbol: str = SYMBOL) -> Optional[Dict]:
    """Main function to generate complete technical snapshot."""
    
    # Fetch data
    df_full, df_today = fetch_intraday_data(symbol)
    
    if df_full is None or df_today is None or df_today.empty:
        return None
    
    # Calculate indicators
    print("📊 Calculating technical indicators...")
    indicators = calculate_technicals(df_full)
    current_tech = get_current_technicals(df_full, indicators)
    
    # Today's range
    day_open = df_today['open'].iloc[0]
    day_high = df_today['high'].max()
    day_low = df_today['low'].min()
    day_change = current_tech['current_price'] - day_open
    day_change_pct = (day_change / day_open) * 100
    
    # Fibonacci
    print("📐 Calculating Fibonacci levels...")
    fib_levels = calculate_fibonacci_levels(df_today)
    
    # Support/Resistance
    print("🎯 Detecting support/resistance...")
    sr_levels = detect_support_resistance(df_today)
    
    # Order Blocks
    print("📦 Detecting order blocks...")
    order_blocks = detect_order_blocks(df_today)
    
    # Fair Value Gaps
    print("⚡ Detecting fair value gaps...")
    fvg = detect_fair_value_gaps(df_today)
    
    # Volume
    print("📈 Analyzing volume...")
    volume_data = calculate_volume_profile(df_today)
    
    # Compile snapshot
    snapshot = {
        'symbol': symbol,
        'generated_at': datetime.now().isoformat(),
        'timeframe': 'H1',
        'trading_day_start': str(get_trading_day_start()),
        'bars_analyzed': len(df_today),
        
        'price_action': {
            'current': current_tech['current_price'],
            'day_open': round_to_2_decimals(day_open),
            'day_high': round_to_2_decimals(day_high),
            'day_low': round_to_2_decimals(day_low),
            'day_change': round_to_2_decimals(day_change),
            'day_change_pct': round_to_2_decimals(day_change_pct)
        },
        
        'moving_averages': {
            'ema50': current_tech['ema50'],
            'ema200': current_tech['ema200'],
            'trend': current_tech['ema_trend'],
            'price_vs_ema50': 'Above' if current_tech['current_price'] > current_tech['ema50'] else 'Below',
            'price_vs_ema200': 'Above' if current_tech['current_price'] > current_tech['ema200'] else 'Below'
        },
        
        'momentum': {
            'rsi': current_tech['rsi'],
            'rsi_status': current_tech['rsi_status'],
            'macd': current_tech['macd'],
            'macd_signal': current_tech['macd_signal'],
            'macd_status': current_tech['macd_status']
        },
        
        'volatility': {
            'atr': current_tech['atr'],
            'day_range': round_to_2_decimals(day_high - day_low)
        },
        
        'fibonacci': fib_levels,
        
        'key_levels': {
            'resistance': sr_levels['resistance'],
            'support': sr_levels['support']
        },
        
        'order_blocks': order_blocks,
        
        'fair_value_gaps': fvg,
        
        'volume': volume_data
    }
    
    return snapshot


def format_snapshot_for_ai(snapshot: Dict) -> str:
    """Format snapshot into AI-friendly text format."""
    
    s = snapshot
    pa = s['price_action']
    ma = s['moving_averages']
    mom = s['momentum']
    vol = s['volatility']
    fib = s['fibonacci']
    kl = s['key_levels']
    ob = s['order_blocks']
    fvg = s['fair_value_gaps']
    volume = s['volume']
    
    text = f"""=== XAU/USD TECHNICAL SNAPSHOT ===
Generated: {datetime.fromisoformat(s['generated_at']).strftime('%Y-%m-%d %H:%M UTC')}
Timeframe: {s['timeframe']} (Intraday - {s['bars_analyzed']} bars since {s['trading_day_start']})

PRICE ACTION:
Current: ${pa['current']}
Day Open: ${pa['day_open']}
Day High: ${pa['day_high']}
Day Low: ${pa['day_low']}
Day Change: ${pa['day_change']} ({pa['day_change_pct']}%)
Day Range: ${vol['day_range']}

MOVING AVERAGES (H1):
EMA50: ${ma['ema50']} -> Price {ma['price_vs_ema50']}
EMA200: ${ma['ema200']} -> Price {ma['price_vs_ema200']}
Trend: {ma['trend']}

MOMENTUM INDICATORS (H1):
RSI(14): {mom['rsi']} -> {mom['rsi_status']}
MACD: {mom['macd']} (Signal: {mom['macd_signal']})
MACD Status: {mom['macd_status']}

VOLATILITY:
ATR(14): ${vol['atr']}
Intraday Range: ${vol['day_range']}

KEY LEVELS:
Resistance: {', '.join([f'${r}' for r in kl['resistance']]) if kl['resistance'] else 'None detected'}
Support: {', '.join([f'${s}' for s in kl['support']]) if kl['support'] else 'None detected'}

FIBONACCI RETRACEMENT (Day Low to Current High):
100% (High): ${fib['100% (High)']}
78.6%: ${fib['78.6%']}
61.8%: ${fib['61.8%']}
50.0%: ${fib['50.0%']}
38.2%: ${fib['38.2%']}
23.6%: ${fib['23.6%']}
0.0% (Low): ${fib['0.0% (Low)']}

ORDER BLOCKS (H1):
Bullish: {len(ob['bullish'])} detected -> {', '.join([f"${b['level']}" for b in ob['bullish']]) if ob['bullish'] else 'None'}
Bearish: {len(ob['bearish'])} detected -> {', '.join([f"${b['level']}" for b in ob['bearish']]) if ob['bearish'] else 'None'}

FAIR VALUE GAPS (H1):
Bullish FVG: {len(fvg['bullish'])} detected -> {', '.join([f"${g['bottom']}-${g['top']}" for g in fvg['bullish']]) if fvg['bullish'] else 'None'}
Bearish FVG: {len(fvg['bearish'])} detected -> {', '.join([f"${g['bottom']}-${g['top']}" for g in fvg['bearish']]) if fvg['bearish'] else 'None'}

VOLUME ANALYSIS (H1):
Total (Today): {volume['total']:,}
Average: {volume['average']:,}
Current: {volume['current']:,}
Status: {volume['status']}

=== TRADE CONTEXT ===
Bias: {ma['trend'].split()[0].upper()} (EMA alignment)
Risk Area: Below ${min(kl['support']) if kl['support'] else pa['day_low']}
Opportunity: {'Pullback to Fib 38.2%-50%' if pa['day_change_pct'] > 0 else 'Break above resistance'}
Caution: {'RSI overbought - expect pullback' if mom['rsi'] > 70 else 'RSI oversold - bounce possible' if mom['rsi'] < 30 else 'Normal conditions'}

=== TRADING NOTES ===
- Trend: {ma['trend']}
- Structure: {'Higher highs/lows' if pa['day_change_pct'] > 0 else 'Lower highs/lows'}
- Entry zones: {', '.join([f'${r}' for r in kl['support'][:2]]) if kl['support'] else f"${pa['day_low']}"}
- SL zones: Below ${min(kl['support']) if kl['support'] else pa['day_low']}
- TP zones: {', '.join([f'${r}' for r in kl['resistance'][:2]]) if kl['resistance'] else f"${pa['day_high']}"}
"""
    
    return text


def save_snapshot(snapshot: Dict, text_format: str):
    """Save snapshot in both JSON and TXT formats with visible paths."""
    
    # Create reports directory
    REPORTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON (full data) with timestamp
    json_file = REPORTS_DIR / f"technical_snapshot_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, default=str)
    
    # Save TXT (AI-friendly) - always overwrites to keep latest
    txt_file = REPORTS_DIR / f"technical_snapshot.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text_format)
    
    # Get absolute paths
    json_path = json_file.absolute()
    txt_path = txt_file.absolute()
    
    print(f"\n{'='*60}")
    print("✅ SNAPSHOT SAVED SUCCESSFULLY")
    print(f"{'='*60}")
    print(f"\n[JSON - Full Data]")
    print(f"  {json_path}")
    print(f"\n[TXT - AI Trading Council]")
    print(f"  {txt_path}")
    print(f"\n{'='*60}")
    
    return str(txt_path)


def main():
    """Main execution."""
    print("=" * 60)
    print("XAU/USD TECHNICAL SNAPSHOT GENERATOR")
    print("Intraday H1 Analysis for AI Trading Council")
    print("=" * 60)
    print()
    
    if not initialize_mt5():
        return
    
    try:
        snapshot = generate_technical_snapshot()
        
        if snapshot:
            text_format = format_snapshot_for_ai(snapshot)
            saved_path = save_snapshot(snapshot, text_format)
            
            print("\n✅ READY FOR AI TRADING COUNCIL")
            print(f"\nUse this file in trading system:")
            print(f"  {saved_path}")
        else:
            print("❌ Failed to generate snapshot")
    
    finally:
        mt5.shutdown()
        print("\n✅ MT5 connection closed")


if __name__ == "__main__":
    main()