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
    print("Attempting to connect to MetaTrader 5...")
    
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"\n❌ MT5 Connection Failed: {error}")
        print("\n🔧 TROUBLESHOOTING STEPS:")
        print("1. Open MetaTrader 5 desktop application")
        print("2. Login to your trading account (File → Login to Trade Account)")
        print("3. Make sure you see 'Connected' in bottom-right corner of MT5")
        print("4. Keep MT5 running and try this script again")
        print("\nIf MT5 is already open and logged in:")
        print("- Restart MT5 completely")
        print("- Make sure you're using the correct MT5 (not MT4)")
        print("- Check if your broker allows API/automated trading")
        return False
    
    account = mt5.account_info()
    if not account:
        print("\n❌ Account Info Failed - MT5 not logged in")
        print("\n🔧 SOLUTION:")
        print("1. In MT5, go to: File → Login to Trade Account")
        print("2. Enter your credentials and connect")
        print("3. Run this script again")
        mt5.shutdown()
        return False
    
    print(f"✅ Connected Successfully!")
    print(f"   Account: {account.login}")
    print(f"   Server: {account.server}")
    print(f"   Balance: {account.balance} {account.currency}")
    return True

def fetch_data(symbol: str) -> Optional[pd.DataFrame]:
    # Fetch last 450 bars regardless of current time (works on weekends)
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, 450)
    
    if rates is None or len(rates) == 0:
        print(f"{symbol}: Failed to fetch data")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    
    last_bar_date = df['time'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"{symbol}: Fetched {len(df)} daily bars (Last bar: {last_bar_date})")
    return df

def calc_indicators(df):
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    
    # Core EMAs
    ema9 = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    ema21 = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()
    
    # RSI
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    
    # MACD
    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd = macd_ind.macd()
    signal = macd_ind.macd_signal()
    macd_hist = macd_ind.macd_diff()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()
    bb_middle = bb.bollinger_mavg()
    bb_width = ((bb_upper - bb_lower) / bb_middle) * 100
    
    # ATR
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    
    # Stochastic
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()
    
    # ADX (Trend Strength)
    adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
    adx = adx_ind.adx()
    adx_pos = adx_ind.adx_pos()
    adx_neg = adx_ind.adx_neg()
    
    # Ichimoku Cloud
    ichimoku = ta.trend.IchimokuIndicator(high, low, window1=9, window2=26, window3=52)
    tenkan = ichimoku.ichimoku_conversion_line()
    kijun = ichimoku.ichimoku_base_line()
    senkou_a = ichimoku.ichimoku_a()
    senkou_b = ichimoku.ichimoku_b()
    
    # On Balance Volume (OBV)
    obv = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    
    # Volume Weighted Average Price (approximation)
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).rolling(window=20).sum() / volume.rolling(window=20).sum()
    
    # Parabolic SAR
    psar = ta.trend.PSARIndicator(high, low, close).psar()
    
    # Awesome Oscillator
    ao = ta.momentum.AwesomeOscillatorIndicator(high, low).awesome_oscillator()
    
    # Williams %R
    willr = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r()
    
    # Commodity Channel Index
    cci = ta.trend.CCIIndicator(high, low, close, window=20).cci()
    
    # Money Flow Index
    mfi = ta.volume.MFIIndicator(high, low, close, volume, window=14).money_flow_index()
    
    # Rate of Change
    roc = ta.momentum.ROCIndicator(close, window=12).roc()
    
    return {
        'rsi': rsi, 'ema9': ema9, 'ema21': ema21, 'ema50': ema50, 'ema200': ema200,
        'macd': macd, 'signal': signal, 'macd_hist': macd_hist,
        'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_middle': bb_middle, 'bb_width': bb_width,
        'atr': atr, 'stoch_k': stoch_k, 'stoch_d': stoch_d, 
        'adx': adx, 'adx_pos': adx_pos, 'adx_neg': adx_neg,
        'tenkan': tenkan, 'kijun': kijun, 'senkou_a': senkou_a, 'senkou_b': senkou_b,
        'obv': obv, 'vwap': vwap, 'psar': psar, 'ao': ao, 'willr': willr,
        'cci': cci, 'mfi': mfi, 'roc': roc
    }

