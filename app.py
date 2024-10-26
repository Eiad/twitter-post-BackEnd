import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, make_response
from flask_cors import CORS
from scheduler import TweetScheduler
import json
import openai

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
    remaining_tweets = tweet_scheduler.get_remaining_tweets_count()
    
    if not is_running or remaining_tweets == 0:
        tweet_scheduler.stop()  # Ensure scheduler is fully stopped
    
    return jsonify({
        "isRunning": is_running,
        "lastTweet": tweet_scheduler.last_tweet_time if hasattr(tweet_scheduler, 'last_tweet_time') else None,
        "remainingTweets": remaining_tweets
    }), 200

@app.route("/generate-tweet", methods=["POST"])
def generate_tweet():
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
    
    criteria = request.json
    
    try:
        openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional social media expert who creates engaging tweets."},
                {"role": "user", "content": f"""Generate a tweet about {criteria['topic']} with these specifications:
                - Industry: {criteria['industry']}
                - Tone: {criteria['tone']}
                - Maximum length: {criteria['length']} characters
                
                The tweet should be engaging and relevant to the {criteria['industry']} industry.
                Use a {criteria['tone']} tone and make it concise but impactful.
                Include relevant hashtags if appropriate."""}
            ]
        )
        
        generated_tweet = completion.choices[0].message.content.strip()
        
        return jsonify({
            "tweet": generated_tweet,
            "criteria": criteria
        }), 200
        
    except Exception as e:
        print(f"Error generating tweet: {str(e)}")
        return jsonify({"error": "Failed to generate tweet"}), 500

@app.route("/generate-tweets", methods=["POST"])
def generate_tweets():
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
    
    criteria = request.json
    
    try:
        openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        tweets = []
        
        # Convert numberOfTweets to integer
        number_of_tweets = int(criteria['numberOfTweets'])
        
        for i in range(number_of_tweets):
            completion = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional social media expert specialized in creating engaging and effective tweets. Your task is to generate a tweet that perfectly matches the given criteria."},
                    {"role": "user", "content": f"""Generate a unique tweet about {criteria['topic']} with these specifications:
                    - Industry: {criteria['industry']}
                    - Tone: {criteria['tone']}
                    - Maximum length: {criteria['length']} characters
                    
                    The tweet should be engaging, relevant to the {criteria['industry']} industry, and use a {criteria['tone']} tone.
                    Make it concise but impactful, and include relevant hashtags if appropriate.
                    Ensure this tweet is different from any others in the series."""}
                ]
            )
            tweets.append({
                'id': i + 1,
                'content': completion.choices[0].message.content.strip()
            })
        
        return jsonify({
            "message": f"Generated {len(tweets)} tweets",
            "tweets": tweets
        }), 200
        
    except ValueError as ve:
        print(f"Error generating tweets: Invalid number of tweets - {str(ve)}")
        return jsonify({"error": "Invalid number of tweets provided"}), 400
    except Exception as e:
        print(f"Error generating tweets: {str(e)}")
        return jsonify({"error": "Failed to generate tweets"}), 500

@app.route("/schedule-tweets", methods=["POST"])
def schedule_tweets():
    access_token = request.headers.get("Authorization")
    if not access_token:
        return jsonify({"error": "No access token provided"}), 401
    
    data = request.json
    tweets = data.get("tweets")
    interval = data.get("interval")
    
    if not tweets or not interval:
        return jsonify({"error": "Missing tweets or interval"}), 400
    
    if not isinstance(tweets, list) or len(tweets) == 0:
        return jsonify({"error": "Invalid tweets format or empty tweets list"}), 400
    
    try:
        interval_seconds = (
            int(interval.get('days', 0)) * 86400 +
            int(interval.get('hours', 0)) * 3600 +
            int(interval.get('minutes', 0)) * 60 +
            int(interval.get('seconds', 0))
        )
        if interval_seconds <= 0:
            return jsonify({"error": "Invalid interval, must be greater than 0 seconds"}), 400
    except ValueError:
        return jsonify({"error": "Invalid interval values, must be integers"}), 400
    
    try:
        token = access_token.replace("Bearer ", "")
        tweet_scheduler.save_token(token)
        tweet_scheduler.schedule_tweets(tweets, interval)
        
        return jsonify({
            "message": f"Scheduled {len(tweets)} tweets with custom interval"
        }), 200
        
    except Exception as e:
        print(f"Error scheduling tweets: {str(e)}")
        return jsonify({"error": f"Failed to schedule tweets: {str(e)}"}), 500

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
