import json
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from pathlib import Path
from datetime import datetime
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

OUTPUT_JSON = "Fetchers/jsons"
OUTPUT_CHARTS = "Fetchers/charts"
INSTRUMENTS = {
    "XAUUSD": "Gold",
    "USA500.IDX": "S&P500",
    "VOL.IDX": "VIX",
    "DOLLAR.IDX": "DXY"
}
TIMEFRAME = mt5.TIMEFRAME_D1

def init_mt5():
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        return False
    if not mt5.account_info():
        print("MT5 not logged in")
        mt5.shutdown()
        return False
    return True

def fetch_data(symbol: str, bars: int = 500) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, bars)
    if rates is None or len(rates) == 0:
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    return df

def round_n(value, n=4):
    if value is None or pd.isna(value) or np.isnan(value) or np.isinf(value):
        return None
    return round(float(value), n)

def parkinson_volatility(df, window=20):
    hl = np.log(df['high'] / df['low'])
    return np.sqrt((1 / (4 * np.log(2))) * (hl ** 2).rolling(window).mean())

def yang_zhang_volatility(df, window=20):
    o = df['open']
    h = df['high']
    l = df['low']
    c = df['close']
    
    oc = np.log(o / c.shift(1))
    cc = np.log(c / c.shift(1))
    ho = np.log(h / o)
    lo = np.log(l / o)
    co = np.log(c / o)
    
    oc_sq = oc ** 2
    cc_sq = cc ** 2
    
    rs = ho * (ho - co) + lo * (lo - co)
    
    close_vol = cc_sq.rolling(window).sum()
    open_vol = oc_sq.rolling(window).sum()
    window_rs = rs.rolling(window).sum()
    
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    result = (open_vol + k * close_vol + (1 - k) * window_rs) / window
    
    return np.sqrt(result) * np.sqrt(252)

def hurst_exponent(series, max_lag=20):
    lags = range(2, max_lag)
    tau = []
    
    for lag in lags:
        pp = np.subtract(series[lag:], series[:-lag])
        tau.append(np.std(pp))
    
    try:
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0]
    except:
        return None

def calculate_hurst_series(df, window=100):
    hurst_values = []
    for i in range(len(df)):
        if i < window:
            hurst_values.append(None)
        else:
            h = hurst_exponent(df['close'].iloc[i-window:i].values)
            hurst_values.append(h)
    return pd.Series(hurst_values, index=df.index)

def volume_profile(df, bins=50):
    price_range = df['high'].max() - df['low'].min()
    bin_size = price_range / bins
    
    price_bins = np.arange(df['low'].min(), df['high'].max() + bin_size, bin_size)
    volume_at_price = np.zeros(len(price_bins) - 1)
    
    for idx, row in df.iterrows():
        price_range_bar = np.linspace(row['low'], row['high'], 10)
        vol_per_price = row['tick_volume'] / len(price_range_bar)
        
        for price in price_range_bar:
            bin_idx = int((price - df['low'].min()) / bin_size)
            if 0 <= bin_idx < len(volume_at_price):
                volume_at_price[bin_idx] += vol_per_price
    
    poc_idx = np.argmax(volume_at_price)
    poc = price_bins[poc_idx]
    
    total_volume = np.sum(volume_at_price)
    cumsum = np.cumsum(sorted(volume_at_price, reverse=True))
    value_area_volume = 0.7 * total_volume
    value_area_bins = np.where(cumsum <= value_area_volume)[0]
    
    volume_in_bins = [(i, volume_at_price[i]) for i in range(len(volume_at_price))]
    volume_in_bins_sorted = sorted(volume_in_bins, key=lambda x: x[1], reverse=True)
    
    value_area_indices = [volume_in_bins_sorted[i][0] for i in range(len(value_area_bins))]
    
    if value_area_indices:
        vah = price_bins[max(value_area_indices) + 1]
        val = price_bins[min(value_area_indices)]
    else:
        vah = poc
        val = poc
    
    return {
        'poc': poc,
        'vah': vah,
        'val': val,
        'profile': (price_bins[:-1], volume_at_price)
    }

def accumulation_distribution_score(df, window=20):
    mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    mfm = mfm.fillna(0)
    mfv = mfm * df['tick_volume']
    ad = mfv.cumsum()
    
    ad_ma = ad.rolling(window).mean()
    ad_std = ad.rolling(window).std()
    
    score = (ad - ad_ma) / ad_std
    score = score.clip(-3, 3) / 3
    
    return score

