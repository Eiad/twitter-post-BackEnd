from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import requests
import os
from datetime import datetime
import json

class TweetScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.access_token = None
        self.last_tweet_time = None

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
        return self.scheduler.running if hasattr(self, 'scheduler') else False

    def post_scheduled_tweet(self):
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
                json={"text": "Tweetaaa from the API"},
                headers=headers
            )
            if response.status_code == 201:
                self.last_tweet_time = datetime.now().isoformat()
                print("Tweet posted successfully")
                return True
            else:
                print(f"Error posting tweet: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error posting scheduled tweet: {str(e)}")
            return False

    def start(self):
        try:
            if not self.scheduler.running:
                self.scheduler.add_job(
                    self.post_scheduled_tweet,
                    'interval',
                    seconds=10,  # Changed from minutes=30 to seconds=10
                    id='tweet_job'
                )
                self.scheduler.start()
                return True
        except Exception as e:
            print(f"Error starting scheduler: {str(e)}")
            return False

    def stop(self):
        try:
            if self.scheduler.running:
                self.scheduler.remove_job('tweet_job')
                self.scheduler.shutdown()
                return True
        except Exception as e:
            print(f"Error stopping scheduler: {str(e)}")
            return False
