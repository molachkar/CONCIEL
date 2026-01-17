import json
import re
import time
import random
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
import hashlib

SUBREDDITS = ["economics", "geopolitics", "worldnews"]

MIN_SCORE = 50
MIN_COMMENTS = 10

class RedditNewsFetcher:
    def __init__(self):
        self.seen_hashes = set()
    
    def fetch_reddit(self, subreddits, limit=100):
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
                        'timestamp': datetime.fromtimestamp(post['created_utc']),
                        'score': post.get('score', 0),
                        'num_comments': post.get('num_comments', 0),
                        'subreddit': subreddit
                    })
                
                print(f"r/{subreddit}: {len(data['data']['children'])} posts")
                time.sleep(random.uniform(2, 3))
                
            except Exception as e:
                print(f"r/{subreddit}: Error - {str(e)}")
        
        return posts
    
    def clean_text(self, text):
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+', '', text)
        return ' '.join(text.split()).strip()
    
    def filter_posts(self, posts):
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        filtered = []
        
        for post in posts:
            if post['timestamp'] < thirty_days_ago:
                continue
            
            if post['score'] < MIN_SCORE or post['num_comments'] < MIN_COMMENTS:
                continue
            
            title = self.clean_text(post['title'])
            
            if len(title) < 20:
                continue
            
            text_hash = hashlib.md5(title.encode()).hexdigest()
            if text_hash in self.seen_hashes:
                continue
            
            self.seen_hashes.add(text_hash)
            
            filtered.append({
                'time': post['timestamp'].isoformat(),
                'title': title,
                'source': f"r/{post['subreddit']}"
            })
        
        return filtered
    
    def run(self):
        print("Reddit News Fetcher - 30 Days")
        print()
        
        print("Fetching Reddit posts...")
        raw_posts = self.fetch_reddit(SUBREDDITS, limit=100)
        print(f"Total fetched: {len(raw_posts)}")
        print()
        
        print("Filtering posts...")
        filtered = self.filter_posts(raw_posts)
        filtered.sort(key=lambda x: x['time'], reverse=True)
        
        print(f"After filtering: {len(filtered)}")
        print()
        
        output = {
            'fetch_time': datetime.now().isoformat(),
            'total_fetched': len(raw_posts),
            'total_filtered': len(filtered),
            'posts': filtered
        }
        
        with open("Fetchers/jsons/reddit_news.json", 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Saved to reddit_news.json")
        print(f"Total posts saved: {len(filtered)}")
        
        return output

if __name__ == "__main__":
    fetcher = RedditNewsFetcher()
    result = fetcher.run()