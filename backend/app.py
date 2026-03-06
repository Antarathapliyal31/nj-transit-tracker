print("starting...")
from flask import Flask,request, jsonify
import json
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests

load_dotenv()
token=None
username=os.getenv("NJT_USRNAME")
password=os.getenv("NJT_PWD")
token=os.getenv("NJT_TOKEN")
app=Flask(__name__)
CORS(app)
@app.route("/trains/<station_name>")
def get_trains(station_name):
    your_station_lst=[]
    response1=requests.post("https://testraildata.njtransit.com/api/TrainData/getTrainSchedule19Rec",data={"token":token,"station":station_name})
    response1=response1.json()
    response1=response1["ITEMS"]
    return jsonify(response1)

if __name__=="__main__":
    app.run(debug=True)
