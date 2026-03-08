print("starting...")
from flask import Flask,request, jsonify,send_from_directory
import json
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address



load_dotenv()
token=None
username=os.getenv("NJT_USRNAME")
password=os.getenv("NJT_PWD")
token=os.getenv("NJT_TOKEN")
app=Flask(__name__)
CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["100 per day", "10 per minute"])

print("TOKEN FROM ENV:", os.getenv("NJT_TOKEN"))
# response = requests.post("https://raildata.njtransit.com/api/TrainData/getToken", data={"username": username, "password": password})
# print(response.json())
# token = response.json().get("token")

@app.route("/")
def index():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, "index.html")

@app.route("/trains/<station_name>")
def get_trains(station_name):
    your_station_lst=[]
    response1=requests.post("https://raildata.njtransit.com/api/TrainData/getTrainSchedule19Rec",data={"token":token,"station":station_name})
    response1=response1.json()
    response1=response1["ITEMS"]
    return jsonify(response1)

@app.route("/trains/stops/<train>")
def getAllStops(train):
    print("Sending to NJT:", {"token": token, "train": train})
    response=requests.post("https://raildata.njtransit.com/api/TrainData/getTrainStopList",data={"token":token,"train":train})
    print("Response status:", response.status_code)
    print("Response text:", response.text[:200])
    print("Token:", token[:10])  # just first 10 chars to verify token is there
    if not response.text:
        return jsonify({"error": "No data found"}), 404
    return jsonify(response.json())


if __name__=="__main__":
    app.run(debug=True)
