import gym
from gym import error, spaces, utils
from gym.utils import seeding

import os
import asyncio
import numpy as np

### Action Type
Action = {
    'top' : (0, -5), # 상
    'bottom' : (0, 5), # 하
    'left' : (-5, 0), # 좌
    'right' : (5, 0), # 우
    'stop' : (0, 0) # 정지
}
ActionType = ['top', 'bottom', 'left', 'right', 'stop']

class CoreEnv(gym.Env):
    metadata = {'render.modes':['REAL', 'CORE']}

    def __init__(self):
        self.__loop = asyncio.get_event_loop()
        self.action_space = CoreAction()
        self.prev_signal_quality = []
        self.signal_quality = []

    def step(self, action):
        observation = []
        reward = []
        done = False
        info = {} # 사용하지 않음

        index = 0
        for node_action in action:
            # For Observation
            observation.append(node_action)

            # For Reward and Done
            if not self.prev_signal_quality:
                reward.append(0)
            elif not self.signal_quality:
                reward.append(0)
            else:
                reward.append(self.__calculate_reward(self.prev_signal_quality[index], self.signal_quality[index]))
                done = self.__checkDone(self.prev_signal_quality[index], self.signal_quality[index])

            index = index + 1

        return observation, reward, done, info

    def reset(self):
        self.__init__()
        self.__state = None

        return self.__state

    def render(self, mode='CORE', close=False, nodes=None, next_state=None):
        if close == False:
            if mode == 'CORE':
                index = 0
                self.__state = next_state
                self.prev_signal_quality = self.signal_quality
                self.signal_quality = []
                for node in nodes:
                    self.signal_quality.append(node.get_signal_quality_dict())
                    print(self.signal_quality)
                    if self.__state == None:
                        direction = Action['stop']
                    else:
                        direction = Action[self.__state[index]]

                    vel_x, vel_y = direction

                    self.__loop.run_until_complete(node.update_location(vel_x, vel_y)) # 100, 200이런식으로 들어가야함!
                    index = index + 1
        else:
            print("Termination Rendering")
            return

    def close(self):
        self.__loop = None

    def __calculate_reward(self, prev, signal):
        key_list = list(prev.keys())
        reward = 0

        for key in key_list:
            if prev[key] >= signal[key]:
                reward = reward + 1
            else:
                reward = reward - 1

        return reward

    def __checkDone(self, prev, signal):
        key_list = list(prev.keys())
        number_of_nodes = len(key_list)
        done_count = 0

        for key in key_list:
            if (signal[key] > 0) and (prev[key] == signal[key]):
                done_count = done_count + 1

        if done_count == number_of_nodes:
            return True

        return False


class CoreAction(gym.ActionWrapper):
    def __init__(self):
        self.number_of_nodes = 0

    def action(self, act):
        return act

    def sample(self, n, reward, prev_action):
        self.number_of_nodes = n
        act = []
        for i in range(n):
            if reward[i] > 0:
                act.append(prev_action[i])
            else:
                choice = np.random.randint(5)
                act.append(ActionType[choice])
        return act
