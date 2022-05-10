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
import json
from libs import picket

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")


def to_hex(value):
    return "0x" + value.encode().hex()


def add_notice(message):
    message = to_hex(message)
    print("Adding notice")
    response = requests.post(rollup_server + "/notice", json={"payload": message})
    print(f"Received notice status {response.status_code} body {response.json()}")
    return True


def add_voucher(address, message):
    message = to_hex(message)
    print("Adding voucher")
    response = requests.post(rollup_server + "/voucher", json={"payload": message, "address": address})
    print(f"Received voucher status {response.status_code}")
    return True


def create_fence(coordinates):
    fence = picket.Fence()

    for each_pair in coordinates:
        fence.add_point((each_pair[0], each_pair[1]))

    return fence


def check_point_in_zone(gps_data, latitude, longitude):
    if type(gps_data[0][0]) in (float, int):
        if len(gps_data) < 3:
            return False

        fence = create_fence(gps_data)
        if fence.check_point((latitude, longitude)):
            return True

        return False

    for inner_zone in gps_data:
        is_in_zone = check_point_in_zone(inner_zone, latitude, longitude)
        if is_in_zone:
            return True

    return False


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

        if check_point_in_zone(zone['geometry']['coordinates'], latitude, longitude):
            return True

    return False


def handle_advance(data):
    body = data
    print(f"Received advance request body {body}")

    data = bytes.fromhex(body["payload"][2:])
    data = data.decode().split(",")
    print(data)
    if len(data) != 15:
        result = "Invalid GPS data"
        add_notice(result)
        return "accept"

    try:
        is_toll_zone = is_in_the_toll_zone(data)
    except Exception as e:
        result = "EXCEPTION: " + e.__str__()
        print("NOTICE EXCEPTION" + e.__str__())
        add_notice(result)
        return "accept"

    if is_toll_zone:
        result = "You are in the toll zone. You need to pay the fee!!!"
        address = body["metadata"]["msg_sender"]
        add_voucher(address, result)
    else:
        result = "You are good"
        add_notice(result)

    print(result)
    return "accept"


def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    logger.info("Adding report")
    report = {"payload": data["payload"]}
    response = requests.post(rollup_server + "/report", json=report)
    logger.info(f"Received report status {response.status_code}")
    return "accept"


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}


finish = {"status": "accept"}
while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])
