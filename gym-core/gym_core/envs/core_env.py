import gym
from gym import error, spaces, utils
from gym.utils import seeding

import os
import asyncio
import numpy as np
import json
from socket import *
from typing import Tuple

from BioAIR.Drones.State import NodeState, TentacleState, EtcState

Address = Tuple[str, int]

### Action Type
Action = {
    'top' : (0, 5), # 상
    'bottom' : (0, -5), # 하
    'left' : (-5, 0), # 좌
    'right' : (5, 0), # 우
    'stop' : (0, 0) # 정지
}
ActionType = ['top', 'bottom', 'left', 'right', 'stop']

class CoreEnv(gym.Env):
    metadata = {'render.modes':['REAL', 'CORE']}

    def __init__(self):
        # super().__init__(env)
        # self.env = env
        # self.nodes = nodes # node들에 대한 리스트
        self.__loop = asyncio.get_event_loop()
        self.action_space = CoreAction()
        self.previous_signal_quality = []

    def step(self, action):
        observation = []

        for node_action in action:
            print(node_action)
            observation.append(node_action)
            reward = None
            done = None
            info = None
        # for node_action in action:
            # node들에 대한 action을 뽑아오기
        # next_state, reward, done, info = self.env.step(action)
        ## modify ...
        return observation, reward, done, info

    def reset(self):
        self.__init__()
        self.__state = None
        self.previous_signal_quality = []

        return self.__state

    def render(self, mode='CORE', close=False, nodes=None, next_state=None):
        if close == False:
            if mode == 'CORE':
                index = 0
                self.__state = next_state
                self.previous_signal_quality = []
                for node in nodes:
                    # self.previous_signal_quality.append(node.get_signal_quality(node.))
                    if self.__state == None:
                        direction = Action['stop']
                    else:
                        direction = Action[self.__state[index]]

                    vel_x, vel_y = direction

                    self.__loop.run_until_complete(node.update_location(vel_x, vel_y)) # 100, 200이런식으로 들어가야함!
                    index = index + 1
            # elif mode == 'REAL':
            #     for node in nodes:
            #         self.__loop.run_until_complete(node.update_location(100, 200))
        else:
            print("Termination Rendering")
            return
        # Render 함수에서 각각의 node의 id, state, tentacle_state, position_x, position_y를 받아서 이 함수를 호출하여 CORE-GUI를 갱신해주게 하자!
        # __update_location() 이용!!

    def close(self):
        self.__loop = None

    def calculate_reward(self):
        return

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
        print(str(node_mac) + ", " + str(node_position_x) + ", " + str(node_position_y) + ", " + str(node_signal))
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


class CoreAction(gym.ActionWrapper):
    def __init__(self):
        self.number_of_nodes = 0

    def action(self, act):
        return act

    def sample(self, n):
        self.number_of_nodes = n
        act = []
        for i in range(n):
            choice = np.random.randint(5)
            act.append(ActionType[choice])
        return act


'''
class Observation(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)

    def observation(self, obs):
        # modify obs
        return obs


class Reward(gym.RewardWrapper):
    def __init__(self, env):
        super().__init__(env)

    def reward(self, rew):
        # modify rew
        return rew
'''