def spread_estimate(df, window=20):
    return ((df['high'] - df['low']) / df['close']).rolling(window).mean()

def price_efficiency_ratio(df, window=20):
    net_change = abs(df['close'] - df['close'].shift(window))
    total_movement = abs(df['close'].diff()).rolling(window).sum()
    
    return net_change / total_movement

def bayesian_regime_probability(df, window=50):
    returns = df['close'].pct_change()
    
    bull_prob = []
    bear_prob = []
    consol_prob = []
    
    for i in range(len(df)):
        if i < window:
            bull_prob.append(None)
            bear_prob.append(None)
            consol_prob.append(None)
        else:
            recent_returns = returns.iloc[i-window:i]
            
            mean_ret = recent_returns.mean()
            std_ret = recent_returns.std()
            
            if std_ret < 0.005:
                p_bull = 0.33
                p_bear = 0.33
                p_consol = 0.34
            else:
                z_score = mean_ret / std_ret
                
                if z_score > 0.5:
                    p_bull = 0.7
                    p_bear = 0.1
                    p_consol = 0.2
                elif z_score < -0.5:
                    p_bull = 0.1
                    p_bear = 0.7
                    p_consol = 0.2
                else:
                    p_bull = 0.25
                    p_bear = 0.25
                    p_consol = 0.5
            
            bull_prob.append(p_bull)
            bear_prob.append(p_bear)
            consol_prob.append(p_consol)
    
    return pd.DataFrame({
        'bull': bull_prob,
        'bear': bear_prob,
        'consolidation': consol_prob
    }, index=df.index)

def calculate_all_metrics(df):
    park_vol = parkinson_volatility(df)
    yz_vol = yang_zhang_volatility(df)
    hurst = calculate_hurst_series(df)
    ad_score = accumulation_distribution_score(df)
    spread = spread_estimate(df)
    efficiency = price_efficiency_ratio(df)
    regime_prob = bayesian_regime_probability(df)
    
    vol_percentile = park_vol.rank(pct=True) * 100
    vol_regime = pd.cut(vol_percentile, bins=[0, 33, 66, 100], labels=['low', 'medium', 'high'])
    
    hurst_state = hurst.apply(lambda x: 'trending' if x and x > 0.5 else 'mean_reverting' if x and x < 0.5 else 'random' if x else None)
    
    return {
        'park_vol': park_vol,
        'yz_vol': yz_vol,
        'hurst': hurst,
        'hurst_state': hurst_state,
        'ad_score': ad_score,
        'spread': spread,
        'efficiency': efficiency,
        'vol_percentile': vol_percentile,
        'vol_regime': vol_regime,
        'regime_prob': regime_prob
    }

def build_json_output(symbol, name, df, metrics, vol_prof, last_n=35):
    df_slice = df.tail(last_n).copy()
    daily_data = {}
    
    for idx in range(len(df_slice)):
        i = df_slice.index[idx]
        date = df_slice.loc[i, 'time'].strftime('%Y-%m-%d')
        
        if date not in daily_data:
            daily_data[date] = {}
        
        daily_data[date][symbol] = {
            "name": name,
            "volatility": {
                "parkinson": round_n(metrics['park_vol'].loc[i]),
                "yang_zhang": round_n(metrics['yz_vol'].loc[i]),
                "regime": str(metrics['vol_regime'].loc[i]) if pd.notna(metrics['vol_regime'].loc[i]) else None,
                "percentile": round_n(metrics['vol_percentile'].loc[i], 2)
            },
            "hurst": {
                "value": round_n(metrics['hurst'].loc[i]),
                "state": metrics['hurst_state'].loc[i]
            },
            "volume": {
                "profile_poc": round_n(vol_prof['poc'], 2),
                "profile_vah": round_n(vol_prof['vah'], 2),
                "profile_val": round_n(vol_prof['val'], 2),
                "accumulation_score": round_n(metrics['ad_score'].loc[i])
            },
            "microstructure": {
                "spread_estimate": round_n(metrics['spread'].loc[i]),
                "efficiency_ratio": round_n(metrics['efficiency'].loc[i])
            },
            "probability": {
                "bull_regime": round_n(metrics['regime_prob']['bull'].loc[i], 2),
                "bear_regime": round_n(metrics['regime_prob']['bear'].loc[i], 2),
                "consolidation": round_n(metrics['regime_prob']['consolidation'].loc[i], 2)
            }
        }
    
    return daily_data

