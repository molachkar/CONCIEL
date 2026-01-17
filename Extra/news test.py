import feedparser
from datetime import datetime, timedelta
import json

def fetch_wgc():
    print("World Gold Council Fetcher - Last 30 Days")
    print()
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    articles = []
    
    # Fetch RSS feed
    feed = feedparser.parse("https://www.gold.org/rss.xml")
    
    print(f"Total entries in feed: {len(feed.entries)}")
    
    for entry in feed.entries:
        pub_date_str = entry.get("published", "")
        
        if not pub_date_str:
            continue
        
        # Parse date
        try:
            article_date = datetime.strptime(pub_date_str.strip(), "%a, %d %b %Y %H:%M:%S %z")
            if article_date.tzinfo:
                article_date = article_date.replace(tzinfo=None)
            
            if article_date >= thirty_days_ago:
                articles.append({
                    "source": "World Gold Council",
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published": pub_date_str,
                    "description": entry.get("summary", ""),
                    "category": "Gold Research",
                    "relevance_score": 100
                })
        except:
            continue
    
    print(f"Articles within 30 days: {len(articles)}")
    
    # Save to working directory
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(articles),
        "articles": articles
    }
    
    with open("gold_news.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to gold_news.json")

if __name__ == "__main__":
    fetch_wgc()