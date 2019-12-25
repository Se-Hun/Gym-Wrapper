import gym
from gym import error, spaces, utils
from gym.utils import seeding

class CoreEnv(gym.Env):
    metadata = {'render.modes':['human']}

    def __init__(self, env):
        super().__init__(env)
        self.env = env

    def step(self, action):
        next_state, reward, done, info = self.env.step(action)
        ## modify ...
        return next_state, reward, done, info

    def reset(self):
        ##
    def render(self, mode='human', close=False):
        ##

