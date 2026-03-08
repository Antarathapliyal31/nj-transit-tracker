print("starting...")
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import threading
import time
import sqlite3
import json
from pywebpush import webpush, WebPushException
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()
username = os.getenv("NJT_USRNAME")
password = os.getenv("NJT_PWD")
token = os.getenv("NJT_TOKEN")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_EMAIL = os.getenv("VAPID_EMAIL")

app = Flask(__name__)
CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["100 per day", "10 per minute"])

# ── DATABASE ──
def init_db():
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT UNIQUE,
        subscription TEXT,
        trains TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('subscriptions.db')

# ── TOKEN REFRESH ──
def refresh_token():
    global token
    while True:
        time.sleep(24 * 60 * 60)
        try:
            response = requests.post(
                "https://raildata.njtransit.com/api/TrainData/getToken",
                data={"username": username, "password": password}
            )
            new_token = response.json().get("token")
            if new_token:
                token = new_token
                print("Token refreshed:", token[:10])
        except Exception as e:
            print("Token refresh error:", e)

t = threading.Thread(target=refresh_token, daemon=True)
t.start()

# ── ROUTES ──
@app.route("/")
def index():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, "index.html")

@app.route("/sw.js")
def service_worker():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    response = send_from_directory(frontend_path, "sw.js", mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route("/manifest.json")
def manifest():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, "manifest.json", mimetype='application/json')

@app.route("/vapid-public-key")
def get_vapid_key():
    return jsonify({"publicKey": VAPID_PUBLIC_KEY})

@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.json
    subscription = data.get("subscription")
    trains = data.get("trains", [])
    endpoint = subscription["endpoint"]
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO subscriptions (endpoint, subscription, trains)
                 VALUES (?, ?, ?)
                 ON CONFLICT(endpoint) DO UPDATE SET trains=excluded.trains''',
              (endpoint, json.dumps(subscription), json.dumps(trains)))
    conn.commit()
    conn.close()
    return jsonify({"status": "subscribed"})

@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    data = request.json
    endpoint = data.get("endpoint")
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM subscriptions WHERE endpoint=?", (endpoint,))
    conn.commit()
    conn.close()
    return jsonify({"status": "unsubscribed"})

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

# ── PUSH NOTIFICATION CHECKER ──
def check_and_push():
    while True:
        time.sleep(60)
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT endpoint, subscription, trains FROM subscriptions")
            rows = c.fetchall()
            conn.close()

            if not rows:
                continue

            # Get all unique trains being tracked
            all_trains = set()
            for _, _, trains_json in rows:
                for train_id in json.loads(trains_json):
                    all_trains.add(train_id)

            if not all_trains:
                continue

            # Fetch NB station data (most common) — in future could be per-user station
            res = requests.post("https://raildata.njtransit.com/api/TrainData/getTrainSchedule19Rec",
                                data={"token": token, "station": "NB"})
            trains_data = res.json().get("ITEMS", [])
            train_status = {}
            for train in trains_data:
                tid = train["TRAIN_ID"]
                if tid in all_trains:
                    if "Cancelled" in train.get("STATUS", ""):
                        train_status[tid] = ("cancelled", train.get("DESTINATION", ""))
                    elif train.get("SEC_LATE", 0) > 120:
                        train_status[tid] = ("delayed", train.get("DESTINATION", ""), train.get("SEC_LATE", 0))
                    else:
                        train_status[tid] = ("ontime", train.get("DESTINATION", ""))

            # Send pushes
            for endpoint, sub_json, trains_json in rows:
                subscription = json.loads(sub_json)
                tracked = json.loads(trains_json)
                for tid in tracked:
                    if tid not in train_status:
                        continue
                    info = train_status[tid]
                    if info[0] == "cancelled":
                        title = f"🚨 Train {tid} Cancelled"
                        body = f"Train {tid} to {info[1]} has been cancelled."
                    elif info[0] == "delayed":
                        mins = int(info[2]) // 60
                        title = f"⚠️ Train {tid} Delayed"
                        body = f"Train {tid} to {info[1]} is +{mins} min late."
                    else:
                        continue
                    try:
                        webpush(
                            subscription_info=subscription,
                            data=json.dumps({"title": title, "body": body}),
                            vapid_private_key=VAPID_PRIVATE_KEY,
                            vapid_claims={"sub": VAPID_EMAIL}
                        )
                    except WebPushException as e:
                        print(f"Push failed for {endpoint[:30]}: {e}")
        except Exception as e:
            print("Push checker error:", e)

push_thread = threading.Thread(target=check_and_push, daemon=True)
push_thread.start()

if __name__ == "__main__":
    app.run(debug=True)