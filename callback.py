from flask import Flask, request, jsonify, redirect
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a Flask app
app = Flask(__name__)

# Twitter API credentials
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_CALLBACK_URL = "http://127.0.0.1:5000/callback"  # Your callback URL

# Callback route to handle OAuth response from Twitter
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Exchange authorization code for access token
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

    return jsonify({"message": "Authentication successful!", "access_token": access_token})

if __name__ == "__main__":
    app.run(debug=True)