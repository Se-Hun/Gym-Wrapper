import gym
from gym import error, spaces, utils
from gym.utils import seeding

import os
import asyncio

class CoreEnv(gym.Env):
    metadata = {'render.modes':['human', 'CORE']}

    def __init__(self):
        # super().__init__(env)
        # self.env = env
        # self.nodes = nodes # node들에 대한 리스트
        self.__loop = asyncio.get_event_loop()

    def step(self, action):
        # for node_action in action:
            # node들에 대한 action을 뽑아오기
        # next_state, reward, done, info = self.env.step(action)
        ## modify ...
        # return next_state, reward, done, info
        return

    def reset(self):
        return

    def render(self, mode='CORE', close=False, nodes=None):
        if close == False:
            if mode == 'CORE':
                for node in nodes:
                    print(node)
                    self.__loop.run_until_complete(node.update_location(100, 200))
        else:
            return
        # Render 함수에서 각각의 node의 id, state, tentacle_state, position_x, position_y를 받아서 이 함수를 호출하여 CORE-GUI를 갱신해주게 하자!
        # __update_location() 이용!!