def determine_signals(c, indicators, i):
    """Calculate strategy signals based on proven technical setups"""
    signals = []
    
    # EMA Alignment (Strong trend confirmation)
    ema9 = indicators['ema9'].loc[i]
    ema21 = indicators['ema21'].loc[i]
    ema50 = indicators['ema50'].loc[i]
    ema200 = indicators['ema200'].loc[i]
    
    if all([c, ema9, ema21, ema50, ema200]):
        if c > ema9 > ema21 > ema50 > ema200:
            signals.append("EMA_BULL_STACK")
        elif c < ema9 < ema21 < ema50 < ema200:
            signals.append("EMA_BEAR_STACK")
    
    # Golden/Death Cross (EMA50/200)
    if ema50 and ema200:
        if i > 0:
            prev_50 = indicators['ema50'].loc[i-1] if not pd.isna(indicators['ema50'].loc[i-1]) else None
            prev_200 = indicators['ema200'].loc[i-1] if not pd.isna(indicators['ema200'].loc[i-1]) else None
            if prev_50 and prev_200:
                if prev_50 <= prev_200 and ema50 > ema200:
                    signals.append("GOLDEN_CROSS")
                elif prev_50 >= prev_200 and ema50 < ema200:
                    signals.append("DEATH_CROSS")
    
    # RSI Divergence zones
    rsi = indicators['rsi'].loc[i]
    if rsi:
        if rsi >= 70:
            signals.append("RSI_OB")
        elif rsi <= 30:
            signals.append("RSI_OS")
    
    # MACD Crossover
    macd = indicators['macd'].loc[i]
    sig = indicators['signal'].loc[i]
    if macd and sig and i > 0:
        prev_macd = indicators['macd'].loc[i-1] if not pd.isna(indicators['macd'].loc[i-1]) else None
        prev_sig = indicators['signal'].loc[i-1] if not pd.isna(indicators['signal'].loc[i-1]) else None
        if prev_macd and prev_sig:
            if prev_macd <= prev_sig and macd > sig:
                signals.append("MACD_BULL_X")
            elif prev_macd >= prev_sig and macd < sig:
                signals.append("MACD_BEAR_X")
    
    # ADX Trend Strength
    adx = indicators['adx'].loc[i]
    adx_pos = indicators['adx_pos'].loc[i]
    adx_neg = indicators['adx_neg'].loc[i]
    if adx:
        if adx > 25:
            if adx_pos and adx_neg and adx_pos > adx_neg:
                signals.append("STRONG_UP")
            elif adx_pos and adx_neg and adx_neg > adx_pos:
                signals.append("STRONG_DOWN")
        elif adx < 20:
            signals.append("WEAK_TREND")
    
    # Bollinger Band Squeeze/Breakout
    bb_width = indicators['bb_width'].loc[i]
    if bb_width and bb_width < 1.5:
        signals.append("BB_SQUEEZE")
    
    bb_upper = indicators['bb_upper'].loc[i]
    bb_lower = indicators['bb_lower'].loc[i]
    if c and bb_upper and bb_lower:
        if c >= bb_upper:
            signals.append("BB_BREAKOUT_UP")
        elif c <= bb_lower:
            signals.append("BB_BREAKOUT_DN")
    
    # Ichimoku Cloud Position
    senkou_a = indicators['senkou_a'].loc[i]
    senkou_b = indicators['senkou_b'].loc[i]
    if c and senkou_a and senkou_b:
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        if c > cloud_top:
            signals.append("ABOVE_CLOUD")
        elif c < cloud_bottom:
            signals.append("BELOW_CLOUD")
        else:
            signals.append("IN_CLOUD")
    
    # Tenkan/Kijun Cross (Ichimoku signal)
    tenkan = indicators['tenkan'].loc[i]
    kijun = indicators['kijun'].loc[i]
    if tenkan and kijun and i > 0:
        prev_tenkan = indicators['tenkan'].loc[i-1] if not pd.isna(indicators['tenkan'].loc[i-1]) else None
        prev_kijun = indicators['kijun'].loc[i-1] if not pd.isna(indicators['kijun'].loc[i-1]) else None
        if prev_tenkan and prev_kijun:
            if prev_tenkan <= prev_kijun and tenkan > kijun:
                signals.append("TK_BULL_X")
            elif prev_tenkan >= prev_kijun and tenkan < kijun:
                signals.append("TK_BEAR_X")
    
    # Money Flow Index
    mfi = indicators['mfi'].loc[i]
    if mfi:
        if mfi >= 80:
            signals.append("MFI_OB")
        elif mfi <= 20:
            signals.append("MFI_OS")
    
    # CCI Extreme readings
    cci = indicators['cci'].loc[i]
    if cci:
        if cci > 100:
            signals.append("CCI_OB")
        elif cci < -100:
            signals.append("CCI_OS")
    
    # Williams %R
    willr = indicators['willr'].loc[i]
    if willr:
        if willr >= -20:
            signals.append("WILL_OB")
        elif willr <= -80:
            signals.append("WILL_OS")
    
    return signals

