import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, make_response
from flask_cors import CORS
from scheduler import TweetScheduler
import json

# Load environment variables
load_dotenv()

# Twitter API credentials
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_CALLBACK_URL = os.getenv("TWITTER_CALLBACK_URL") 
FRONTEND_URL = os.getenv("FRONTEND_URL") 

# Create a Flask app
app = Flask(__name__)
CORS(app, 
    origins="http://localhost:3003",
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)
# Add this after creating the Flask app
tweet_scheduler = TweetScheduler()

# Route to start the OAuth 2.0 flow and redirect to Twitter
@app.route("/auth")
def auth():
    auth_url = f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id={TWITTER_CLIENT_ID}&redirect_uri={TWITTER_CALLBACK_URL}&scope=tweet.read%20tweet.write%20users.read&state=state&code_challenge=challenge&code_challenge_method=plain"
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    # Exchange code for access token
    response = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        data={
            "code": code,
            "grant_type": "authorization_code",
            "client_id": TWITTER_CLIENT_ID,
            "redirect_uri": TWITTER_CALLBACK_URL,
            "code_verifier": "challenge",
        },
        auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to get access token"}), 400

    access_token = response.json().get("access_token")
    tweet_scheduler.save_token(access_token)  # Save token in scheduler instance
    
    return redirect(f"{FRONTEND_URL}?access_token={access_token}")

@app.route("/tweet", methods=["POST"])
def post_tweet():
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
    
    tweet_text = request.json.get("tweet")
    if not tweet_text:
        return jsonify({"error": "No tweet text provided"}), 400

    headers = {
        "Authorization": access_token,
        "Content-Type": "application/json",
    }
    
    response = requests.post(
        "https://api.twitter.com/2/tweets",
        headers=headers,
        json={"text": tweet_text}
    )
    
    if response.status_code == 201:
        return jsonify({"message": "Tweet posted successfully"}), 201
    else:
        return jsonify({"error": "Failed to post tweet", "details": response.text}), 400

# Add these routes after your existing routes, before if __name__ == "__main__":
@app.route("/scheduler/start", methods=["POST", "OPTIONS"])
def start_scheduler():
    if request.method == "OPTIONS":
        return handle_preflight()
        
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
        
    token = access_token.replace("Bearer ", "")
    tweet_scheduler.save_token(token)
    tweet_scheduler.start()
    return jsonify({"message": "Scheduler started successfully"}), 200

@app.route("/scheduler/stop", methods=["POST", "OPTIONS"])
def stop_scheduler():
    if request.method == "OPTIONS":
        return handle_preflight()
        
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
        
    tweet_scheduler.stop()
    return jsonify({"message": "Scheduler stopped successfully"}), 200

@app.route("/scheduler/status", methods=["GET", "OPTIONS"])
def scheduler_status():
    if request.method == "OPTIONS":
        return handle_preflight()
        
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
        
    is_running = tweet_scheduler.is_running()
    return jsonify({
        "isRunning": is_running,
        "lastTweet": tweet_scheduler.last_tweet_time if hasattr(tweet_scheduler, 'last_tweet_time') else None
    }), 200

def handle_preflight():
    response = make_response()
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3003"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "3600"
    response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization"
    return response, 200

if __name__ == "__main__":
    app.run(debug=True)
