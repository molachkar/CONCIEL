import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import pandas as pd
import numpy as np
import ta
import MetaTrader5 as mt5
from pathlib import Path

OUTPUT_PATH = "reports"
INSTRUMENTS = {
    "XAUUSD": "Gold",
    "USA500.IDX": "S&P500",
    "VOL.IDX": "VIX",
    "DOLLAR.IDX": "DXY"
}
TIMEFRAME = mt5.TIMEFRAME_D1

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

def fetch_data(symbol: str) -> Optional[pd.DataFrame]:
    now_utc = datetime.now(timezone.utc)
    start = now_utc - timedelta(days=450)
    
    rates = mt5.copy_rates_range(symbol, TIMEFRAME, start, now_utc)
    if rates is None or len(rates) == 0:
        print(f"{symbol}: Failed to fetch data")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    
    print(f"{symbol}: Fetched {len(df)} daily bars")
    return df

def calc_indicators(df):
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    ema9 = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    ema21 = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()
    
    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd = macd_ind.macd()
    signal = macd_ind.macd_signal()
    
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()
    
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()
    
    adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
    adx = adx_ind.adx()
    
    return {
        'rsi': rsi, 'ema9': ema9, 'ema21': ema21, 'ema50': ema50, 'ema200': ema200,
        'macd': macd, 'signal': signal, 'bb_upper': bb_upper, 'bb_lower': bb_lower,
        'atr': atr, 'stoch_k': stoch_k, 'stoch_d': stoch_d, 'adx': adx
    }

def format_instrument_data(symbol: str, name: str, df, indicators, last_n=35):
    df_slice = df.tail(last_n).copy()
    output = []
    
    output.append(f"\n{'='*80}")
    output.append(f"{name} ({symbol}) - 35 Day History")
    output.append(f"{'='*80}\n")
    
    for idx in range(len(df_slice)):
        i = df_slice.index[idx]
        date = df_slice.loc[i, 'time'].strftime('%m-%d-%y')
        o = round_2(df_slice.loc[i, 'open'])
        h = round_2(df_slice.loc[i, 'high'])
        l = round_2(df_slice.loc[i, 'low'])
        c = round_2(df_slice.loc[i, 'close'])
        v = int(df_slice.loc[i, 'tick_volume'])
        
        rsi = round_2(indicators['rsi'].loc[i])
        ema9 = round_2(indicators['ema9'].loc[i])
        ema21 = round_2(indicators['ema21'].loc[i])
        ema50 = round_2(indicators['ema50'].loc[i])
        ema200 = round_2(indicators['ema200'].loc[i])
        macd = round_2(indicators['macd'].loc[i])
        sig = round_2(indicators['signal'].loc[i])
        bbu = round_2(indicators['bb_upper'].loc[i])
        bbl = round_2(indicators['bb_lower'].loc[i])
        atr = round_2(indicators['atr'].loc[i])
        stk = round_2(indicators['stoch_k'].loc[i])
        std = round_2(indicators['stoch_d'].loc[i])
        adx = round_2(indicators['adx'].loc[i])
        
        trend = "B" if c and ema50 and c > ema50 else "S" if c and ema50 and c < ema50 else "N"
        rsi_s = "OB" if rsi and rsi >= 70 else "OS" if rsi and rsi <= 30 else "N"
        macd_s = "B" if macd and sig and macd > sig else "S"
        stoch_s = "EH" if std and std >= 80 else "EL" if std and std <= 20 else "N"
        
        output.append(
            f"{date}|O:{o}|H:{h}|L:{l}|C:{c}|V:{v}|"
            f"RSI:{rsi}({rsi_s})|E9:{ema9}|E21:{ema21}|E50:{ema50}|E200:{ema200}|T:{trend}|"
            f"MACD:{macd}|S:{sig}|M:{macd_s}|BBU:{bbu}|BBL:{bbl}|ATR:{atr}|"
            f"STK:{stk}|STD:{std}({stoch_s})|ADX:{adx}"
        )
    
    current_idx = df.index[-1]
    curr_price = round_2(df.loc[current_idx, 'close'])
    curr_rsi = round_2(indicators['rsi'].loc[current_idx])
    curr_ema50 = round_2(indicators['ema50'].loc[current_idx])
    curr_ema200 = round_2(indicators['ema200'].loc[current_idx])
    
    output.append(f"\nCURRENT: {curr_price}|RSI:{curr_rsi}|E50:{curr_ema50}|E200:{curr_ema200}")
    
    last_7 = df.tail(7)
    high_7 = round_2(last_7['high'].max())
    low_7 = round_2(last_7['low'].min())
    
    last_30 = df.tail(30)
    high_30 = round_2(last_30['high'].max())
    low_30 = round_2(last_30['low'].min())
    
    output.append(f"7D_RANGE: {low_7}-{high_7}|30D_RANGE: {low_30}-{high_30}")
    
    return "\n".join(output)

def save_report(text):
    output_dir = Path(OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    txt_file = output_dir / "Fetchers/jsons/market_tech.txt"
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"\nSaved: {txt_file.absolute()}")
    return str(txt_file)

def main():
    print("Multi-Instrument Technical Analysis - 35 Day History")
    print()
    
    if not init_mt5():
        return
    
    try:
        all_output = []
        all_output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        all_output.append(f"Period: 35 days")
        all_output.append(f"Instruments: {len(INSTRUMENTS)}")
        
        all_output.append("\nLEGEND:")
        all_output.append("O=Open|H=High|L=Low|C=Close|V=Volume|E=EMA|T=Trend(B=Bull/S=Bear/N=Neutral)")
        all_output.append("RSI: OB=Overbought(>=70)|OS=Oversold(<=30)|N=Neutral")
        all_output.append("M=MACD(B=Bullish/S=Bearish)|BBU=BollingerUpper|BBL=BollingerLower")
        all_output.append("STK=Stochastic K|STD=Stochastic D|Stoch: EH=ExhaustionHigh(>=80)|EL=ExhaustionLow(<=20)|N=Neutral")
        all_output.append("ADX=TrendStrength|ATR=AverageTrueRange")
        
        for symbol, name in INSTRUMENTS.items():
            print(f"\nProcessing {symbol}...")
            df = fetch_data(symbol)
            if df is None or df.empty:
                continue
            
            print(f"Calculating indicators...")
            indicators = calc_indicators(df)
            
            formatted = format_instrument_data(symbol, name, df, indicators, last_n=35)
            all_output.append(formatted)
        
        final_text = "\n".join(all_output)
        save_report(final_text)
        print("\nComplete")
        
    finally:
        mt5.shutdown()
        print("MT5 closed")

if __name__ == "__main__":
    main()