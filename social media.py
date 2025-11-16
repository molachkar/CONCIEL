import json
import re
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from collections import defaultdict
import hashlib

from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

try:
    nltk.data.find('vader_lexicon')
except:
    nltk.download('vader_lexicon', quiet=True)

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "Gold", "economy", "StockMarket"]

class RedditSentimentLayer:
    def __init__(self):
        self.sia = SentimentIntensityAnalyzer()
        self.seen_hashes = {}
        self.output_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)
    
    def fetch_reddit(self, subreddits, limit=50):
        posts = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
                req = Request(url, headers=headers)
                response = urlopen(req, timeout=15)
                data = json.loads(response.read().decode())
                
                for child in data['data']['children']:
                    post = child['data']
                    
                    posts.append({
                        'title': post.get('title', ''),
                        'timestamp': datetime.fromtimestamp(post['created_utc']).isoformat(),
                        'score': post.get('score', 0),
                        'num_comments': post.get('num_comments', 0),
                        'subreddit': subreddit
                    })
                
                print(f"  r/{subreddit}: {len(data['data']['children'])} posts")
                time.sleep(random.uniform(2, 3))
                
            except Exception as e:
                print(f"  r/{subreddit}: Error - {str(e)}")
        
        return posts
    
    def clean_text(self, text):
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+', '', text)
        return ' '.join(text.split()).strip()
    
    def filter_posts(self, posts):
        filtered = []
        
        for post in posts:
            if post['score'] < 5:
                continue
            
            title = self.clean_text(post['title'])
            
            if len(title) < 15 or len(title) > 2000:
                continue
            
            text_hash = hashlib.md5(title.encode()).hexdigest()
            if text_hash in self.seen_hashes:
                time_diff = (datetime.fromisoformat(post['timestamp']) - 
                           datetime.fromisoformat(self.seen_hashes[text_hash])).days
                if time_diff < 3:
                    continue
            
            self.seen_hashes[text_hash] = post['timestamp']
            
            post['cleaned_title'] = title
            filtered.append(post)
        
        return filtered
    
    def analyze_sentiment(self, posts):
        for post in posts:
            score = self.sia.polarity_scores(post['cleaned_title'])
            post['sentiment_score'] = round(score['compound'], 4)
        return posts
    
    def calculate_fear_greed(self, sentiments):
        if not sentiments:
            return {"fear": 50, "greed": 50}
        
        avg = sum(sentiments) / len(sentiments)
        greed_pct = int(((avg + 1) / 2) * 100)
        fear_pct = 100 - greed_pct
        
        return {"fear": fear_pct, "greed": greed_pct}
    
    def filter_timeframe(self, posts, hours=None, days=None):
        now = datetime.now()
        
        if hours:
            cutoff = now - timedelta(hours=hours)
            return [p for p in posts if datetime.fromisoformat(p['timestamp']) >= cutoff]
        elif days:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff = today_start - timedelta(days=days)
            return [p for p in posts if cutoff <= datetime.fromisoformat(p['timestamp']) < today_start]
        
        return posts
    
    def run(self):
        print("="*60)
        print("Reddit Sentiment Layer - Minimal")
        print("="*60)
        
        print("\nFetching Reddit posts...")
        raw_posts = self.fetch_reddit(SUBREDDITS, limit=50)
        print(f"Total fetched: {len(raw_posts)}")
        
        print("\nFiltering...")
        filtered = self.filter_posts(raw_posts)
        print(f"After filtering: {len(filtered)}")
        
        print("\nAnalyzing sentiment...")
        analyzed = self.analyze_sentiment(filtered)
        
        timeframes = {
            "30D": self.filter_timeframe(analyzed, days=30),
            "7D": self.filter_timeframe(analyzed, days=7),
            "24H": self.filter_timeframe(analyzed, hours=24)
        }
        
        output = {}
        
        for tf_name, tf_posts in timeframes.items():
            tf_posts.sort(key=lambda x: x['timestamp'])
            
            sentiments = [p['sentiment_score'] for p in tf_posts]
            fear_greed = self.calculate_fear_greed(sentiments)
            
            clean_posts = []
            for p in tf_posts:
                clean_posts.append({
                    'title': p['cleaned_title'],
                    'time': p['timestamp']
                })
            
            output[tf_name] = {
                'timeframe': tf_name,
                'total_posts': len(tf_posts),
                'fear_greed_index': fear_greed,
                'posts': clean_posts
            }
            
            print(f"{tf_name}: {len(tf_posts)} posts, Fear: {fear_greed['fear']}% / Greed: {fear_greed['greed']}%")
        
        final_output = {
            'fetch_time': datetime.now().isoformat(),
            'total_posts_fetched': len(raw_posts),
            'total_posts_after_filter': len(filtered),
            'source': 'reddit',
            'subreddits': SUBREDDITS,
            **output
        }
        
        out_path = self.output_dir / "reddit_sentiment.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"Saved to {out_path}")
        print("="*60)
        
        return final_output

if __name__ == "__main__":
    layer = RedditSentimentLayer()
    result = layer.run()
    
    total = sum(result[tf]['total_posts'] for tf in ['30D', '7D', '24H'])
    print(f"\n✓ Total posts: {total}")