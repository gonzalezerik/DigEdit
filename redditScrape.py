import os
import json
import time
import logging
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()

class Config:
    TARGET_URL = os.getenv("TARGET_URL")
    REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", "2"))
    OUTPUT_FILE = os.getenv("OUTPUT_FILE", "reddit_data.json")

    @classmethod
    def validate(cls):
        if not cls.TARGET_URL:
            raise ValueError("Missing required environment variable: TARGET_URL")

class RedditScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'python:reddit_to_neo4j:v1.0 (by /u/your_username)'
        })

    def _get_url(self, url: str, params: Dict = None) -> Dict:
        try:
            time.sleep(Config.REQUEST_DELAY)
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            if response.status_code == 429:
                logger.warning("Rate limited! Waiting longer...")
                time.sleep(60)
                raise Exception("Rate limited by Reddit")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def _extract_comments_recursive(self, comments: List, parent_id: str = None) -> List:
        extracted = []
        for item in comments:
            if item.get('kind') == 't1':  # Comment
                comment_data = {
                    "id": f"t1_{item['data']['id']}",  # Normalize ID
                    "text": item['data']['body'],
                    "score": item['data']['score'],
                    "created_utc": item['data']['created_utc'],
                    "author": item['data']['author'] if item['data']['author'] else "[deleted]",
                    "parent_id": item['data']['parent_id'], # API returns t3_xxx or t1_xxx
                    "permalink": item['data']['permalink']
                }
                extracted.append(comment_data)

                if item['data'].get('replies'):
                    if isinstance(item['data']['replies'], dict):
                        extracted.extend(self._extract_comments_recursive(
                            item['data']['replies']['data']['children'],
                            comment_data['id']
                        ))
            elif item.get('kind') == 'more':
                logger.info(f"Skipping MoreComments placeholder for {item['data']['id']}")
        return extracted

    def fetch_submission_data(self, url: str) -> Dict[str, Any]:
        logger.info(f"Scraping Reddit thread: {url}")
        url = url.split('?')[0]
        if url.endswith('/'): url = url[:-1]
        json_url = f"{url}.json"

        try:
            data = self._get_url(json_url)
            if not isinstance(data, list) or len(data) < 2:
                raise ValueError(f"Unexpected JSON structure: {data}")

            submission = data[0]['data']['children'][0]['data']
            comments_data = data[1]['data']['children']

            # Normalize Post ID to match parent_id format (t3_xxx)
            post_id = f"t3_{submission['id']}"

            post_data = {
                "id": post_id,
                "title": submission['title'],
                "text": submission.get('selftext', '') or '',
                "score": submission['score'],
                "url": submission['url'],
                "created_utc": submission['created_utc'],
                "author": submission['author'] if submission['author'] else "[deleted]",
                "subreddit_name": submission['subreddit']
            }

            comments = []
            for comment in comments_data:
                if comment.get('kind') == 't1':
                    # Normalize Comment ID to match parent_id format (t1_xxx)
                    comment_id = f"t1_{comment['data']['id']}"
                    
                    comment_entry = {
                        "id": comment_id,
                        "text": comment['data']['body'],
                        "score": comment['data']['score'],
                        "created_utc": comment['data']['created_utc'],
                        "author": comment['data']['author'] if comment['data']['author'] else "[deleted]",
                        "parent_id": comment['data']['parent_id'], # Already has prefix
                        "permalink": comment['data']['permalink']
                    }
                    comments.append(comment_entry)

                    if comment['data'].get('replies'):
                        if isinstance(comment['data']['replies'], dict):
                            replies = self._extract_comments_recursive(
                                comment['data']['replies']['data']['children'],
                                comment_id
                            )
                            comments.extend(replies)

            return {
                "post": post_data,
                "comments": comments
            }
        except Exception as e:
            logger.error(f"Failed to scrape submission: {e}")
            raise

def main():
    Config.validate()
    scraper = RedditScraper()
    
    try:
        reddit_data = scraper.fetch_submission_data(Config.TARGET_URL)
        
        # Export to JSON file
        with open(Config.OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(reddit_data, f, indent=2)
        
        logger.info(f"Data successfully exported to {Config.OUTPUT_FILE}")
    except Exception as e:
        logger.critical(f"Fatal Error: {e}")
        raise

if __name__ == "__main__":
    main()