def format_instrument_data(symbol: str, name: str, df, indicators, last_n=35):
    df_slice = df.tail(last_n).copy()
    output = []
    
    output.append(f"\n{'='*100}")
    output.append(f"{name} ({symbol}) - 35 Day History with Advanced Technicals")
    output.append(f"{'='*100}\n")
    
    for idx in range(len(df_slice)):
        i = df_slice.index[idx]
        date = df_slice.loc[i, 'time'].strftime('%m-%d-%y')
        o = round_2(df_slice.loc[i, 'open'])
        h = round_2(df_slice.loc[i, 'high'])
        l = round_2(df_slice.loc[i, 'low'])
        c = round_2(df_slice.loc[i, 'close'])
        v = int(df_slice.loc[i, 'tick_volume'])
        
        # Core indicators
        rsi = round_2(indicators['rsi'].loc[i])
        ema9 = round_2(indicators['ema9'].loc[i])
        ema21 = round_2(indicators['ema21'].loc[i])
        ema50 = round_2(indicators['ema50'].loc[i])
        ema200 = round_2(indicators['ema200'].loc[i])
        
        macd = round_2(indicators['macd'].loc[i])
        sig = round_2(indicators['signal'].loc[i])
        macd_hist = round_2(indicators['macd_hist'].loc[i])
        
        bbu = round_2(indicators['bb_upper'].loc[i])
        bbl = round_2(indicators['bb_lower'].loc[i])
        bbm = round_2(indicators['bb_middle'].loc[i])
        bbw = round_2(indicators['bb_width'].loc[i])
        
        atr = round_2(indicators['atr'].loc[i])
        stk = round_2(indicators['stoch_k'].loc[i])
        std = round_2(indicators['stoch_d'].loc[i])
        
        adx = round_2(indicators['adx'].loc[i])
        adx_pos = round_2(indicators['adx_pos'].loc[i])
        adx_neg = round_2(indicators['adx_neg'].loc[i])
        
        # Advanced indicators
        tenkan = round_2(indicators['tenkan'].loc[i])
        kijun = round_2(indicators['kijun'].loc[i])
        senkou_a = round_2(indicators['senkou_a'].loc[i])
        senkou_b = round_2(indicators['senkou_b'].loc[i])
        
        vwap = round_2(indicators['vwap'].loc[i])
        psar = round_2(indicators['psar'].loc[i])
        ao = round_2(indicators['ao'].loc[i])
        willr = round_2(indicators['willr'].loc[i])
        cci = round_2(indicators['cci'].loc[i])
        mfi = round_2(indicators['mfi'].loc[i])
        roc = round_2(indicators['roc'].loc[i])
        
        # Signal determination
        signals = determine_signals(c, indicators, i)
        signal_str = ",".join(signals) if signals else "NEUTRAL"
        
        # Trend classification
        trend = "BULL" if c and ema200 and c > ema200 else "BEAR" if c and ema200 and c < ema200 else "NEUT"
        
        # Price vs EMAs position
        ema_pos = ""
        if c and ema50 and ema200:
            if c > ema50 > ema200:
                ema_pos = "AB50&200"
            elif c < ema50 < ema200:
                ema_pos = "BL50&200"
            elif c > ema50 and ema50 < ema200:
                ema_pos = "AB50/BL200"
            else:
                ema_pos = "MIXED"
        
        # MACD momentum
        macd_mom = "BULL" if macd and sig and macd > sig else "BEAR"
        
        # ADX strength classification
        adx_str = "STRONG" if adx and adx > 25 else "WEAK" if adx and adx < 20 else "MOD"
        
        output.append(f"--- {date} ---")
        output.append(f"PRICE: O:{o}|H:{h}|L:{l}|C:{c}|V:{v}")
        output.append(f"EMAS: E9:{ema9}|E21:{ema21}|E50:{ema50}|E200:{ema200}|POS:{ema_pos}|TREND:{trend}")
        output.append(f"MOMENTUM: RSI:{rsi}|MACD:{macd}|SIG:{sig}|HIST:{macd_hist}|DIR:{macd_mom}")
        output.append(f"TREND_STR: ADX:{adx}({adx_str})|+DI:{adx_pos}|-DI:{adx_neg}")
        output.append(f"BANDS: BBU:{bbu}|BBM:{bbm}|BBL:{bbl}|WIDTH:{bbw}|ATR:{atr}")
        output.append(f"STOCH: K:{stk}|D:{std}")
        output.append(f"ICHIMOKU: TK:{tenkan}|KJ:{kijun}|SA:{senkou_a}|SB:{senkou_b}")
        output.append(f"ADVANCED: VWAP:{vwap}|PSAR:{psar}|AO:{ao}|WILL:{willr}|CCI:{cci}|MFI:{mfi}|ROC:{roc}")
        output.append(f"SIGNALS: {signal_str}")
        output.append("")
    
    # Current market summary
    current_idx = df.index[-1]
    curr_price = round_2(df.loc[current_idx, 'close'])
    curr_rsi = round_2(indicators['rsi'].loc[current_idx])
    curr_ema50 = round_2(indicators['ema50'].loc[current_idx])
    curr_ema200 = round_2(indicators['ema200'].loc[current_idx])
    curr_adx = round_2(indicators['adx'].loc[current_idx])
    curr_signals = determine_signals(curr_price, indicators, current_idx)
    
    output.append(f"\n{'='*100}")
    output.append(f"CURRENT MARKET STATE")
    output.append(f"{'='*100}")
    output.append(f"PRICE: {curr_price}")
    output.append(f"KEY_LEVELS: EMA50:{curr_ema50}|EMA200:{curr_ema200}")
    output.append(f"MOMENTUM: RSI:{curr_rsi}|ADX:{curr_adx}")
    output.append(f"ACTIVE_SIGNALS: {','.join(curr_signals) if curr_signals else 'NEUTRAL'}")
    
    # Range analysis
    last_7 = df.tail(7)
    high_7 = round_2(last_7['high'].max())
    low_7 = round_2(last_7['low'].min())
    range_7 = round_2(high_7 - low_7)
    
    last_30 = df.tail(30)
    high_30 = round_2(last_30['high'].max())
    low_30 = round_2(last_30['low'].min())
    range_30 = round_2(high_30 - low_30)
    
    output.append(f"\nRANGE_ANALYSIS:")
    output.append(f"7D: {low_7}-{high_7} (Range:{range_7})")
    output.append(f"30D: {low_30}-{high_30} (Range:{range_30})")
    
    # Distance from EMAs
    if curr_price and curr_ema50 and curr_ema200:
        dist_50 = round_2(((curr_price - curr_ema50) / curr_ema50) * 100)
        dist_200 = round_2(((curr_price - curr_ema200) / curr_ema200) * 100)
        output.append(f"\nDISTANCE_FROM_EMAS:")
        output.append(f"From_EMA50: {dist_50}%")
        output.append(f"From_EMA200: {dist_200}%")
    
    return "\n".join(output)

