import gym
from gym import error, spaces, utils
from gym.utils import seeding

import os
import asyncio
import numpy as np

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

    def step(self, action):
        for node_action in action:
            node_action
        # for node_action in action:
            # node들에 대한 action을 뽑아오기
        # next_state, reward, done, info = self.env.step(action)
        ## modify ...
        # return next_state, reward, done, info
        return

    def reset(self):
        self.__init__()
        self.__state = None

        return self.__state

    def render(self, mode='CORE', close=False, nodes=None, next_state=None):
        if close == False:
            if mode == 'CORE':
                index = 0
                self.__state = next_state
                for node in nodes:
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
