import asyncio # 비동기 처리를 위한 라이브러리
import os
import configparser
import math
import json
import time
from socket import *
from typing import Tuple

from BioAIR.Drones.Exception import (
    ConnectionToDroneException
)

from BioAIR.Drones.State import NodeState, TentacleState, EtcState

# from mavsdk import System
# from mavsdk import (
# 		Attitude,
# 		OffboardError,
# 		PositionNedYaw,
# 		VelocityBodyYawspeed,
# 		VelocityNedYaw,
# )

Address = Tuple[str, int]

### hyper parameter
SAMPLENUM = 5
RETRIES = 5
CORE_MODE = 0
REAL_MODE = 1
TARGETPROXIMITY = 20
TARGETFORCE = 1.0
UNKNOWN = -9999

class Node():
    def __init__(self, run_mode=REAL_MODE, configuration_file=None, log_file='logtest'):
        self.__nt_int = 'wlan0'
        self.__run_mode = run_mode
        self.__configuration_file = configuration_file
        self.__log_file = log_file
        self.__log_directory = f'{os.getcwd()}/logs'

        # asyncio를 사용하지 않겠다.
        self.__loop = None

        # Node table
        self.__node_status = {}  # node_id, node_state, node_position_x, node_position_y, node_last_communication_time, node_signal
        self.__node_signal = {}  #

        self.__initialization(self.__configuration_file)

        # Bioairing()을 사용하지 않을 것이므로~
        self.__loop = asyncio.get_event_loop()
        coro = self.__loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', self.__port))
        asyncio.ensure_future(coro)
        # asyncio.ensure_future(self.__bioairing())

        if self.__run_mode == CORE_MODE:
            # Read configurate file
            pass
        elif self.__run_mode == REAL_MODE:
            import re, uuid
            self.__mac = ':'.join((re.findall('..', '%012x' % uuid.getnode())))
            print("The MAC address in formatted and less complex way is : ", self.__mac)

            self.__connection_with_drone()

            if self.__drone == None:
                raise ConnectionToDroneException()
            asyncio.ensure_future(self.__update_position())

        # self.run(0)

    def __initialization(self, configuration_file):
        self.__core_ip = '127.0.0.1'
        self.__drone = None
        self.__mac = None
        self.__id = -1  # Node Id

        # state를 살려둔 이유는 이걸로 Done을 파악하기 위해서!!
        self.__state = NodeState.Loading  # Node State

        self.__position_x = None  # X = longitude
        self.__position_y = None  # Y = latitude
        self.__destinations = []
        self.__dest_index = 0
        self.__dest_id = None
        self.__dest_position_x = None
        self.__dest_position_y = None
        self.__origin_id = None
        self.__origin_position_x = None
        self.__origin_position_y = None
        self.__altitude = None

        # tentacle이 필요할까?
        # self.__tentacle_state = TentacleState.Forming
        # self.__tentacle_id = UNKNOWN
        # self.__tentacle_within_pos = UNKNOWN

        self.__port = 10800
        self.__incompltete_orphan = 0
        self.__hold = False

        # signal quality
        self.__max_groundspeed = 10
        self.__radio_range = 0
        self.__highSQ = 0.3
        self.__lowSQ = 0.1
        self.__equilibrium_zone = 0.1
        self.__equilibrium = 0
        self.__prev_vel_x = 0
        self.__prev_vel_y = 0

        config = configparser.ConfigParser()
        config.read(configuration_file)

        # core configuration
        if 'CORE_IP' in config['CORE']:
            self.__core_ip = config['CORE']['CORE_IP']

        if 'MAC' in config['CORE']:
            self.__mac = config['CORE']['MAC']

        if 'ID' in config['CORE']:
            self.__id = int(config['CORE']['ID'])

        # state를 살려둔 이유는 이걸로 Done을 파악하기 위해서
        if 'STATE' in config['CORE']:
            self.__state = config['CORE']['STATE']

            if self.__state == 'Origin':
                self.__state = NodeState.Origin
            elif self.__state == 'Destination':
                self.__state = NodeState.Destination
            elif self.__state == 'Free':
                self.__state = NodeState.Free
            elif self.__state == 'Orphan':
                self.__state = NodeState.Orphan

        if 'POSITION_X' in config['CORE']:
            self.__position_x = float(config['CORE']['POSITION_X'])

        if 'POSITION_Y' in config['CORE']:
            self.__position_y = float(config['CORE']['POSITION_Y'])

        if 'ALTITUDE' in config['CORE']:
            self.__altitude = float(config['CORE']['ALTITUDE'])

        if 'ORIGIN_ID' in config['CORE']:
            self.__origin_id = int(config['CORE']['ORIGIN_ID'])

            if 'ORIGIN_POSITION_X' in config['CORE']:
                self.__origin_position_x = float(config['CORE']['ORIGIN_POSITION_X'])
            else:
                print("No ORIGIN_POSITION_X")
                raise ValueError

            if 'ORIGIN_POSITION_Y' in config['CORE']:
                self.__origin_position_y = float(config['CORE']['ORIGIN_POSITION_Y'])
            else:
                print("No ORIGIN_POSITION_Y")
                raise ValueError

            self.__add_node_status(self.__origin_id, UNKNOWN, self.__origin_position_x, self.__origin_position_y,
                                   UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN)
            self.__refresh_origin()

        if 'DEST_ID' in config['CORE']:
            self.__dest_id = int(config['CORE']['DEST_ID'])

            if 'DEST_POSITION_X' in config['CORE']:
                self.__dest_position_x = float(config['CORE']['DEST_POSITION_X'])
            else:
                print("No DEST_POSITION_X")
                raise ValueError

            if 'DEST_POSITION_Y' in config['CORE']:
                self.__dest_position_y = float(config['CORE']['DEST_POSITION_Y'])
            else:
                print("No DEST_POSITION_Y")
                raise ValueError

            self.__add_node_status(self.__dest_id, UNKNOWN, self.__dest_position_x, self.__dest_position_y, UNKNOWN,
                                   UNKNOWN, UNKNOWN, UNKNOWN)
            self.__update_destination(self.__dest_id, 1)

        if 'PORT' in config['CORE']:
            self.__port = int(config['CORE']['PORT'])

        if 'RADIO_RANGE' in config['CORE']:
            self.__radio_range = float(config['CORE']['RADIO_RANGE'])

        if 'MAX_GROUNDSPEED' in config['CORE']:
            self.__max_groundspeed = float(config['CORE']['MAX_GROUNDSPEED'])

        # signal configuration
        if 'HIGH_SQ' in config['SIGNAL']:
            self.__highSQ = float(config['SIGNAL']['HIGH_SQ'])

        if 'LOW_SQ' in config['SIGNAL']:
            self.__lowSQ = float(config['SIGNAL']['LOW_SQ'])

        if 'EQUILIBRIUM_ZONE' in config['SIGNAL']:
            self.__equilibrium_zone = float(config['SIGNAL']['EQUILIBRIUM_ZONE'])

        if 'EQUILIBRIUM' in config['SIGNAL']:
            self.__equilibrium = float(config['SIGNAL']['EQUILIBRIUM'])

        # end of configuration

        print(f'Node {self.__id} is registered');


    def __add_node_status(self, node_id, node_state, node_position_x, node_position_y, node_signal, tentacle_id,
                          tentacle_state, tentacle_within_pos):
        # add or update nodes statue
        if node_id in self.__node_status:
            # update
            self.__node_signal[node_id].pop(0)
            self.__node_signal[node_id].append(node_signal)

            avg_signal = 0
            sig_count = 0

            for i in self.__node_signal[node_id]:
                if i != UNKNOWN:
                    avg_signal += i
                    sig_count += 1

            if sig_count == 0:
                avg_signal = UNKNOWN
            else:
                avg_signal /= sig_count

            self.__node_status[node_id]['node_state'] = node_state
            self.__node_status[node_id]['node_position_x'] = node_position_x
            self.__node_status[node_id]['node_position_y'] = node_position_y
            self.__node_status[node_id]['node_last_connection_time'] = 0
            self.__node_status[node_id]['node_signal'] = avg_signal
            self.__node_status[node_id]['tentacle_id'] = tentacle_id
            self.__node_status[node_id]['tentacle_state'] = tentacle_state
            self.__node_status[node_id]['tentacle_within_pos'] = tentacle_within_pos

        else:
            # add
            self.__node_status[node_id] = {}
            self.__node_signal[node_id] = [node_signal] * SAMPLENUM

            self.__node_status[node_id]['node_state'] = node_state
            self.__node_status[node_id]['node_position_x'] = node_position_x
            self.__node_status[node_id]['node_position_y'] = node_position_y
            self.__node_status[node_id]['node_last_connection_time'] = 0
            self.__node_status[node_id]['node_signal'] = node_signal
            self.__node_status[node_id]['tentacle_id'] = tentacle_id
            self.__node_status[node_id]['tentacle_state'] = tentacle_state
            self.__node_status[node_id]['tentacle_within_pos'] = tentacle_within_pos


    def __refresh_origin(self):
        self.__origin_position_x = self.__node_status[self.__origin_id]['node_position_x']
        self.__origin_position_y = self.__node_status[self.__origin_id]['node_position_y']


    def __refresh_destination(self, dest_id):
        self.__dest_position_x = self.__node_status[dest_id]['node_position_x']
        self.__dest_position_y = self.__node_status[dest_id]['node_position_y']


    # About drone
    async def __connection_with_drone(self):
        self.__drone = System()
        await self.__drone.connect(system_address="udp://:14551")

        print("Waiting for drone...")

        async for state in self.__drone.core.connection_state():
            if state.is_connected:
                mav_sys_id = await self.__drone.param.get_int_param('MAV_SYS_ID')
                print(f"Drone discovered with MAV_SYS_ID: {mav_sys_id}")
                self.__droneID = mav_sys_id  # MAV_SYS_ID 를 사용하자
                break


    async def __update_position(self):
        async for position in self.__drone.telemetry.position():
            # print(f"cur_position: {position}")
            self.__position_x = position.longitude_deg
            self.__position_y = position.latitude_deg
            self.__altitude = position.altitude_m


    async def update_location(self, vel_x, vel_y):
        expected_x, expected_y, wp_latitude, wp_longtitude = 0, 0, 0, 0
        wait_time = 0

        if (((self.__prev_vel_x < 0) and (vel_x >= 0)) or ((self.__prev_vel_x > 0) and (vel_x <= 0)) or (
                (self.__prev_vel_x == 0) and (vel_x != 0)) or ((self.__prev_vel_y < 0) and (vel_y >= 0)) or (
                (self.__prev_vel_y > 0) and (vel_y <= 0)) or ((self.__prev_vel_y == 0) and (vel_y != 0))):
            wait_time = 0
        else:
            wait_time = 1.5 * ((vel_x ** 2) + (vel_y ** 2))

        vel_x = vel_x * self.__max_groundspeed
        vel_y = vel_y * self.__max_groundspeed

        if (vel_x >= self.__max_groundspeed):
            vel_y = (vel_y * self.__max_groundspeed) / vel_x
            vel_x = self.__max_groundspeed
        elif (vel_x <= -self.__max_groundspeed):
            vel_y = (vel_y * (0 - self.__max_groundspeed)) / vel_x
            vel_x = -self.__max_groundspeed

        if (vel_y >= self.__max_groundspeed):
            vel_x = (vel_x * self.__max_groundspeed) / vel_y
            vel_y = self.__max_groundspeed
        elif (vel_y <= -self.__max_groundspeed):
            vel_x = (vel_x * (0 - self.__max_groundspeed)) / vel_y
            vel_y = -self.__max_groundspeed

        if self.__run_mode == CORE_MODE:
            await asyncio.sleep(0.5)
            self.__position_x = self.__position_x + (vel_x * 0.3)
            self.__position_y = self.__position_y + (vel_y * 0.3)
            self.__update_core_position(self.__id, self.__state, self.__position_x, self.__position_y)

        elif self.__run_mode == REAL_MODE:
            self.__update_real_position(self.__position_x, self.__position_y, vel_x, vel_y)
            pass
        elif self.__run_mode == 2:
            pass

    def __update_destination(self, dest_id, update_type):
        done = False

        if update_type > 0:
            self.__destinations.append(dest_id)
        elif update_type < 0:
            if update_type == UNKNOWN:
                self.__dest_index = 0
            else:
                self.__dest_index += 1

            if self.__dest_index >= len(self.__destinations):
                self.__dest_index = len(self.__destinations) - 1
                done = True

            elif dest_id == UNKNOWN:
                self.__dest_index -= 1

        # tentacle id를 쓸 필요 없으므로 제거
        # self.__change_tetacle_id(self.__destinations[self.__dest_index])

        self.__refresh_destination(self.__destinations[self.__dest_index])
        return done

    # Render 함수에서 각각의 node의 id, state, tentacle_state, position_x, position_y를 받아서 이 함수를 호출하여 CORE-GUI를 갱신해주게 하자!
    def __update_core_position(self, node_id, state, position_x, position_y):
        cmd = f'coresendmsg -a {self.__core_ip} NODE NUMBER={node_id} NAME={node_id}_{state} X_POSITION={int(position_x)} Y_POSITION={int(position_y)}'
        # start cmd
        # print(cmd)
        os.popen(cmd)

    # 신호 세기를 받아오기 위해서
    def __get_signal_quality(self, node_mac, node_position_x, node_position_y):
        if self.__run_mode == CORE_MODE:  # CORE
            rxSignal = math.sqrt((self.__position_x - node_position_x) ** 2 + (self.__position_y - node_position_y) ** 2)

            if (rxSignal < self.__radio_range):
                # rxSignal = 50 - (10 * math.log(rxSignal/4))
                rxSignal = 1 - (rxSignal / self.__radio_range)
            else:
                rxSignal = UNKNOWN

        elif self.__run_mode == REAL_MODE:  # Real
            check_signal_cmd = f'iw dev {self.__nt_int} station get {node_mac} | grep signal: | grep -oE ([-]{{1}}[0-9]*){{1}}'
            result = os.popen(check_signal_cmd).read()

            if result == '':
                rxSignal = UNKNOWN

            else:
                rxSignal = int(result.strip().split('\n')[0])
                rxSignal = 1.0 + (rxSignal / 101)

        return rxSignal

    # 이거가 있어야 신호 세기를 주고 받을 수 있을 것 같음..
    def __broadcast(self):
        connectionInfo = ('<broadcast>', self.__port)

        data = json.dumps({
            'node_id': self.__id,
            'node_state': self.__state.value,
            'node_position_x': self.__position_x,
            'node_position_y': self.__position_y,
            'node_mac': self.__mac,
            # tentacle은 안 필요할 것 같음
            # 'tentacle_id': self.__tentacle_id,
            # 'tentacle_state': self.__tentacle_state.value,
            # 'tentacle_within_pos': self.__tentacle_within_pos,
        })

        self.__transport.sendto(data.encode(), connectionInfo)

        # print(f"-- Broadcast : {self.__mac} / node_id : {self.__id}, node_state : {self.__state}, node_position_x : {self.__position_x}, node_position_y : {self.__position_y}, tentacle_id : {self.__tentacle_id}, tentacle_within_pos : {self.__tentacle_within_pos}')

        self.__loop.call_later(1, self.__broadcast)

    # brodcast를 받기 위해서
    def datagram_received(self, data, addr: Address):

        data = json.loads(data.decode())
        node_mac = data.get('node_mac')

        if node_mac == self.__mac:
            # print("-- From myself")
            return

        if self.__state == NodeState.Loading:
            print("-- Drone is not ready")
            return

        node_id = data.get('node_id')
        node_state = data.get('node_state')
        node_state = NodeState(node_state)
        node_position_x = data.get('node_position_x')
        node_position_y = data.get('node_position_y')

        # tentacle은 안 필요할 것 같음
        # tentacle_id = data.get('tentacle_id')
        # tentacle_state = data.get('tentacle_state')
        # tentacle_state = TentacleState(tentacle_state)
        # tentacle_within_pos = data.get('tentacle_within_pos')

        node_signal = self.__get_signal_quality(node_mac, node_position_x, node_position_y)

        # Test를 위해 node_signal을 반환하도록 함
        print(node_position_x + ", " + node_position_y + ", " + node_signal)
        return node_signal

        log = f"-- From : {node_mac} / SQ : {node_signal} / node_id : {node_id}, node_state : {node_state}, node_position_x : {node_position_x}, node_position_y : {node_position_y}, tentacle_id : {tentacle_id}, tentacle_state : {tentacle_state} tentacle_within_pos : {tentacle_within_pos}"

        print(log)

        # write data to log.file
        timestr = time.strftime("%Y%m%d-%H%M%S")
        try:
            if not (os.path.isdir(self.__log_directory)):
                os.makedirs(os.path.join(self.__log_directory))
        except OSError as e:
            if e.errno != errno.EEXIST:
                print("Failed to create directory !")
                raise

        with open(f'{os.getcwd()}/logs/{self.__id}_{self.__log_file}.log', 'a') as f:
            log = f'{timestr} ID {self.__id} X {self.__position_x} Y {self.__position_y} STATE {self.__state} \n' + log + '\n'
            f.write(log)

        self.__add_node_status(node_id, node_state, node_position_x, node_position_y, node_signal, tentacle_id,
                               tentacle_state, tentacle_within_pos)
        # self.__update_status(node_id, node_state, node_signal, tentacle_id, tentacle_state, tentacle_within_pos)

    # About communication
    def connection_made(self, transport: asyncio.DatagramTransport):
        self.__transport = transport
        sock = self.__transport.get_extra_info('socket')
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        self.__broadcast()
