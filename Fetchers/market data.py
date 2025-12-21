#!/usr/bin/env python3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
import pandas as pd
import numpy as np
import ta
import MetaTrader5 as mt5
import os

INSTRUMENTS = {
    "XAUUSD": "Gold spot",
    "USA500.IDX": "S&P500 index CFD",
    "VOL.IDX": "Volatility Index (VIX CFD)",
    "DOLLAR.IDX": "Dollar Index (DXY CFD)"
}

def round_to_2_decimals(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float, np.number)):
        return round(float(value), 2)
    return value

def initialize_mt5() -> bool:
    # Try to initialize MT5 with specific parameters
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return False
    
    # Check if terminal is authorized
    account_info = mt5.account_info()
    if account_info is None:
        print("Terminal authorization failed. Please ensure:")
        print("1. MetaTrader 5 terminal is running")
        print("2. You are logged into your account")
        print("3. AutoTrading is enabled (Tools -> Options -> Expert Advisors)")
        print("4. 'Allow automated trading' is checked")
        mt5.shutdown()
        return False
    
    print(f"✓ Connected to account: {account_info.login}")
    print(f"✓ Server: {account_info.server}")
    return True

def fetch_extended_daily_ohlc(symbol: str, output_days: int = 30, total_days: int = 300) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Fetch extended data for indicator calculations, return full dataset and last N days"""
    now = datetime.now()
    extended_days_ago = now - timedelta(days=total_days + 100)  # Extra buffer for trading days
    
    rates = mt5.copy_rates_range(
        symbol, 
        mt5.TIMEFRAME_D1, 
        extended_days_ago,
        now
    )
    
    if rates is None or len(rates) == 0:
        return None, None
    
    df_full = pd.DataFrame(rates)
    df_full['time'] = pd.to_datetime(df_full['time'], unit='s')
    
    # Select only OHLC columns
    df_full = df_full[['time', 'open', 'high', 'low', 'close']]
    
    # Return full data for calculations and last 30 days for output
    df_output = df_full.tail(output_days).copy()
    
    return df_full, df_output

def compute_daily_technicals(df_full: pd.DataFrame, df_output: pd.DataFrame) -> Optional[List[Dict[str, Any]]]:
    """Compute technical indicators using full dataset, return values for output period only"""
    if df_full is None or len(df_full) < 200:
        return None
    
    technicals_list = []
    
    close = df_full['close']
    high = df_full['high']
    low = df_full['low']
    
    # Calculate indicators on full dataset
    rsi_indicator = ta.momentum.RSIIndicator(close, window=14)
    rsi_series = rsi_indicator.rsi()
    
    ema50_indicator = ta.trend.EMAIndicator(close, window=50)
    ema200_indicator = ta.trend.EMAIndicator(close, window=200)
    
    ema50_series = ema50_indicator.ema_indicator()
    ema200_series = ema200_indicator.ema_indicator()
    
    macd_indicator = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    histogram = macd_indicator.macd_diff()
    
    stoch_indicator = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch_indicator.stoch()
    stoch_d = stoch_indicator.stoch_signal()
    
    # Get the indices that correspond to df_output in df_full
    output_start_idx = len(df_full) - len(df_output)
    
    # Build technicals for each day in the output period
    for i in range(len(df_output)):
        full_idx = output_start_idx + i
        
        rsi_val = rsi_series.iloc[full_idx] if full_idx < len(rsi_series) and not pd.isna(rsi_series.iloc[full_idx]) else None
        
        if rsi_val is not None:
            if rsi_val >= 70:
                rsi_status = "Overbought"
            elif rsi_val <= 30:
                rsi_status = "Oversold"
            else:
                rsi_status = "Neutral"
        else:
            rsi_status = None
        
        ema50_val = ema50_series.iloc[full_idx] if full_idx < len(ema50_series) and not pd.isna(ema50_series.iloc[full_idx]) else None
        ema200_val = ema200_series.iloc[full_idx] if full_idx < len(ema200_series) and not pd.isna(ema200_series.iloc[full_idx]) else None
        
        if ema50_val is not None and ema200_val is not None:
            ema_trend = "Bullish" if ema50_val > ema200_val else "Bearish"
        else:
            ema_trend = None
        
        macd_val = macd_line.iloc[full_idx] if full_idx < len(macd_line) and not pd.isna(macd_line.iloc[full_idx]) else None
        signal_val = signal_line.iloc[full_idx] if full_idx < len(signal_line) and not pd.isna(signal_line.iloc[full_idx]) else None
        hist_val = histogram.iloc[full_idx] if full_idx < len(histogram) and not pd.isna(histogram.iloc[full_idx]) else None
        
        stoch_k_val = stoch_k.iloc[full_idx] if full_idx < len(stoch_k) and not pd.isna(stoch_k.iloc[full_idx]) else None
        stoch_d_val = stoch_d.iloc[full_idx] if full_idx < len(stoch_d) and not pd.isna(stoch_d.iloc[full_idx]) else None
        
        if stoch_d_val is not None:
            if stoch_d_val >= 80:
                stoch_status = "Exhaustion Near Highs"
            elif stoch_d_val <= 20:
                stoch_status = "Exhaustion Near Lows"
            else:
                stoch_status = "Neutral"
        else:
            stoch_status = None
        
        technicals_list.append({
            "date": str(df_output['time'].iloc[i]),
            "rsi_value": round_to_2_decimals(rsi_val),
            "rsi_status": rsi_status,
            "ema50_value": round_to_2_decimals(ema50_val),
            "ema200_value": round_to_2_decimals(ema200_val),
            "ema_trend": ema_trend,
            "macd_value": round_to_2_decimals(macd_val),
            "macd_signal": round_to_2_decimals(signal_val),
            "macd_histogram": round_to_2_decimals(hist_val),
            "stoch_k_value": round_to_2_decimals(stoch_k_val),
            "stoch_d_value": round_to_2_decimals(stoch_d_val),
            "stoch_status": stoch_status
        })
    
    return technicals_list

def detect_30d_high_low(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect the highest high and lowest low in 30-day period"""
    if df is None or df.empty:
        return {"high": None, "low": None, "high_date": None, "low_date": None}
    
    high_idx = df['high'].idxmax()
    low_idx = df['low'].idxmin()
    
    return {
        "thirty_day_high": round_to_2_decimals(df.loc[high_idx, 'high']),
        "thirty_day_high_date": str(df.loc[high_idx, 'time']),
        "thirty_day_low": round_to_2_decimals(df.loc[low_idx, 'low']),
        "thirty_day_low_date": str(df.loc[low_idx, 'time'])
    }

