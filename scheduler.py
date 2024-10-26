from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import requests
import os
from datetime import datetime, timedelta
import json

class TweetScheduler:
    def __init__(self):
        self.scheduler = None
        self.access_token = None
        self.last_tweet_time = None
        self.tweet_queue = []

    def load_token(self):
        try:
            with open('token_store.json', 'r') as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
        except FileNotFoundError:
            self.access_token = None

    def save_token(self, token):
        self.access_token = token
        print(f"Saved access token: {token[:10]}...")  # Log first 10 chars for debugging

    def is_running(self):
        return self.scheduler is not None and self.scheduler.running and len(self.tweet_queue) > 0

    def schedule_tweets(self, tweets, interval):
        self.tweet_queue = tweets
        self.create_scheduler()
        
        interval_seconds = (
            interval['days'] * 86400 +
            interval['hours'] * 3600 +
            interval['minutes'] * 60 +
            interval['seconds']
        )
        
        start_time = datetime.now() + timedelta(minutes=1)  # Start in 1 minute
        for i, tweet in enumerate(tweets):
            scheduled_time = start_time + timedelta(seconds=i*interval_seconds)
            self.scheduler.add_job(
                self.post_scheduled_tweet,
                'date',
                run_date=scheduled_time,
                args=[tweet['content']],
                id=f'tweet_job_{i}'
            )
        
        self.scheduler.start()

    def post_scheduled_tweet(self, tweet_content):
        if not self.access_token:
            print("No access token available")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                "https://api.twitter.com/2/tweets",
                json={"text": tweet_content},
                headers=headers
            )
            if response.status_code == 201:
                self.last_tweet_time = datetime.now().isoformat()
                print(f"Tweet posted successfully: {tweet_content[:50]}...")
                self.tweet_queue.pop(0)  # Remove the posted tweet from the queue
                if not self.tweet_queue:
                    self.stop()  # Stop the scheduler if there are no more tweets
                return True
            else:
                print(f"Error posting tweet: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error posting scheduled tweet: {str(e)}")
            return False

    def create_scheduler(self):
        if self.scheduler is not None:
            try:
                self.scheduler.shutdown(wait=False)
            except:
                pass
        self.scheduler = BackgroundScheduler()

    def stop(self):
        try:
            if self.scheduler:
                self.scheduler.remove_all_jobs()
                self.scheduler.shutdown(wait=False)
                self.scheduler = None
            self.tweet_queue = []
            self.last_tweet_time = None
            return True
        except Exception as e:
            print(f"Error stopping scheduler: {str(e)}")
            return False

    def get_remaining_tweets_count(self):
        return len(self.tweet_queue)
