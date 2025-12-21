#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

INPUT_FOLDER = "TEXT/daily_snapshots"
OUTPUT_FOLDER = "TEXT/daily_summaries"

class DataFormatter:
    """Handles formatting of various data types"""
    
    @staticmethod
    def format_number(num: Optional[Union[int, float]], prefix: str = "$", decimals: int = 2) -> str:
        """Format number with prefix and proper decimals"""
        if num is None:
            return "N/A"
        try:
            return f"{prefix}{num:,.{decimals}f}"
        except (ValueError, TypeError):
            return str(num)
    
    @staticmethod
    def calculate_change(open_price: Optional[float], close_price: Optional[float]) -> tuple:
        """Calculate absolute and percentage change"""
        if open_price is None or close_price is None or open_price == 0:
            return None, None
        try:
            change = close_price - open_price
            pct_change = (change / open_price) * 100
            return change, pct_change
        except (ValueError, TypeError, ZeroDivisionError):
            return None, None
    
    @staticmethod
    def parse_numeric(value: Any) -> Optional[float]:
        """Safely parse numeric value from various formats"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                cleaned = value.replace('%', '').replace(',', '').replace('$', '').replace('B', '').replace('M', '').replace('K', '').strip()
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def interpret_rsi(rsi: Optional[float]) -> str:
        """Interpret RSI value"""
        if rsi is None:
            return "no RSI data"
        if rsi < 30:
            return "oversold conditions"
        elif rsi < 45:
            return "bearish momentum"
        elif rsi < 55:
            return "neutral momentum"
        elif rsi < 70:
            return "bullish momentum"
        else:
            return "overbought conditions"
    
    @staticmethod
    def interpret_ema_trend(trend: Optional[str]) -> str:
        """Interpret EMA trend"""
        if not trend:
            return "no trend data"
        return f"{trend.lower()} trend"


class InflationDataFormatter:
    """Formats monthly inflation and economic indicators"""
    
    @staticmethod
    def format(inflation_data: Dict[str, Any]) -> Optional[str]:
        """Convert inflation data to simple, readable format"""
        if not inflation_data:
            return None
        
        indicators = inflation_data.get("indicators", {})
        
        if not indicators:
            return "No inflation data available for this period."
        
        sections = []
        
        # Inflation Indicators
        inflation_items = []
        
        if "CPI" in indicators and indicators["CPI"].get("data"):
            cpi_data = indicators["CPI"]["data"][-1]
            cpi_val = DataFormatter.parse_numeric(cpi_data.get("value"))
            cpi_date = cpi_data.get("date", "")
            if cpi_val is not None:
                try:
                    date_obj = datetime.fromisoformat(cpi_date)
                    month_str = date_obj.strftime("%B %Y")
                    inflation_items.append(f"Consumer Price Index (CPI) stood at {cpi_val:.2f} in {month_str}.")
                except:
                    inflation_items.append(f"Consumer Price Index (CPI) stood at {cpi_val:.2f}.")
        
        if "PCE" in indicators and indicators["PCE"].get("data"):
            pce_data = indicators["PCE"]["data"][-1]
            pce_val = DataFormatter.parse_numeric(pce_data.get("value"))
            pce_date = pce_data.get("date", "")
            if pce_val is not None:
                try:
                    date_obj = datetime.fromisoformat(pce_date)
                    month_str = date_obj.strftime("%B %Y")
                    inflation_items.append(f"Personal Consumption Expenditures (PCE) was {pce_val:.2f} in {month_str}.")
                except:
                    inflation_items.append(f"Personal Consumption Expenditures (PCE) was {pce_val:.2f}.")
        
        if "PPI" in indicators and indicators["PPI"].get("data"):
            ppi_data = indicators["PPI"]["data"][-1]
            ppi_val = DataFormatter.parse_numeric(ppi_data.get("value"))
            ppi_date = ppi_data.get("date", "")
            if ppi_val is not None:
                try:
                    date_obj = datetime.fromisoformat(ppi_date)
                    month_str = date_obj.strftime("%B %Y")
                    inflation_items.append(f"Producer Price Index (PPI) was {ppi_val:.2f} in {month_str}.")
                except:
                    inflation_items.append(f"Producer Price Index (PPI) was {ppi_val:.2f}.")
        
        if inflation_items:
            sections.append("INFLATION INDICATORS:\n" + " ".join(inflation_items))
        
        # Employment
        employment_items = []
        
        if "UNEMPLOYMENT" in indicators and indicators["UNEMPLOYMENT"].get("data"):
            unemp_data = indicators["UNEMPLOYMENT"]["data"][-1]
            unemp_val = DataFormatter.parse_numeric(unemp_data.get("value"))
            unemp_date = unemp_data.get("date", "")
            if unemp_val is not None:
                try:
                    date_obj = datetime.fromisoformat(unemp_date)
                    month_str = date_obj.strftime("%B %Y")
                    employment_items.append(f"Unemployment rate was {unemp_val:.1f}% in {month_str}.")
                except:
                    employment_items.append(f"Unemployment rate was {unemp_val:.1f}%.")
        
        if "NFP" in indicators and indicators["NFP"].get("data"):
            nfp_data = indicators["NFP"]["data"][-1]
            nfp_val = DataFormatter.parse_numeric(nfp_data.get("value"))
            if nfp_val is not None:
                employment_items.append(f"Non-Farm Payrolls totaled {nfp_val:,.0f}K jobs.")
        
        if employment_items:
            sections.append("EMPLOYMENT:\n" + " ".join(employment_items))
        
        # Monetary Policy
        monetary_items = []
        
        if "FEDFUNDS" in indicators and indicators["FEDFUNDS"].get("data"):
            fedfunds_data = indicators["FEDFUNDS"]["data"]
            if fedfunds_data:
                latest = fedfunds_data[-1]
                latest_val = DataFormatter.parse_numeric(latest.get("value"))
                latest_date = latest.get("date", "")
                
                if latest_val is not None:
                    try:
                        date_obj = datetime.fromisoformat(latest_date)
                        month_str = date_obj.strftime("%B %Y")
                        monetary_items.append(f"Federal Funds Rate was {latest_val:.2f}% as of {month_str}.")
                    except:
                        monetary_items.append(f"Federal Funds Rate was {latest_val:.2f}%.")
                
                if len(fedfunds_data) > 1:
                    first = fedfunds_data[0]
                    first_val = DataFormatter.parse_numeric(first.get("value"))
                    if first_val is not None and latest_val is not None:
                        change = latest_val - first_val
                        if abs(change) > 0.01:
                            trend = "down" if change < 0 else "up"
                            monetary_items.append(f"Rate moved {trend} {abs(change):.2f} percentage points during this period.")
        
        if "M2_MONEY_SUPPLY" in indicators and indicators["M2_MONEY_SUPPLY"].get("data"):
            m2_data = indicators["M2_MONEY_SUPPLY"]["data"][-1]
            m2_val = DataFormatter.parse_numeric(m2_data.get("value"))
            if m2_val is not None:
                monetary_items.append(f"M2 money supply was ${m2_val:,.1f} billion.")
        
        if monetary_items:
            sections.append("MONETARY POLICY:\n" + " ".join(monetary_items))
        
        # Economic Activity
        activity_items = []
        
        if "RETAIL_SALES" in indicators and indicators["RETAIL_SALES"].get("data"):
            retail_data = indicators["RETAIL_SALES"]["data"][-1]
            retail_val = DataFormatter.parse_numeric(retail_data.get("value"))
            if retail_val is not None:
                activity_items.append(f"Retail sales totaled ${retail_val:,.0f} million.")
        
        if "INDUSTRIAL_PROD" in indicators and indicators["INDUSTRIAL_PROD"].get("data"):
            ind_data = indicators["INDUSTRIAL_PROD"]["data"][-1]
            ind_val = DataFormatter.parse_numeric(ind_data.get("value"))
            if ind_val is not None:
                activity_items.append(f"Industrial production index was {ind_val:.2f}.")
        
        if activity_items:
            sections.append("ECONOMIC ACTIVITY:\n" + " ".join(activity_items))
        
        return "\n\n".join(sections) if sections else "No economic data available."


class MarketDataFormatter:
    """Formats market data (OHLC) for all instruments"""
    
    INSTRUMENT_NAMES = {
        "XAUUSD": "Gold (XAU/USD)",
        "USA500.IDX": "S&P 500",
        "VOL.IDX": "VIX (Volatility Index)",
        "DOLLAR.IDX": "US Dollar Index (DXY)"
    }
    
    @staticmethod
    def format(data: Dict[str, Any]) -> Optional[str]:
        """Convert market data to natural language"""
        if not data:
            return None
        
        # Extract unique instruments from market_data
        instruments = set()
        for key in data.keys():
            if "_OPEN" in key or "_CLOSE" in key:
                instrument = key.replace("_OPEN", "").replace("_HIGH", "").replace("_LOW", "").replace("_CLOSE", "")
                if not instrument.endswith("_30D"):
                    instruments.add(instrument)
        
        if not instruments:
            return None
        
        lines = []
        
        for instrument in sorted(instruments):
            try:
                open_p = DataFormatter.parse_numeric(data.get(f"{instrument}_OPEN"))
                high = DataFormatter.parse_numeric(data.get(f"{instrument}_HIGH"))
                low = DataFormatter.parse_numeric(data.get(f"{instrument}_LOW"))
                close = DataFormatter.parse_numeric(data.get(f"{instrument}_CLOSE"))
                
                if not all([open_p, high, low, close]):
                    continue
                
                change, pct_change = DataFormatter.calculate_change(open_p, close)
                if change is None or pct_change is None:
                    continue
                
                range_val = high - low
                
                # Determine direction
                if abs(change) < 0.01:
                    direction = "no change"
                    change_text = "flat"
                    pct_text = "0.00%"
                elif change > 0:
                    direction = "gain"
                    change_text = f"+{change:.2f}"
                    pct_text = f"+{pct_change:.2f}%"
                else:
                    direction = "loss"
                    change_text = f"{change:.2f}"
                    pct_text = f"{pct_change:.2f}%"
                
                instrument_name = MarketDataFormatter.INSTRUMENT_NAMES.get(instrument, instrument)
                
                if instrument == "XAUUSD":
                    text = f"{instrument_name}: Opened at ${open_p:,.2f}, high ${high:,.2f}, low ${low:,.2f}, closed at ${close:,.2f}. "
                else:
                    text = f"{instrument_name}: Opened at {open_p:,.2f}, high {high:,.2f}, low {low:,.2f}, closed at {close:,.2f}. "
                
                text += f"Daily {direction} of {change_text} ({pct_text}), range {range_val:.2f}."
                
                # Add 30-day range if available
                day_high = data.get(f"{instrument}_30D_HIGH")
                day_low = data.get(f"{instrument}_30D_LOW")
                if day_high is not None and day_low is not None:
                    text += f" 30-day range: {day_low:,.2f} - {day_high:,.2f}."
                
                lines.append(text)
            except Exception:
                continue
        
        return "\n".join(lines) if lines else None


class TechnicalsFormatter:
    """Formats technical indicators for all instruments"""
    
    INSTRUMENT_NAMES = {
        "XAUUSD": "Gold (XAU/USD)",
        "USA500.IDX": "S&P 500",
        "VOL.IDX": "VIX",
        "DOLLAR.IDX": "Dollar Index (DXY)"
    }
    
    @staticmethod
    def format(data: Dict[str, Any]) -> Optional[str]:
        """Convert technicals to natural language"""
        if not data:
            return None
        
        # Extract unique instruments
        instruments = set()
        for key in data.keys():
            if "_RSI" in key:
                instrument = key.replace("_RSI", "").replace("_RSI_STATUS", "")
                instruments.add(instrument)
        
        if not instruments:
            return None
        
        lines = []
        
        for instrument in sorted(instruments):
            try:
                rsi = DataFormatter.parse_numeric(data.get(f"{instrument}_RSI"))
                rsi_status = data.get(f"{instrument}_RSI_STATUS")
                ema50 = DataFormatter.parse_numeric(data.get(f"{instrument}_EMA50"))
                ema200 = DataFormatter.parse_numeric(data.get(f"{instrument}_EMA200"))
                ema_trend = data.get(f"{instrument}_EMA_TREND")
                macd = DataFormatter.parse_numeric(data.get(f"{instrument}_MACD"))
                macd_signal = DataFormatter.parse_numeric(data.get(f"{instrument}_MACD_SIGNAL"))
                macd_hist = DataFormatter.parse_numeric(data.get(f"{instrument}_MACD_HIST"))
                stoch_k = DataFormatter.parse_numeric(data.get(f"{instrument}_STOCH_K"))
                stoch_d = DataFormatter.parse_numeric(data.get(f"{instrument}_STOCH_D"))
                stoch_status = data.get(f"{instrument}_STOCH_STATUS")
                
                parts = []
                instrument_name = TechnicalsFormatter.INSTRUMENT_NAMES.get(instrument, instrument)
                
                # RSI
                if rsi is not None:
                    rsi_text = f"RSI: {rsi:.2f}"
                    if rsi_status:
                        rsi_text += f" ({rsi_status.lower()})"
                    parts.append(rsi_text)
                
                # EMA Trend
                if ema_trend:
                    ema_text = f"EMA trend: {ema_trend.lower()}"
                    if ema50 is not None and ema200 is not None:
                        ema_text += f" (EMA50: {ema50:.2f}, EMA200: {ema200:.2f})"
                    parts.append(ema_text)
                
                # MACD
                if macd is not None:
                    macd_text = f"MACD: {macd:.2f}"
                    if macd_signal is not None:
                        macd_text += f", signal: {macd_signal:.2f}"
                    if macd_hist is not None:
                        hist_dir = "positive" if macd_hist > 0 else "negative"
                        macd_text += f", histogram: {macd_hist:.2f} ({hist_dir})"
                    parts.append(macd_text)
                
                # Stochastic
                if stoch_d is not None:
                    stoch_text = f"Stochastic: {stoch_d:.2f}"
                    if stoch_status:
                        stoch_text += f" ({stoch_status.lower()})"
                    parts.append(stoch_text)
                
                if parts:
                    lines.append(f"{instrument_name}: {'. '.join(parts)}.")
            except Exception:
                continue
        
        return "\n".join(lines) if lines else None


class EconomicEventsFormatter:
    """Formats economic events data"""
    
    @staticmethod
    def format(events: List[Dict[str, Any]]) -> Optional[str]:
        """Convert economic events to natural language"""
        if not events:
            return None
        
        lines = []
        for event in events:
            try:
                time = event.get("time", "Unknown time")
                currency = event.get("currency", "")
                event_name = event.get("event", "Unknown event")
                actual = event.get("actual", "")
                forecast = event.get("forecast", "")
                previous = event.get("previous", "")
                
                text = f"At {time}, {currency} {event_name} was released."
                
                if actual:
                    text += f" Actual: {actual}"
                    
                    if forecast and actual != forecast:
                        actual_num = DataFormatter.parse_numeric(actual)
                        forecast_num = DataFormatter.parse_numeric(forecast)
                        
                        if actual_num is not None and forecast_num is not None:
                            if actual_num > forecast_num:
                                text += f", beating forecast of {forecast}"
                            elif actual_num < forecast_num:
                                text += f", missing forecast of {forecast}"
                        else:
                            text += f" (forecast: {forecast})"
                    elif forecast:
                        text += f", matching forecast of {forecast}"
                    
                    if previous and actual != previous:
                        actual_num = DataFormatter.parse_numeric(actual)
                        previous_num = DataFormatter.parse_numeric(previous)
                        
                        if actual_num is not None and previous_num is not None:
                            change = actual_num - previous_num
                            if abs(change) > 0.01:
                                direction = "rising" if change > 0 else "falling"
                                text += f" and {direction} from previous {previous}."
                            else:
                                text += f", unchanged from previous {previous}."
                        else:
                            text += f" (previous: {previous})."
                    elif not forecast:
                        text += "."
                
                lines.append(text)
            except Exception:
                continue
        
        return "\n".join(lines) if lines else None


class FundamentalsFormatter:
    """Formats fundamental data"""
    
    @staticmethod
    def format(data: Dict[str, Any]) -> Optional[str]:
        """Convert fundamentals data to natural language"""
        if not data:
            return None
        
        lines = []
        
        if "TREASURY_10Y" in data:
            val = DataFormatter.parse_numeric(data["TREASURY_10Y"])
            if val is not None:
                lines.append(f"10-Year Treasury yield: {val:.2f}%.")
        
        if "HY_CREDIT_SPREAD" in data:
            val = DataFormatter.parse_numeric(data["HY_CREDIT_SPREAD"])
            if val is not None:
                lines.append(f"High-yield credit spread: {val:.2f}%.")
        
        if "JOBLESS_CLAIMS" in data:
            val = DataFormatter.parse_numeric(data["JOBLESS_CLAIMS"])
            if val is not None:
                lines.append(f"Initial jobless claims: {val:,.0f}K.")
        
        if "REAL_RATE" in data:
            val = DataFormatter.parse_numeric(data["REAL_RATE"])
            if val is not None:
                lines.append(f"Real interest rate: {val:.2f}%.")
        
        # Gold ETFs
        gld_parts = []
        if "GLD_CLOSE" in data:
            val = DataFormatter.parse_numeric(data["GLD_CLOSE"])
            if val is not None:
                gld_parts.append(f"closed at ${val:.2f}")
        
        if "GLD_VOLUME" in data:
            val = DataFormatter.parse_numeric(data["GLD_VOLUME"])
            if val is not None:
                gld_parts.append(f"volume {val:,.0f}")
        
        if gld_parts:
            lines.append(f"GLD ETF: {', '.join(gld_parts)}.")
        
        iau_parts = []
        if "IAU_CLOSE" in data:
            val = DataFormatter.parse_numeric(data["IAU_CLOSE"])
            if val is not None:
                iau_parts.append(f"closed at ${val:.2f}")
        
        if "IAU_VOLUME" in data:
            val = DataFormatter.parse_numeric(data["IAU_VOLUME"])
            if val is not None:
                iau_parts.append(f"volume {val:,.0f}")
        
        if iau_parts:
            lines.append(f"IAU ETF: {', '.join(iau_parts)}.")
        
        return " ".join(lines) if lines else None


class NewsFormatter:
    """Formats news articles"""
    
    @staticmethod
    def format(articles: List[Dict[str, Any]]) -> Optional[str]:
        """Convert news articles to natural language"""
        if not articles:
            return None
        
        by_category = {}
        for article in articles:
            category = article.get("category", "general")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(article)
        
        lines = []
        total_count = 0
        
        for category in sorted(by_category.keys()):
            items = by_category[category]
            lines.append(f"\n{category.upper()} ({len(items)} items):")
            
            for item in items:
                title = item.get("title", "").strip()
                ticker = item.get("ticker", "").strip()
                
                if title:
                    ticker_text = f" [{ticker}]" if ticker else ""
                    lines.append(f"  • {title}{ticker_text}")
                    total_count += 1
        
        if lines:
            lines.append(f"\n[Total: {total_count} news items]")
            return "\n".join(lines)
        
        return None


class RedditFormatter:
    """Formats Reddit posts"""
    
    @staticmethod
    def format(posts: List[Dict[str, Any]]) -> Optional[str]:
        """Convert reddit posts to natural language"""
        if not posts:
            return None
        
        by_subreddit = {}
        for post in posts:
            source = post.get("source", "unknown")
            if source not in by_subreddit:
                by_subreddit[source] = []
            by_subreddit[source].append(post)
        
        lines = []
        total_count = 0
        
        for subreddit in sorted(by_subreddit.keys()):
            items = by_subreddit[subreddit]
            lines.append(f"\n{subreddit} ({len(items)} posts):")
            
            for post in items:
                title = post.get("title", "").strip()
                if title:
                    lines.append(f"  • {title}")
                    total_count += 1
        
        if lines:
            lines.append(f"\n[Total: {total_count} posts tracked]")
            return "\n".join(lines)
        
        return None


class SnapshotConverter:
    """Main converter class"""
    
    @staticmethod
    def convert_to_text(snapshot_data: Dict[str, Any], is_inflation_file: bool = False) -> str:
        """Convert entire snapshot to natural language summary"""
        
        if is_inflation_file:
            generated_at = snapshot_data.get("generated_at", "")
            
            try:
                gen_date = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                date_header = gen_date.strftime("%B %d, %Y")
            except:
                date_header = "Monthly Indicators"
            
            sections = []
            sections.append(date_header)
            sections.append("")
            
            formatted = InflationDataFormatter.format(snapshot_data)
            if formatted:
                sections.append(formatted)
            else:
                sections.append("No economic data available.")
            
            sections.append("")
            sections.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            return "\n".join(sections)
        
        # Standard daily snapshot handling
        date = snapshot_data.get("date", "Unknown Date")
        data = snapshot_data.get("data", {})
        
        try:
            date_obj = datetime.fromisoformat(date)
            date_header = date_obj.strftime("%B %d, %Y")
        except:
            date_header = date
        
        sections = []
        sections.append(date_header)
        sections.append("")
        
        # Process each category with new structure
        formatters = [
            ("market_data", "MARKET DATA", MarketDataFormatter.format),
            ("technicals", "TECHNICAL INDICATORS", TechnicalsFormatter.format),
            ("economic_events", "ECONOMIC EVENTS", EconomicEventsFormatter.format),
            ("fundamentals", "FUNDAMENTALS", FundamentalsFormatter.format),
            ("news", "NEWS HIGHLIGHTS", NewsFormatter.format),
            ("reddit", "SOCIAL SENTIMENT", RedditFormatter.format),
        ]
        
        for key, title, formatter in formatters:
            if key in data and data[key]:
                try:
                    formatted = formatter(data[key])
                    if formatted:
                        sections.append(f"{title}:")
                        sections.append(formatted)
                        sections.append("")
                except Exception as e:
                    sections.append(f"{title}: [Error processing data: {str(e)}]")
                    sections.append("")
        
        sections.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return "\n".join(sections)


def main():
    print("\n" + "="*70)
    print("ENHANCED DAILY SNAPSHOT TO NATURAL LANGUAGE CONVERTER")
    print("="*70 + "\n")
    
    input_path = Path(INPUT_FOLDER)
    if not input_path.exists():
        print(f"ERROR: {INPUT_FOLDER} folder not found")
        return
    
    output_path = Path(OUTPUT_FOLDER)
    output_path.mkdir(exist_ok=True)
    
    inflation_file = input_path / "inflation_data.json"
    snapshot_files = []
    
    if inflation_file.exists():
        snapshot_files.append(inflation_file)
        print("Found inflation_data.json - processing as monthly overview\n")
    
    daily_files = sorted(input_path.glob("snapshot_*.json"))
    snapshot_files.extend(daily_files)
    
    if not snapshot_files:
        print(f"ERROR: No snapshot files found in {INPUT_FOLDER}")
        return
    
    print(f"Found {len(snapshot_files)} files to process\n")
    
    converted_count = 0
    error_count = 0
    
    for snapshot_file in snapshot_files:
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot_data = json.load(f)
            
            is_inflation = snapshot_file.name == "inflation_data.json"
            
            text_summary = SnapshotConverter.convert_to_text(snapshot_data, is_inflation_file=is_inflation)
            
            if is_inflation:
                output_file = output_path / "summary_monthly_indicators.txt"
            else:
                date = snapshot_data.get("date", "unknown")
                output_file = output_path / f"summary_{date}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text_summary)
            
            converted_count += 1
            print(f"✓ {output_file.name}")
            
        except Exception as e:
            error_count += 1
            print(f"✗ Error processing {snapshot_file.name}: {str(e)}")
    
    print("\n" + "="*70)
    print(f"Successfully converted: {converted_count}")
    print(f"Errors encountered: {error_count}")
    print(f"Output folder: {OUTPUT_FOLDER}/")
    print("="*70)
    print("FINISHED\n")


if __name__ == "__main__":
    main()