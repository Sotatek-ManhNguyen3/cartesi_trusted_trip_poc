## Trusted Trip POC DApp 

This example will define 2 kind of zones in map : Inner Safety Zone and Runaway Protection Zone and notice users when they enter the zone which requires charging fee.

We will use the [picket library](https://github.com/sam-drew/picket) to check whether a point is in a zone. It receives a list of coordinates, and a point. The output will be true (if that point is in the zone drew from list coordinate) or false.

## Building the environment

To run the trusted trip poc example, clone the repository as follows:

```shell
$ git clone git@github.com:Sotatek-ManhNguyen3/cartesi_trusted_trip_poc.git
```

Then, build the back-end for the trusted trip example:

```shell
$ make machine
```

## Running the environment

In order to start the containers in production mode, simply run:

```shell
$ docker-compose up --build
```

_Note:_ If you decide to use [Docker Compose V2](https://docs.docker.com/compose/cli-command/), make sure you set the [compatibility flag](https://docs.docker.com/compose/cli-command-compatibility/) when executing the command (e.g., `docker compose --compatibility up`).

Allow some time for the infrastructure to be ready.
How much will depend on your system, but after some time showing the error `"concurrent call in session"`, eventually the container logs will repeatedly show the following:

```shell
server_manager_1      | Received GetVersion
server_manager_1      | Received GetStatus
server_manager_1      |   default_rollups_id
server_manager_1      | Received GetSessionStatus for session default_rollups_id
server_manager_1      |   0
server_manager_1      | Received GetEpochStatus for session default_rollups_id epoch 0
```

To stop the containers, first end the process with `Ctrl + C`.
Then, remove the containers and associated volumes by executing:

```shell
$ docker-compose down -v
```

## Understanding the application
GPS data processing PoC in partnership with IoTeX, assuming that given GPS data input is trustworthy.</br>
Concept:

- Trusted vehicle “real-time” GPS data is sent as inputs and cross-referenced against public map datasets
- If at any time the vehicle enters a toll zone or congestion zone, a notice is issued billing the vehicle owner for tolls


The GPS data will use the format based on GPGGA (Global Positioning System Fix Data (Time, Position, Elevation))

GPGGA is a commonplace format specified by the National Marine Electronics Association (NMEA. In addition to GPS receivers, it’s also used by echo sounder, sonars, anemometer, gyrocompass, and autopilot devices.)

Example: `$GPGGA,170241.00,3401.21189,N,11824.67797,W,1,06,2.14,71.6,M,-32.9,M,,*57`

Field Description:

| Position | Field name                                         | Example data | Description                                                       |
|----------|----------------------------------------------------|--------------|-------------------------------------------------------------------|
| 0        | Sentence Type Identifier                           | $GPGGA       | GGA protocol header                                               |
| 1        | Time                                               | 170241       | 17:02:41 UTC                                                      |
| 2        | Latitude                                           | 3401.21189   | ddmm.mmmm format, converts to 34.020196 or 34d 1' 12.706" N       |
| 3        | Latitude Hemisphere                                | N            | N = North, S = South                                              |
| 4        | Longitude                                          | 11824.67797  | dddmm.mmmm format, converts to -118.41129833 or 118d 24' 48673" W |
| 5        | Longitude Hemisphere                               | W            | W = West, E = East                                                |
| 6        | - 0 = Invalid</br>- 1 = GPS fix</br>- 2 = DGPS fix | 1            | Data is from a GPS fix                                            |
| 7        | Number of Satellites                               | 6            | 6 Satellites are in view                                          |
| 8        | Horizontal Dilution of Precision (HDOP)            | 2.14         | Relative accuracy of horizontal position                          |
| 9        | Altitude                                           | 71.6         | 71.6 meters above mean sea level                                  |
| 10       | Altitude Units                                     | M            | M = meters                                                        |
| 11       | Height of geoid above WGS84 ellipsoid              | -32.9        | -32.9 meters                                                      |
| 12       | Height of geoid above WGS84 ellipsoid Units        | M            | M = meters                                                        |
| 13       | Time since last DGPS update                        | blank        | No last update                                                    |
| 14       | DGPS reference station id                          | blank        | No station id                                                     |
| 15       | Checksum                                           | *57          | Used by program to check for transmission errors                  |

## Interacting with the application

With the infrastructure in place, go to a separate terminal window and send an input as follows:

```shell
$ docker exec cartesi_trusted_trip_poc_hardhat_1 npx hardhat --network localhost trustedtrip:addInput --input "0x2447504747412C3137303234312E30302C333430312E32313138392C4E2C31313832342E36373739372C572C312C30362C322E31342C37312E362C4D2C2D33322E392C4D2C2C2A3537"
```
This input means `$GPGGA,170241.00,3401.21189,N,11824.67797,W,1,06,2.14,71.6,M,-32.9,M,,*57`

The input will have been accepted when you receive a response similar to the following one:

```shell
Added input '0x2447504747412C3137303234312E30302C333430312E32313138392C4E2C31313832342E36373739372C572C312C30362C322E31342C37312E362C4D2C2D33322E392C4D2C2C2A3537' to epoch '0' (timestamp: 1646377281, signer: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266, tx: 0xfac214be3290c7d3e856e915707a4c97538911b676eaa76e79c84133c2875d9e)
```

In order to verify the notices generated by your inputs, run the command:

```shell
$ curl http://localhost:4000/graphql -H 'Content-Type: application/json' -d '{ "query" : "query getNotice { GetNotice( query: { session_id: \"default_rollups_id\", epoch_index: \"0\", input_index: \"0\" } ) { session_id epoch_index input_index notice_index payload } }" }'
```

The response should be something like this:

```shell
{"data":{"GetNotice":[{"session_id":"default_rollups_id","epoch_index":"0","input_index":"0","notice_index":"0","payload":"596f752061726520696e2074686520746f6c6c207a6f6e652e20596f75206e65656420746f207061792074686520666565212121"}]}}
```
The data in payload is `You are in the toll zone. You need to pay the fee!!!`, it means the data gps sent to the roll up is in the toll zone.

There are three possible results:
- Invalid GPS data (If the data sent by gps does not have the correct form)
- You are good (If the location is not in the toll zone)
- You are in the toll zone. You need to pay the fee!!! (If the location is in the toll zone)
