import asyncio  # 비동기 처리를 위한 라이브러리
import configparser
import os

# import Rectangle

# from BioAIR.Drones.Exception import (
#     ConnectionToDroneException
# )

# from BioAIR.Drones.State import NodeState, TentacleState, EtcState

### hyper parameter
SAMPLENUM = 5
RETRIES = 5
CORE_MODE = 0
REAL_MODE = 1
TARGETPROXIMITY = 20
TARGETFORCE = 1.0
UNKNOWN = -9999

### Action Type
Action = {
    0: (0, 5),  # 상
    1: (0, -5),  # 하
    2: (-5, 0),  # 좌
    3: (5, 0)  # 우
}

### Box Configure
Box_Configure = {
    "x1": 0,
    "y1": 0,
    "width": 1000,
    "height": 1000
}


class Rectangle():
    def __init__(self, x1, y1, width, height):
        self.width = width
        self.height = height
        self.x1 = x1
        self.y1 = y1
        self.x2 = x1 + width
        self.y2 = y1
        self.x3 = x1
        self.y3 = y1 + height
        self.x4 = x1 + width
        self.y4 = y1 + height

    def is_beyond_range(self, x, y):
        if ((self.x1 < x) and (x < self.x2)) and ((self.y1 < y) and (y < self.y3)):
            return False
        else:
            return True


