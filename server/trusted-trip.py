# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from os import environ
import logging
import requests
from flask import Flask, request
import json
from libs import picket

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

dispatcher_url = environ["HTTP_DISPATCHER_URL"]
app.logger.info(f"HTTP dispatcher url is {dispatcher_url}")


def is_in_the_toll_zone(gps_data):
    latitude = float(gps_data[2][:2]) + float(gps_data[2][2:]) / 60
    longitude = float(gps_data[4][:2]) + float(gps_data[4][2:]) / 60
    print("Latitude: " + str(latitude))
    print("Longitude: " + str(longitude))

    f = open('Airport_Runway_Protection_Zone_and_Inner_Safety_Zone.geojson')
    data = json.load(f)

    for zone in data['features']:
        if zone['properties']['ZONE_TYPE'] != "Runway Protection Zone":
            continue

        for inner_zone in zone['geometry']['coordinates']:
            print('Inner zone')
            print(len(inner_zone))
            if len(inner_zone) < 3:
                continue

            fence = create_fence(inner_zone)
            if fence.check_point((longitude, latitude)):
                return True

    return False


def create_fence(coordinates):
    fence = picket.Fence()

    for each_pair in coordinates:
        fence.add_point((each_pair[0], each_pair[1]))

    return fence


def call_back_to_rollup(result):
    result = "0x" + result.encode().hex()
    print("result in hex")
    print(result)
    print("Adding notice")
    response = requests.post(dispatcher_url + "/notice", json={"payload": result})
    print(f"Received notice status {response.status_code} body {response.json()}")
    print("Finishing")
    response = requests.post(dispatcher_url + "/finish", json={"status": "accept"})
    print(f"Received finish status {response.status_code}")


@app.route('/advance', methods=['POST'])
def advance():
    body = request.get_json("metadata")
    print(f"Received advance request body {body}")

    data = bytes.fromhex(body["payload"][2:])
    data = data.decode().split(",")
    print(data)
    if len(data) != 15:
        result = "Invalid GPS data"
        call_back_to_rollup(result)
        return "", 202

    is_toll_zone = is_in_the_toll_zone(data)

    if is_toll_zone:
        result = "You are in the toll zone. You need to pay the fee!!!"
    else:
        result = "You are good"

    print(result)
    call_back_to_rollup(result)
    return "", 202


@app.route('/inspect', methods=['GET'])
def inspect(payload):
    print('abcde')
    print(f"Received inspect request payload {payload}")
    return {"reports": [{"payload": payload}]}, 200
