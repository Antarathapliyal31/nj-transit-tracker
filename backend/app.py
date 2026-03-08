print("starting...")
from flask import Flask, request, jsonify, send_from_directory
import json
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import threading
import time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()
username = os.getenv("NJT_USRNAME")
password = os.getenv("NJT_PWD")
token = os.getenv("NJT_TOKEN")

def refresh_token():
    global token
    while True:
        time.sleep(24 * 60 * 60)  # wait 24 hours
        try:
            response = requests.post(
                "https://raildata.njtransit.com/api/TrainData/getToken",
                data={"username": username, "password": password}
            )
            new_token = response.json().get("token")
            if new_token:
                token = new_token
                print("Token refreshed successfully:", token[:10])
            else:
                print("Token refresh failed - keeping old token")
        except Exception as e:
            print("Token refresh error:", e)

# Start background thread
t = threading.Thread(target=refresh_token, daemon=True)
t.start()

app = Flask(__name__)
CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["100 per day", "10 per minute"])
print("TOKEN FROM ENV:", token)

@app.route("/")
def index():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, "index.html")

@app.route("/trains/<station_name>")
def get_trains(station_name):
    response1 = requests.post("https://raildata.njtransit.com/api/TrainData/getTrainSchedule19Rec", data={"token": token, "station": station_name})
    response1 = response1.json()
    response1 = response1["ITEMS"]
    return jsonify(response1)

@app.route("/trains/stops/<train>")
def getAllStops(train):
    response = requests.post("https://raildata.njtransit.com/api/TrainData/getTrainStopList", data={"token": token, "train": train})
    if not response.text:
        return jsonify({"error": "No data found"}), 404
    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True)