def create_charts(symbol, name, df, metrics, vol_prof):
    charts_dir = Path(OUTPUT_CHARTS)
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    df_chart = df.tail(100).copy()
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df_chart['time'], df_chart['close'], label='Price', linewidth=1.5, color='black')
    ax1.axhline(y=vol_prof['poc'], color='red', linestyle='--', label=f'POC: {vol_prof["poc"]:.2f}', linewidth=2)
    ax1.axhline(y=vol_prof['vah'], color='green', linestyle='--', label=f'VAH: {vol_prof["vah"]:.2f}', linewidth=1)
    ax1.axhline(y=vol_prof['val'], color='green', linestyle='--', label=f'VAL: {vol_prof["val"]:.2f}', linewidth=1)
    ax1.fill_between(df_chart['time'], vol_prof['val'], vol_prof['vah'], alpha=0.2, color='green')
    ax1.set_title(f'{name} - Price with Volume Profile Levels', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(df_chart['time'], metrics['park_vol'].loc[df_chart.index], label='Parkinson', linewidth=1.5)
    ax2.plot(df_chart['time'], metrics['yz_vol'].loc[df_chart.index], label='Yang-Zhang', linewidth=1.5)
    ax2.set_title('Volatility Estimates', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Volatility')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(df_chart['time'], metrics['hurst'].loc[df_chart.index], linewidth=1.5, color='purple')
    ax3.axhline(y=0.5, color='red', linestyle='--', label='Random Walk', linewidth=1)
    ax3.fill_between(df_chart['time'], 0.5, 1, alpha=0.2, color='green', label='Trending')
    ax3.fill_between(df_chart['time'], 0, 0.5, alpha=0.2, color='orange', label='Mean Reverting')
    ax3.set_title('Hurst Exponent', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Hurst Value')
    ax3.set_ylim(0, 1)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    ax4 = fig.add_subplot(gs[2, :])
    bull = metrics['regime_prob']['bull'].loc[df_chart.index].fillna(0)
    bear = metrics['regime_prob']['bear'].loc[df_chart.index].fillna(0)
    consol = metrics['regime_prob']['consolidation'].loc[df_chart.index].fillna(0)
    
    ax4.fill_between(df_chart['time'], 0, bull, label='Bull', alpha=0.7, color='green')
    ax4.fill_between(df_chart['time'], bull, bull + consol, label='Consolidation', alpha=0.7, color='gray')
    ax4.fill_between(df_chart['time'], bull + consol, bull + consol + bear, label='Bear', alpha=0.7, color='red')
    ax4.set_title('Regime Probability Distribution', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Probability')
    ax4.set_ylim(0, 1)
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    chart_file = charts_dir / f"{symbol}_deepin.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    fig2, ax = plt.subplots(figsize=(10, 8))
    price_bins, volume_at_price = vol_prof['profile']
    ax.barh(price_bins, volume_at_price, height=price_bins[1]-price_bins[0], alpha=0.7, color='steelblue')
    ax.axhline(y=vol_prof['poc'], color='red', linestyle='--', linewidth=2, label=f'POC: {vol_prof["poc"]:.2f}')
    ax.axhline(y=vol_prof['vah'], color='green', linestyle='--', linewidth=1.5, label=f'VAH: {vol_prof["vah"]:.2f}')
    ax.axhline(y=vol_prof['val'], color='green', linestyle='--', linewidth=1.5, label=f'VAL: {vol_prof["val"]:.2f}')
    ax.set_title(f'{name} - Volume Profile Distribution', fontsize=14, fontweight='bold')
    ax.set_xlabel('Volume')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='x')
    
    profile_file = charts_dir / f"{symbol}_volume_profile.png"
    plt.savefig(profile_file, dpi=150, bbox_inches='tight')
    plt.close()

def main():
    if not init_mt5():
        return
    
    try:
        all_daily_data = {}
        
        for symbol, name in INSTRUMENTS.items():
            df = fetch_data(symbol, 500)
            if df is None or df.empty:
                continue
            
            metrics = calculate_all_metrics(df)
            vol_prof = volume_profile(df.tail(100))
            
            daily_data = build_json_output(symbol, name, df, metrics, vol_prof, last_n=35)
            
            for date, instruments in daily_data.items():
                if date not in all_daily_data:
                    all_daily_data[date] = {}
                all_daily_data[date].update(instruments)
            
            create_charts(symbol, name, df, metrics, vol_prof)
        
        output_dir = Path(OUTPUT_JSON)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        daily_file = output_dir / "deepin_daily.json"
        with open(daily_file, 'w') as f:
            json.dump({
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "daily_data": all_daily_data
            }, f, indent=2)
        
        print("Done")
        
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()