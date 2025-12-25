#!/usr/bin/env python3
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np
import ta
import MetaTrader5 as mt5
from pathlib import Path

# ============================================================================
# CONFIGURATION - EDIT THESE PATHS
# ============================================================================
OUTPUT_PATH = r"C:\\Users\\PC\\Desktop\\all in\\Ai_conciel\\reports"
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
# ============================================================================

def round_2(value):
    if value is None or pd.isna(value):
        return None
    return round(float(value), 2)

def init_mt5():
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        return False
    account = mt5.account_info()
    if not account:
        print("Login failed")
        mt5.shutdown()
        return False
    print(f"Connected: {account.login} | {account.server}")
    return True

def fetch_data(symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    now_utc = datetime.now(timezone.utc)
    extended_start = now_utc - timedelta(days=15)
    
    rates = mt5.copy_rates_range(symbol, TIMEFRAME, extended_start, now_utc)
    if rates is None or len(rates) == 0:
        print(f"Failed to fetch data: {mt5.last_error()}")
        return None, None
    
    df_full = pd.DataFrame(rates)
    df_full['time'] = pd.to_datetime(df_full['time'], unit='s', utc=True)
    df_full = df_full[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    
    last_bar = df_full['time'].max()
    hours_ago = (now_utc - last_bar).total_seconds() / 3600
    
    if hours_ago > 2:
        print(f"Market closed (last bar {hours_ago:.1f}h ago)")
        df_today = df_full.tail(24).copy()
    else:
        intraday_start = now_utc - timedelta(hours=24)
        df_today = df_full[df_full['time'] >= intraday_start].copy()
    
    if df_today.empty:
        return None, None
    
    print(f"Fetched {len(df_full)} bars | Analysis: {len(df_today)} bars")
    return df_full, df_today

def calc_indicators(df):
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    
    # Trend
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    ema9 = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    ema21 = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()
    
    # MACD
    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd = macd_ind.macd()
    signal = macd_ind.macd_signal()
    histogram = macd_ind.macd_diff()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_middle = bb.bollinger_mavg()
    bb_lower = bb.bollinger_lband()
    bb_width = bb.bollinger_wband()
    
    # ATR & Volatility
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    
    # Stochastic
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()
    
    # ADX (Trend Strength)
    adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
    adx = adx_ind.adx()
    plus_di = adx_ind.adx_pos()
    minus_di = adx_ind.adx_neg()
    
    # CCI (Commodity Channel Index)
    cci = ta.trend.CCIIndicator(high, low, close, window=20).cci()
    
    # Williams %R
    williams = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r()
    
    # OBV (On Balance Volume)
    obv = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    
    # Rate of Change
    roc = ta.momentum.ROCIndicator(close, window=12).roc()
    
    return {
        'rsi': rsi, 'ema9': ema9, 'ema21': ema21, 'ema50': ema50, 'ema200': ema200,
        'macd': macd, 'signal': signal, 'histogram': histogram,
        'bb_upper': bb_upper, 'bb_middle': bb_middle, 'bb_lower': bb_lower, 'bb_width': bb_width,
        'atr': atr, 'stoch_k': stoch_k, 'stoch_d': stoch_d,
        'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
        'cci': cci, 'williams': williams, 'obv': obv, 'roc': roc
    }

def get_current_tech(df_full, indicators):
    idx = -1
    price = df_full['close'].iloc[idx]
    
    rsi = indicators['rsi'].iloc[idx]
    ema9 = indicators['ema9'].iloc[idx]
    ema21 = indicators['ema21'].iloc[idx]
    ema50 = indicators['ema50'].iloc[idx]
    ema200 = indicators['ema200'].iloc[idx]
    
    macd = indicators['macd'].iloc[idx]
    signal = indicators['signal'].iloc[idx]
    histogram = indicators['histogram'].iloc[idx]
    
    bb_upper = indicators['bb_upper'].iloc[idx]
    bb_middle = indicators['bb_middle'].iloc[idx]
    bb_lower = indicators['bb_lower'].iloc[idx]
    bb_width = indicators['bb_width'].iloc[idx]
    
    atr = indicators['atr'].iloc[idx]
    
    stoch_k = indicators['stoch_k'].iloc[idx]
    stoch_d = indicators['stoch_d'].iloc[idx]
    
    adx = indicators['adx'].iloc[idx]
    plus_di = indicators['plus_di'].iloc[idx]
    minus_di = indicators['minus_di'].iloc[idx]
    
    cci = indicators['cci'].iloc[idx]
    williams = indicators['williams'].iloc[idx]
    obv = indicators['obv'].iloc[idx]
    roc = indicators['roc'].iloc[idx]
    
    # RSI Status
    rsi_status = "Overbought" if rsi >= 70 else "Oversold" if rsi <= 30 else "Neutral"
    
    # EMA Trend
    if pd.notna(ema9) and pd.notna(ema21) and pd.notna(ema50) and pd.notna(ema200):
        if price > ema9 > ema21 > ema50 > ema200:
            trend = "Strong Bullish"
        elif price > ema50 > ema200:
            trend = "Bullish"
        elif price < ema9 < ema21 < ema50 < ema200:
            trend = "Strong Bearish"
        elif price < ema50 < ema200:
            trend = "Bearish"
        else:
            trend = "Mixed"
    else:
        trend = "Insufficient data"
    
    # MACD Status
    macd_status = "Bullish" if pd.notna(macd) and pd.notna(signal) and macd > signal else "Bearish"
    
    # Stochastic Status
    stoch_status = "Overbought" if stoch_k >= 80 else "Oversold" if stoch_k <= 20 else "Neutral"
    
    # ADX Trend Strength
    if pd.notna(adx):
        if adx > 25:
            trend_strength = "Strong"
        elif adx > 20:
            trend_strength = "Moderate"
        else:
            trend_strength = "Weak"
    else:
        trend_strength = "Unknown"
    
    # BB Position
    if pd.notna(bb_upper) and pd.notna(bb_lower):
        if price > bb_upper:
            bb_position = "Above Upper Band"
        elif price < bb_lower:
            bb_position = "Below Lower Band"
        else:
            bb_position = "Inside Bands"
    else:
        bb_position = "Unknown"
    
    return {
        'price': round_2(price),
        'rsi': round_2(rsi), 'rsi_status': rsi_status,
        'ema9': round_2(ema9), 'ema21': round_2(ema21), 'ema50': round_2(ema50), 'ema200': round_2(ema200),
        'trend': trend,
        'macd': round_2(macd), 'signal': round_2(signal), 'histogram': round_2(histogram),
        'macd_status': macd_status,
        'bb_upper': round_2(bb_upper), 'bb_middle': round_2(bb_middle), 'bb_lower': round_2(bb_lower),
        'bb_width': round_2(bb_width), 'bb_position': bb_position,
        'atr': round_2(atr),
        'stoch_k': round_2(stoch_k), 'stoch_d': round_2(stoch_d), 'stoch_status': stoch_status,
        'adx': round_2(adx), 'plus_di': round_2(plus_di), 'minus_di': round_2(minus_di),
        'trend_strength': trend_strength,
        'cci': round_2(cci), 'williams': round_2(williams), 'obv': round_2(obv), 'roc': round_2(roc)
    }

def calc_fib(df):
    low = df['low'].min()
    high = df['high'].max()
    diff = high - low
    return {
        '0.0': round_2(low),
        '23.6': round_2(low + diff * 0.236),
        '38.2': round_2(low + diff * 0.382),
        '50.0': round_2(low + diff * 0.500),
        '61.8': round_2(low + diff * 0.618),
        '78.6': round_2(low + diff * 0.786),
        '100': round_2(high)
    }

def detect_sr(df):
    if len(df) < 3:
        return {'resistance': [], 'support': []}
    
    highs = df['high'].values
    lows = df['low'].values
    res = []
    sup = []
    
    for i in range(1, len(highs) - 1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            res.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            sup.append(lows[i])
    
    return {
        'resistance': [round_2(r) for r in sorted(set(res), reverse=True)[:3]],
        'support': [round_2(s) for s in sorted(set(sup))[:3]]
    }

def calc_pivot_points(df):
    """Calculate standard pivot points"""
    high = df['high'].max()
    low = df['low'].min()
    close = df['close'].iloc[-1]
    
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    
    return {
        'pivot': round_2(pivot),
        'r1': round_2(r1), 'r2': round_2(r2), 'r3': round_2(r3),
        's1': round_2(s1), 's2': round_2(s2), 's3': round_2(s3)
    }

def generate_snapshot(symbol=SYMBOL):
    df_full, df_today = fetch_data(symbol)
    if df_full is None or df_today.empty:
        return None
    
    print("Calculating indicators...")
    indicators = calc_indicators(df_full)
    tech = get_current_tech(df_full, indicators)
    
    open_price = df_today['open'].iloc[0]
    high = df_today['high'].max()
    low = df_today['low'].min()
    change = tech['price'] - open_price
    change_pct = (change / open_price) * 100
    
    fib = calc_fib(df_today)
    sr = detect_sr(df_today)
    pivots = calc_pivot_points(df_today)
    
    vol_total = int(df_today['tick_volume'].sum())
    vol_avg = int(df_today['tick_volume'].mean())
    vol_current = int(df_today['tick_volume'].iloc[-1])
    vol_status = "High" if vol_current > vol_avg * 1.2 else "Normal" if vol_current > vol_avg * 0.8 else "Low"
    
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'price': tech['price'],
        'open': round_2(open_price),
        'high': round_2(high),
        'low': round_2(low),
        'change': round_2(change),
        'change_pct': round_2(change_pct),
        'range': round_2(high - low),
        'ema9': tech['ema9'],
        'ema21': tech['ema21'],
        'ema50': tech['ema50'],
        'ema200': tech['ema200'],
        'trend': tech['trend'],
        'rsi': tech['rsi'],
        'rsi_status': tech['rsi_status'],
        'macd': tech['macd'],
        'macd_signal': tech['signal'],
        'macd_histogram': tech['histogram'],
        'macd_status': tech['macd_status'],
        'bb_upper': tech['bb_upper'],
        'bb_middle': tech['bb_middle'],
        'bb_lower': tech['bb_lower'],
        'bb_width': tech['bb_width'],
        'bb_position': tech['bb_position'],
        'atr': tech['atr'],
        'stoch_k': tech['stoch_k'],
        'stoch_d': tech['stoch_d'],
        'stoch_status': tech['stoch_status'],
        'adx': tech['adx'],
        'plus_di': tech['plus_di'],
        'minus_di': tech['minus_di'],
        'trend_strength': tech['trend_strength'],
        'cci': tech['cci'],
        'williams_r': tech['williams'],
        'obv': tech['obv'],
        'roc': tech['roc'],
        'fib_0': fib['0.0'],
        'fib_236': fib['23.6'],
        'fib_382': fib['38.2'],
        'fib_50': fib['50.0'],
        'fib_618': fib['61.8'],
        'fib_786': fib['78.6'],
        'fib_100': fib['100'],
        'resistance': sr['resistance'],
        'support': sr['support'],
        'pivot': pivots['pivot'],
        'r1': pivots['r1'], 'r2': pivots['r2'], 'r3': pivots['r3'],
        's1': pivots['s1'], 's2': pivots['s2'], 's3': pivots['s3'],
        'volume_total': vol_total,
        'volume_avg': vol_avg,
        'volume_current': vol_current,
        'volume_status': vol_status
    }

def format_snapshot(s):
    return f"""=== XAU/USD TECHNICAL SNAPSHOT ===
Generated: {datetime.fromisoformat(s['generated_at']):%Y-%m-%d %H:%M UTC}

PRICE ACTION:
Current: ${s['price']}
Open: ${s['open']}
High: ${s['high']}
Low: ${s['low']}
Change: ${s['change']} ({s['change_pct']}%)
Range: ${s['range']}

MOVING AVERAGES:
EMA9: ${s['ema9']}
EMA21: ${s['ema21']}
EMA50: ${s['ema50']}
EMA200: ${s['ema200']}
Trend: {s['trend']}

MOMENTUM:
RSI(14): {s['rsi']} - {s['rsi_status']}
Stochastic K: {s['stoch_k']} D: {s['stoch_d']} - {s['stoch_status']}
CCI(20): {s['cci']}
Williams %R: {s['williams_r']}
ROC(12): {s['roc']}

TREND INDICATORS:
MACD: {s['macd']} Signal: {s['macd_signal']} Histogram: {s['macd_histogram']} - {s['macd_status']}
ADX(14): {s['adx']} - Trend Strength: {s['trend_strength']}
+DI: {s['plus_di']} -DI: {s['minus_di']}

VOLATILITY & BANDS:
ATR(14): ${s['atr']}
BB Upper: ${s['bb_upper']}
BB Middle: ${s['bb_middle']}
BB Lower: ${s['bb_lower']}
BB Width: {s['bb_width']}
Price Position: {s['bb_position']}

VOLUME:
Total: {s['volume_total']:,}
Average: {s['volume_avg']:,}
Current: {s['volume_current']:,}
Status: {s['volume_status']}
OBV: {s['obv']}

FIBONACCI LEVELS:
100%: ${s['fib_100']}
78.6%: ${s['fib_786']}
61.8%: ${s['fib_618']}
50.0%: ${s['fib_50']}
38.2%: ${s['fib_382']}
23.6%: ${s['fib_236']}
0%: ${s['fib_0']}

KEY LEVELS:
Resistance: {', '.join([f'${r}' for r in s['resistance']]) if s['resistance'] else 'None'}
Support: {', '.join([f'${sup}' for sup in s['support']]) if s['support'] else 'None'}

PIVOT POINTS:
R3: ${s['r3']}
R2: ${s['r2']}
R1: ${s['r1']}
Pivot: ${s['pivot']}
S1: ${s['s1']}
S2: ${s['s2']}
S3: ${s['s3']}
"""

def save_snapshot(text):
    output_dir = Path(OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    txt_file = output_dir / "tech.txt"
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"\nSaved: {txt_file.absolute()}")
    return str(txt_file)

def main():
    print("=" * 60)
    print("XAU/USD Technical Snapshot Generator")
    print("=" * 60)
    
    if not init_mt5():
        return
    
    try:
        snapshot = generate_snapshot()
        if snapshot:
            text = format_snapshot(snapshot)
            save_snapshot(text)
            print("Ready for AI Trading Council")
        else:
            print("Failed to generate snapshot")
    finally:
        mt5.shutdown()
        print("MT5 closed")

if __name__ == "__main__":
    main()