def analyze_instrument_30d(symbol: str) -> Optional[Dict[str, Any]]:
    """Analyze instrument with 30-day market data and technicals"""
    
    # Fetch extended data for calculations, get last 30 days for output
    df_full, df_output = fetch_extended_daily_ohlc(symbol, output_days=30, total_days=300)
    
    if df_full is None or df_output is None or df_output.empty:
        print(f"Failed to fetch data for {symbol}")
        return None
    
    if len(df_full) < 200:
        print(f"Warning: {symbol} only has {len(df_full)} days of data, need 200+ for accurate indicators")
    
    print(f"  Fetched {len(df_full)} days total, using last {len(df_output)} days for output")
    
    # Convert OHLC to JSON-serializable format
    market_data = []
    for _, row in df_output.iterrows():
        market_data.append({
            "date": str(row['time']),
            "open": round_to_2_decimals(row['open']),
            "high": round_to_2_decimals(row['high']),
            "low": round_to_2_decimals(row['low']),
            "close": round_to_2_decimals(row['close'])
        })
    
    # Detect 30-day high/low
    high_low_info = detect_30d_high_low(df_output)
    
    # Compute daily technicals using full dataset
    technicals = compute_daily_technicals(df_full, df_output)
    
    result = {
        "instrument": symbol,
        "description": INSTRUMENTS.get(symbol, "Unknown"),
        "analysis_timestamp": datetime.now().isoformat(),
        "period": "30_days",
        "thirty_day_range": high_low_info,
        "market_data": market_data,
        "technicals": technicals if technicals else []
    }
    
    return result

def save_to_json(results: List[Dict[str, Any]], filename: str = "Fetchers/jsons/market_analysis_30d.json"):
    """Save all results to a single JSON file"""
    if not results:
        return
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "period_days": 30,
        "instruments": results
    }
    
    with open(filename, 'w') as jsonfile:
        json.dump(output, jsonfile, indent=2, default=str)

def main():
    if not initialize_mt5():
        return
    
    results = []
    
    for symbol in INSTRUMENTS.keys():
        print(f"Analyzing {symbol}...")
        result = analyze_instrument_30d(symbol)
        if result:
            results.append(result)
            print(f"✓ {symbol} analysis complete ({len(result['market_data'])} days)")
    
    mt5.shutdown()
    
    if results:
        save_to_json(results)
        print(f"\n✓ Complete analysis saved to market_analysis_30d.json")
        print(f"✓ Total instruments analyzed: {len(results)}")
    else:
        print("No results to save")

if __name__ == "__main__":
    main()