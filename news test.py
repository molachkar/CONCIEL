import requests
import feedparser
from datetime import datetime
import json
import time
import re

class GoldNewsAggregator:
    
    def __init__(self, newsapi_key, finnhub_key, alphavantage_key, gnews_key):
        self.newsapi_key = newsapi_key
        self.finnhub_key = finnhub_key
        self.alphavantage_key = alphavantage_key
        self.gnews_key = gnews_key
        self.all_news = []
        
        # Gold-specific keywords for better filtering
        self.gold_keywords = [
            'gold', 'bullion', 'precious metal', 'gold price', 
            'gold mining', 'gold market', 'gold investment', 
            'gold reserve', 'gold demand', 'gold supply',
            'XAU', 'troy ounce', 'gold futures', 'LBMA',
            'gold ETF', 'gold bar', 'gold coin'
        ]
    
    def is_gold_relevant(self, title, description):
        """Score content relevance to gold (0-100)"""
        text = f"{title} {description}".lower()
        
        # Direct gold mentions (high score)
        if 'gold' in text:
            score = 80
            
            # Boost for specific gold terms
            if any(term in text for term in ['gold price', 'gold market', 'gold mining', 'precious metal']):
                score += 15
            
            # Penalize if it's just passing mention
            if text.count('gold') == 1 and len(text) > 300:
                score -= 20
                
            return score
        
        # Related precious metals (medium score)
        if any(term in text for term in ['silver', 'platinum', 'palladium', 'precious metal']):
            return 40
        
        # Mining or commodities (low score)
        if any(term in text for term in ['mining', 'commodity', 'metal']):
            return 20
            
        return 0
    
    def fetch_newsapi(self):
        """Fetch gold-specific news from NewsAPI"""
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "apiKey": self.newsapi_key,
                "q": '"gold price" OR "gold market" OR "gold mining" OR "gold bullion"',
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 30  # Get more to filter
            }
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            added = 0
            if data.get("status") == "ok":
                for article in data.get("articles", []):
                    title = article.get("title", "")
                    desc = article.get("description", "")
                    
                    # Only add if gold-relevant
                    relevance = self.is_gold_relevant(title, desc)
                    if relevance >= 60:  # High threshold
                        self.all_news.append({
                            "source": "NewsAPI",
                            "title": title,
                            "url": article.get("url"),
                            "published": article.get("publishedAt"),
                            "description": desc,
                            "category": "Gold News",
                            "relevance_score": relevance
                        })
                        added += 1
            
            print(f"✓ NewsAPI: {added} gold articles (filtered from {len(data.get('articles', []))})")
        except Exception as e:
            print(f"✗ NewsAPI failed: {e}")
    
    def fetch_kitco_alternative(self):
        """Fetch Kitco news via their actual working endpoints"""
        try:
            # Try their news API endpoint
            urls_to_try = [
                "https://www.kitco.com/feed/KitcoNews.xml",
                "https://www.kitco.com/commentaries/rss/latest.xml",
            ]
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, timeout=15, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    
                    if response.status_code == 200:
                        feed = feedparser.parse(response.content)
                        
                        if feed.entries:
                            added = 0
                            for entry in feed.entries[:15]:
                                self.all_news.append({
                                    "source": "Kitco News",
                                    "title": entry.get("title", ""),
                                    "url": entry.get("link", ""),
                                    "published": entry.get("published", datetime.now().isoformat()),
                                    "description": entry.get("summary", ""),
                                    "category": "Gold Market",
                                    "relevance_score": 95  # Kitco is gold-focused
                                })
                                added += 1
                            
                            print(f"✓ Kitco News: {added} articles")
                            return
                except:
                    continue
            
            print("✗ Kitco: All endpoints failed")
            
        except Exception as e:
            print(f"✗ Kitco failed: {e}")
    
    def fetch_goldprice_org(self):
        """GoldPrice.org news - very gold-specific"""
        try:
            feed = feedparser.parse("https://goldprice.org/rss/full-feeds/news.xml")
            
            added = 0
            for entry in feed.entries[:10]:
                self.all_news.append({
                    "source": "GoldPrice.org",
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published": entry.get("published", datetime.now().isoformat()),
                    "description": entry.get("summary", ""),
                    "category": "Gold Price News",
                    "relevance_score": 100
                })
                added += 1
            
            print(f"✓ GoldPrice.org: {added} articles")
        except Exception as e:
            print(f"✗ GoldPrice.org failed: {e}")
    
    def fetch_mining_com_gold_only(self):
        """Fetch ONLY gold-related articles from Mining.com"""
        try:
            feed = feedparser.parse("https://www.mining.com/feed/")
            
            added = 0
            for entry in feed.entries[:30]:  # Check more entries
                title = entry.get("title", "")
                desc = entry.get("summary", "")
                
                # Only add if gold-relevant
                relevance = self.is_gold_relevant(title, desc)
                if relevance >= 50:
                    self.all_news.append({
                        "source": "Mining.com",
                        "title": title,
                        "url": entry.get("link"),
                        "published": entry.get("published", datetime.now().isoformat()),
                        "description": desc,
                        "category": "Gold Mining",
                        "relevance_score": relevance
                    })
                    added += 1
                    
                    if added >= 10:  # Limit to 10 gold articles
                        break
            
            print(f"✓ Mining.com: {added} gold articles")
        except Exception as e:
            print(f"✗ Mining.com failed: {e}")
    
    def fetch_bullion_vault(self):
        """BullionVault gold news"""
        try:
            feed = feedparser.parse("https://www.bullionvault.com/gold-news/rss")
            
            added = 0
            for entry in feed.entries[:10]:
                self.all_news.append({
                    "source": "BullionVault",
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published": entry.get("published", datetime.now().isoformat()),
                    "description": entry.get("summary", ""),
                    "category": "Gold Investment",
                    "relevance_score": 95
                })
                added += 1
            
            print(f"✓ BullionVault: {added} articles")
        except Exception as e:
            print(f"✗ BullionVault failed: {e}")
    
    def fetch_gold_eagle(self):
        """Gold Eagle news - gold-focused commentary"""
        try:
            feed = feedparser.parse("https://www.gold-eagle.com/rss/dailynews.xml")
            
            added = 0
            for entry in feed.entries[:10]:
                self.all_news.append({
                    "source": "Gold Eagle",
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published": entry.get("published", datetime.now().isoformat()),
                    "description": entry.get("summary", ""),
                    "category": "Gold Analysis",
                    "relevance_score": 90
                })
                added += 1
            
            print(f"✓ Gold Eagle: {added} articles")
        except Exception as e:
            print(f"✗ Gold Eagle failed: {e}")
    
    def fetch_cme_metals_fixed(self):
        """CME Group Metals News - with better error handling"""
        urls_to_try = [
            "https://www.cmegroup.com/feeds/market-news-metals.rss",
            "https://www.cmegroup.com/rss/market-news-metals.xml",
            "https://www.cmegroup.com/feeds/articles-markets-metals.rss"
        ]
        
        for url in urls_to_try:
            try:
                # Use shorter timeout and custom headers
                response = requests.get(
                    url, 
                    timeout=10,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/rss+xml, application/xml, text/xml'
                    }
                )
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    
                    if feed.entries:
                        added = 0
                        for entry in feed.entries[:5]:
                            self.all_news.append({
                                "source": "CME Metals",
                                "title": entry.get("title"),
                                "url": entry.get("link"),
                                "published": entry.get("published", datetime.now().isoformat()),
                                "description": entry.get("summary", ""),
                                "category": "Gold Futures",
                                "relevance_score": 85
                            })
                            added += 1
                        
                        print(f"✓ CME Metals: {added} articles")
                        return
            except requests.Timeout:
                continue
            except Exception:
                continue
        
        print(f"✗ CME Metals: All URLs failed or timed out (not critical)")
    
    def fetch_gnews_gold_specific(self):
        """Fetch gold-specific news from GNews"""
        try:
            url = "https://gnews.io/api/v4/search"
            params = {
                "apikey": self.gnews_key,
                "q": '"gold price" OR "gold market"',  # More specific query
                "lang": "en",
                "max": 20
            }
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            added = 0
            for article in data.get("articles", []):
                title = article.get("title", "")
                desc = article.get("description", "")
                
                relevance = self.is_gold_relevant(title, desc)
                if relevance >= 60:
                    self.all_news.append({
                        "source": "GNews",
                        "title": title,
                        "url": article.get("url"),
                        "published": article.get("publishedAt"),
                        "description": desc,
                        "category": "Gold News",
                        "relevance_score": relevance
                    })
                    added += 1
            
            print(f"✓ GNews: {added} gold articles (filtered from {len(data.get('articles', []))})")
        except Exception as e:
            print(f"✗ GNews failed: {e}")
    
    def fetch_finnhub_gold(self):
        """Fetch gold-related market news from Finnhub"""
        try:
            url = f"https://finnhub.io/api/v1/news?category=forex&token={self.finnhub_key}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            added = 0
            for article in data[:30]:  # Check more articles
                title = article.get("headline", "")
                desc = article.get("summary", "")
                
                relevance = self.is_gold_relevant(title, desc)
                if relevance >= 50:  # Medium threshold for market news
                    self.all_news.append({
                        "source": "Finnhub",
                        "title": title,
                        "url": article.get("url"),
                        "published": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
                        "description": desc,
                        "category": "Gold Market",
                        "relevance_score": relevance
                    })
                    added += 1
                    
                    if added >= 5:  # Limit to 5 articles
                        break
            
            print(f"✓ Finnhub: {added} gold articles (filtered from 30)")
        except Exception as e:
            print(f"✗ Finnhub failed: {e}")
    
    def fetch_alphavantage_gold(self):
        """Fetch gold-related news from AlphaVantage"""
        try:
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics=economy_macro,finance&apikey={self.alphavantage_key}&limit=30"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            added = 0
            for article in data.get("feed", []):
                title = article.get("title", "")
                desc = article.get("summary", "")
                
                relevance = self.is_gold_relevant(title, desc)
                if relevance >= 50:  # Medium threshold
                    self.all_news.append({
                        "source": "AlphaVantage",
                        "title": title,
                        "url": article.get("url"),
                        "published": article.get("time_published"),
                        "description": desc,
                        "category": "Market News",
                        "relevance_score": relevance
                    })
                    added += 1
                    
                    if added >= 5:  # Limit to 5 articles
                        break
            
            print(f"✓ AlphaVantage: {added} gold articles (filtered from {len(data.get('feed', []))})")
        except Exception as e:
            print(f"✗ AlphaVantage failed: {e}")
    
    def fetch_world_gold_council(self):
        """World Gold Council - authoritative source"""
        try:
            feed = feedparser.parse("https://www.gold.org/rss.xml")
            
            added = 0
            for entry in feed.entries[:10]:
                self.all_news.append({
                    "source": "World Gold Council",
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published": entry.get("published", datetime.now().isoformat()),
                    "description": entry.get("summary", ""),
                    "category": "Gold Research",
                    "relevance_score": 100
                })
                added += 1
            
            print(f"✓ World Gold Council: {added} articles")
        except Exception as e:
            print(f"✗ World Gold Council failed: {e}")
    
    def remove_duplicates(self):
        """Remove duplicate articles, sort by relevance, and limit to top 20"""
        seen_urls = set()
        unique_news = []
        
        # Sort by relevance score first
        self.all_news.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        for article in self.all_news:
            url = article.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(article)
        
        # Limit to top 20 most relevant articles
        self.all_news = unique_news[:20]
    
    def save_to_json(self, filename="gold_news.json"):
        """Save with statistics"""
        # Calculate average relevance
        avg_relevance = sum(a.get("relevance_score", 0) for a in self.all_news) / len(self.all_news) if self.all_news else 0
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_articles": len(self.all_news),
            "max_articles": 20,
            "average_gold_relevance": round(avg_relevance, 1),
            "articles": self.all_news
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved TOP {len(self.all_news)} articles to {filename}")
        print(f"✓ Average gold relevance score: {avg_relevance:.1f}/100")
        
        # Show relevance distribution
        high_relevance = sum(1 for a in self.all_news if a.get("relevance_score", 0) >= 80)
        print(f"✓ High relevance (≥80): {high_relevance} articles")
    
    def fetch_all(self):
        print("=" * 60)
        print("Fetching GOLD-SPECIFIC news from multiple sources...")
        print("=" * 60)
        
        # Priority 1: Gold-specific sources
        print("\n🥇 TIER 1: Gold-Focused Sources")
        print("-" * 60)
        self.fetch_world_gold_council()
        time.sleep(1)
        
        self.fetch_kitco_alternative()
        time.sleep(1)
        
        self.fetch_goldprice_org()
        time.sleep(1)
        
        self.fetch_bullion_vault()
        time.sleep(1)
        
        self.fetch_gold_eagle()
        time.sleep(1)
        
        self.fetch_cme_metals_fixed()  # Fixed version
        time.sleep(1)
        
        # Priority 2: General sources with gold filtering
        print("\n🥈 TIER 2: Filtered General Sources")
        print("-" * 60)
        self.fetch_mining_com_gold_only()
        time.sleep(1)
        
        self.fetch_newsapi()
        time.sleep(1)
        
        self.fetch_gnews_gold_specific()
        time.sleep(1)
        
        # Priority 3: Market news sources (limited)
        print("\n🥉 TIER 3: Market News (Gold-Filtered)")
        print("-" * 60)
        self.fetch_finnhub_gold()
        time.sleep(1)
        
        self.fetch_alphavantage_gold()
        time.sleep(1)
        
        # Process results
        print("\n" + "=" * 60)
        print("PROCESSING RESULTS")
        print("=" * 60)
        
        self.remove_duplicates()
        self.save_to_json()
        
        # Summary by source
        print(f"\n📊 BREAKDOWN BY SOURCE:")
        source_counts = {}
        for article in self.all_news:
            source = article.get("source", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count} articles")


if __name__ == "__main__":
    # Your API keys
    NEWSAPI_KEY = "07d638496f4741849ce55d2c42320107"
    FINNHUB_KEY = "d2jh4u9r01qj8a5jboegd2jh4u9r01qj8a5jbof0"
    ALPHAVANTAGE_KEY = "RA4O6HFA0Z3SWC2B"
    GNEWS_KEY = "3ca29aea34716d7b94e513c9463ef5f1"
    
    aggregator = GoldNewsAggregator(
        newsapi_key=NEWSAPI_KEY,
        finnhub_key=FINNHUB_KEY,
        alphavantage_key=ALPHAVANTAGE_KEY,
        gnews_key=GNEWS_KEY
    )
    
    aggregator.fetch_all()