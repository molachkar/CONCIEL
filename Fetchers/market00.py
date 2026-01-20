import json
from datetime import datetime
from typing import Optional
import pandas as pd
import ta
import MetaTrader5 as mt5
from pathlib import Path

OUTPUT_PATH = "Fetchers/jsons"
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
        print("MT5 not logged in")
        mt5.shutdown()
        return False
    
    return True

def fetch_data(symbol: str) -> Optional[pd.DataFrame]:
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, 450)
    
    if rates is None or len(rates) == 0:
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    return df

def calc_indicators(df):
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    
    ema9 = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    ema21 = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()
    
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    
    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd = macd_ind.macd()
    signal = macd_ind.macd_signal()
    macd_hist = macd_ind.macd_diff()
    
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()
    bb_middle = bb.bollinger_mavg()
    bb_width = ((bb_upper - bb_lower) / bb_middle) * 100
    
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()
    
    adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
    adx = adx_ind.adx()
    adx_pos = adx_ind.adx_pos()
    adx_neg = adx_ind.adx_neg()
    
    ichimoku = ta.trend.IchimokuIndicator(high, low, window1=9, window2=26, window3=52)
    tenkan = ichimoku.ichimoku_conversion_line()
    kijun = ichimoku.ichimoku_base_line()
    senkou_a = ichimoku.ichimoku_a()
    senkou_b = ichimoku.ichimoku_b()
    
    obv = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).rolling(window=20).sum() / volume.rolling(window=20).sum()
    
    psar = ta.trend.PSARIndicator(high, low, close).psar()
    ao = ta.momentum.AwesomeOscillatorIndicator(high, low).awesome_oscillator()
    willr = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r()
    cci = ta.trend.CCIIndicator(high, low, close, window=20).cci()
    mfi = ta.volume.MFIIndicator(high, low, close, volume, window=14).money_flow_index()
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
    signals = []
    
    ema9 = indicators['ema9'].loc[i]
    ema21 = indicators['ema21'].loc[i]
    ema50 = indicators['ema50'].loc[i]
    ema200 = indicators['ema200'].loc[i]
    
    if all([c, ema9, ema21, ema50, ema200]):
        if c > ema9 > ema21 > ema50 > ema200:
            signals.append("EMA_BULL_STACK")
        elif c < ema9 < ema21 < ema50 < ema200:
            signals.append("EMA_BEAR_STACK")
    
    if ema50 and ema200 and i > 0:
        prev_50 = indicators['ema50'].loc[i-1] if not pd.isna(indicators['ema50'].loc[i-1]) else None
        prev_200 = indicators['ema200'].loc[i-1] if not pd.isna(indicators['ema200'].loc[i-1]) else None
        if prev_50 and prev_200:
            if prev_50 <= prev_200 and ema50 > ema200:
                signals.append("GOLDEN_CROSS")
            elif prev_50 >= prev_200 and ema50 < ema200:
                signals.append("DEATH_CROSS")
    
    rsi = indicators['rsi'].loc[i]
    if rsi:
        if rsi >= 70:
            signals.append("RSI_OB")
        elif rsi <= 30:
            signals.append("RSI_OS")
    
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
    
    mfi = indicators['mfi'].loc[i]
    if mfi:
        if mfi >= 80:
            signals.append("MFI_OB")
        elif mfi <= 20:
            signals.append("MFI_OS")
    
    cci = indicators['cci'].loc[i]
    if cci:
        if cci > 100:
            signals.append("CCI_OB")
        elif cci < -100:
            signals.append("CCI_OS")
    
    willr = indicators['willr'].loc[i]
    if willr:
        if willr >= -20:
            signals.append("WILL_OB")
        elif willr <= -80:
            signals.append("WILL_OS")
    
    return signals

def build_daily_data_structure(symbol: str, name: str, df, indicators, last_n=35):
    df_slice = df.tail(last_n).copy()
    daily_data = {}
    
    for idx in range(len(df_slice)):
        i = df_slice.index[idx]
        date = df_slice.loc[i, 'time'].strftime('%Y-%m-%d')
        
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
        
        signals = determine_signals(c, indicators, i)
        
        if date not in daily_data:
            daily_data[date] = {}
        
        daily_data[date][symbol] = {
            "name": name,
            "price": {"o": o, "h": h, "l": l, "c": c, "v": v},
            "ema": {"e9": ema9, "e21": ema21, "e50": ema50, "e200": ema200},
            "momentum": {"rsi": rsi, "macd": macd, "sig": sig, "hist": macd_hist},
            "trend": {"adx": adx, "pos": adx_pos, "neg": adx_neg},
            "bb": {"upper": bbu, "mid": bbm, "lower": bbl, "width": bbw},
            "vol": {"atr": atr},
            "stoch": {"k": stk, "d": std},
            "ichimoku": {"tk": tenkan, "kj": kijun, "sa": senkou_a, "sb": senkou_b},
            "adv": {"vwap": vwap, "psar": psar, "ao": ao, "willr": willr, "cci": cci, "mfi": mfi, "roc": roc},
            "signals": signals
        }
    
    return daily_data

def save_json_output(all_data):
    output_dir = Path(OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / "market_technicals.json"
    
    output = {
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "instruments": list(INSTRUMENTS.keys()),
        "daily_data": all_data
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return str(json_file)

def main():
    if not init_mt5():
        return
    
    try:
        all_daily_data = {}
        
        for symbol, name in INSTRUMENTS.items():
            df = fetch_data(symbol)
            if df is None or df.empty:
                continue
            
            indicators = calc_indicators(df)
            daily_data = build_daily_data_structure(symbol, name, df, indicators, last_n=35)
            
            for date, instruments in daily_data.items():
                if date not in all_daily_data:
                    all_daily_data[date] = {}
                all_daily_data[date].update(instruments)
        
        save_json_output(all_daily_data)
        print("Done")
        
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()