def save_report(text):
    output_dir = Path(OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    txt_file = output_dir / "Fetchers/jsons/market_tech.txt"
    txt_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"\nSaved: {txt_file.absolute()}")
    return str(txt_file)

def main():
    print("Multi-Instrument Advanced Technical Analysis - 35 Day History")
    print("(Works on weekends - uses last available data)")
    print()
    
    if not init_mt5():
        return
    
    try:
        all_output = []
        all_output.append(f"{'='*100}")
        all_output.append(f"ADVANCED TECHNICAL ANALYSIS REPORT")
        all_output.append(f"{'='*100}")
        all_output.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        all_output.append(f"Period: Last 35 trading days")
        all_output.append(f"Instruments: {len(INSTRUMENTS)}")
        all_output.append(f"Note: Data reflects last available market close (Friday close if run on weekends)")
        
        all_output.append("\n" + "="*100)
        all_output.append("SIGNAL LEGEND")
        all_output.append("="*100)
        all_output.append("EMA_BULL_STACK: Price > E9 > E21 > E50 > E200 (Strong uptrend)")
        all_output.append("EMA_BEAR_STACK: Price < E9 < E21 < E50 < E200 (Strong downtrend)")
        all_output.append("GOLDEN_CROSS: EMA50 crosses above EMA200 (Bullish)")
        all_output.append("DEATH_CROSS: EMA50 crosses below EMA200 (Bearish)")
        all_output.append("RSI_OB/OS: RSI Overbought (>=70) / Oversold (<=30)")
        all_output.append("MACD_BULL_X/BEAR_X: MACD crosses signal line")
        all_output.append("STRONG_UP/DOWN: ADX > 25 with directional bias")
        all_output.append("WEAK_TREND: ADX < 20 (consolidation)")
        all_output.append("BB_SQUEEZE: Bollinger Band Width < 1.5 (low volatility)")
        all_output.append("BB_BREAKOUT_UP/DN: Price breaks Bollinger Bands")
        all_output.append("ABOVE/BELOW/IN_CLOUD: Ichimoku Cloud position")
        all_output.append("TK_BULL_X/BEAR_X: Tenkan/Kijun cross (Ichimoku signal)")
        all_output.append("MFI_OB/OS: Money Flow Index extreme (>=80 / <=20)")
        all_output.append("CCI_OB/OS: Commodity Channel Index extreme (>100 / <-100)")
        all_output.append("WILL_OB/OS: Williams %R extreme (>=-20 / <=-80)")
        
        all_output.append("\n" + "="*100)
        all_output.append("INDICATOR ABBREVIATIONS")
        all_output.append("="*100)
        all_output.append("E9/E21/E50/E200: Exponential Moving Averages")
        all_output.append("RSI: Relative Strength Index | MACD: Moving Average Convergence Divergence")
        all_output.append("ADX: Average Directional Index | +DI/-DI: Directional Indicators")
        all_output.append("BBU/BBM/BBL: Bollinger Upper/Middle/Lower | WIDTH: BB Width %")
        all_output.append("ATR: Average True Range | K/D: Stochastic K/D")
        all_output.append("TK: Tenkan-sen | KJ: Kijun-sen | SA/SB: Senkou Span A/B")
        all_output.append("VWAP: Volume Weighted Average Price | PSAR: Parabolic SAR")
        all_output.append("AO: Awesome Oscillator | WILL: Williams %R")
        all_output.append("CCI: Commodity Channel Index | MFI: Money Flow Index")
        all_output.append("ROC: Rate of Change")
        
        for symbol, name in INSTRUMENTS.items():
            print(f"\nProcessing {symbol}...")
            df = fetch_data(symbol)
            if df is None or df.empty:
                continue
            
            print(f"Calculating advanced indicators...")
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