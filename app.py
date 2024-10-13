import os
import tweepy
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Twitter API credentials
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_CALLBACK_URL = os.getenv("TWITTER_CALLBACK_URL") 
FRONTEND_URL = os.getenv("FRONTEND_URL") 

# Create a Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Route to start the OAuth 2.0 flow and redirect to Twitter
@app.route("/auth")
def authenticate():
    auth_url = f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id={TWITTER_CLIENT_ID}&redirect_uri={TWITTER_CALLBACK_URL}&scope=tweet.read%20tweet.write%20users.read&state=state&code_challenge=challenge&code_challenge_method=plain"
    return redirect(auth_url)

# Callback route to handle OAuth response from Twitter
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code provided"}), 400

    
    # Sending a POST request to the twitter API endpoint with the provided data
    response = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        data={
            "client_id": TWITTER_CLIENT_ID,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": TWITTER_CALLBACK_URL,
            "code_verifier": "challenge",
        },
        auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to get access token", "details": response.text}), 400

    # Get access token from the response
    access_token = response.json().get("access_token")

    # Redirect to the frontend with the access token
    return redirect(f"{FRONTEND_URL}?access_token={access_token}")

# Define a route for posting tweets
@app.route("/tweet", methods=["POST"])
def post_tweet():
    tweet_text = request.json.get("tweet", "")
    access_token = request.headers.get("Authorization").split(" ")[1]

    if not access_token:
        return jsonify({"error": "No access token available"}), 400

    # Use the access token to post a tweet
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    tweet_response = requests.post(
        "https://api.twitter.com/2/tweets",
        headers=headers,
        json={"text": tweet_text}
    )

    if tweet_response.status_code != 201:
        return jsonify({"error": "Failed to post tweet", "details": tweet_response.text}), tweet_response.status_code

    return jsonify({"message": "Tweet posted successfully!", "tweet_data": tweet_response.json()}), 201

if __name__ == "__main__":
    app.run(debug=True)