class Node(asyncio.DatagramProtocol):

    def __init__(self, run_mode=REAL_MODE, configuration_file=None, log_file='logtest'):
        # Done을 체크하기 위한 가상의 박스를 만듦
        self.__box = Rectangle(Box_Configure['x1'], Box_Configure['y1'], Box_Configure['width'],
                               Box_Configure['height'])

        self.__nt_int = 'wlan0'
        self.__run_mode = run_mode
        self.__configuration_file = configuration_file
        self.__log_file = log_file
        self.__log_directory = f'{os.getcwd()}/logs'

        self.__loop = None

        # Node table
        self.__node_status = {}  # node_id, node_state, node_position_x, node_position_y, node_last_communication_time, node_signal
        self.__node_signal = {}  #

        self.__initialization(self.__configuration_file)

        self.__loop = asyncio.get_event_loop()
        coro = self.__loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', self.__port))
        asyncio.ensure_future(coro)
        asyncio.ensure_future(self.step(1))
        # bioairing() 안 쓸것이므로 주석처리
        # asyncio.ensure_future(self.__bioairing())

        if self.__run_mode == CORE_MODE:
            # Read configurate file
            pass
        elif self.__run_mode == REAL_MODE:
            import re, uuid
            self.__mac = ':'.join((re.findall('..', '%012x' % uuid.getnode())))
            print("The MAC address in formatted and less complex way is : ", self.__mac)

            # 실제로 드론 연결한 것 아니므로 일단 주석처리
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
        self.__position_x = None  # X = longitude
        self.__position_y = None  # Y = latitude
        # 상태를 x,y 좌표로 할 것이므로 주석처리
        # self.__state = NodeState.Loading # Node State
        self.__destinations = []
        self.__dest_index = 0
        self.__dest_id = None
        self.__dest_position_x = None
        self.__dest_position_y = None
        self.__origin_id = None
        self.__origin_position_x = None
        self.__origin_position_y = None
        self.__altitude = None
        # 강화학습을 할 것이므로 Tentacle의 개념이 안 쓰일 것 같아서 주석처리
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

        # 각 STATE를 노드의 좌표 값으로 하기로 했으므로 주석처리
        # if 'STATE' in config['CORE']:
        #     self.__state = config['CORE']['STATE']
        #
        #     if self.__state == 'Origin':
        #         self.__state = NodeState.Origin
        #     elif self.__state == 'Destination':
        #         self.__state = NodeState.Destination
        #     elif self.__state == 'Free':
        #         self.__state = NodeState.Free
        #     elif self.__state == 'Orphan':
        #         self.__state = NodeState.Orphan

        if 'POSITION_X' in config['CORE']:
            self.__position_x = float(config['CORE']['POSITION_X'])

        if 'POSITION_Y' in config['CORE']:
            self.__position_y = float(config['CORE']['POSITION_Y'])

        # state 값을 좌표로 이용하기 위해 이 코드를 추가함
        self.__state = (self.__position_x, self.__position_y)

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

            # 필요없는 함수라서 주석처리
            # self.__add_node_status(self.__origin_id, UNKNOWN, self.__origin_position_x, self.__origin_position_y,
            #                        UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN)
            # self.__refresh_origin()

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

            # 필요없는 함수라서 주석처리
            # self.__add_node_status(self.__dest_id, UNKNOWN, self.__dest_position_x, self.__dest_position_y, UNKNOWN,
            #                        UNKNOWN, UNKNOWN, UNKNOWN)
            # self.__update_destination(self.__dest_id, 1)

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

    async def __update_location(self, vel_x, vel_y):
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

        # if self.__run_mode == CORE_MODE:
        #     await asyncio.sleep(0.5)
        #     self.__position_x = self.__position_x + (vel_x * 0.3)
        #     self.__position_y = self.__position_y + (vel_y * 0.3)
        #     self.__update_core_position(self.__id, self.__state, self.__tentacle_state, self.__position_x,
        #                                 self.__position_y)
        #
        # elif self.__run_mode == REAL_MODE:
        #     self.__update_real_position(self.__position_x, self.__position_y, vel_x, vel_y)
        #     pass
        # elif self.__run_mode == 2:
        #     pass

    def __update_core_position(self, node_id, state, position_x, position_y):
        cmd = f'coresendmsg -a {self.__core_ip} NODE NUMBER={node_id} NAME={node_id}_{state} X_POSITION={int(position_x)} Y_POSITION={int(position_y)}'
        # start cmd
        # print(cmd)
        os.popen(cmd)

    def __update_real_position(self, position_x, position_y, vel_x, vel_y):
        print(f'From ({position_x}, {position_y}) move with vel_x : {vel_x}, vel_y : {vel_y}')

        self.__drone.offboard.set_velocity_ned(vel_y, vel_x, 0.0, 0.0)

    # Set the drone be ready
    def run(self, height):
        # Do
        print("Start BioAIR")

        if self.__run_mode == REAL_MODE:
            self.__change_mode_to_offboard()
            self.__takeoff_m(height)

        print("Drone is ready")
        self.__loop.run_forever()

    def reset(self):
        self.__init__(self.__run_mode, self.__configuration_file, self.__log_file)
        # Return Observation
        # if self.__state == NodeState.Loading:
        #     return None
        # else:
        #     return self.__state
        return self.__state

    async def step(self, action):
        direction = Action[action]

        vel_x, vel_y = direction
        await self.__update_location(vel_x, vel_y)
        self.__prev_vel_x = vel_x
        self.__prev_vel_y = vel_y

        await asyncio.sleep(0.5)  # 왜 잠을 재우는지는 모르겠음..

        self.__state = (self.__position_x, self.__position_y)  # state를 (position_x, position_y)로 정의함

        Done = False  # Done : 가상의 Rectangle의 범위를 넘어서면 True
        if self.__box.is_beyond_range(self.__position_x, self.__position_y):
            Done = True

        ob = Observation(self.__position_x, self.__position_y)  # Observation : (x, y)

        Info = {}  # Info : 아직 사용되지 않음

        distance_x = abs(self.__dest_position_x - self.__position_x)
        distance_y = abs(self.__dest_position_y - self.__position_y)

        # Reward = Width - distance
        reward_x = self.__box.width - distance_x
        reward_y = self.__box.height - distance_y

        # Total Reward
        Reward = reward_x + reward_y

        return Done, ob, Info, Reward

    async def render(self):
        print("Render Function")
        if self.__run_mode == CORE_MODE:
            await asyncio.sleep(0.5)
            self.__position_x = self.__position_x + (self.__prev_vel_x * 0.3)
            self.__position_y = self.__position_y + (self.__prev_vel_y * 0.3)
            self.__update_core_position(self.__id, self.__state, self.__position_x, self.__position_y)

        elif self.__run_mode == REAL_MODE:
            self.__update_real_position(self.__position_x, self.__position_y, self.__prev_vel_x, self.__prev_vel_y)
            pass
        elif self.__run_mode == 2:
            pass

        return


class Observation():
    def __init__(self, x, y):
        self.x = x
        self.y = y


