from gym.envs.registration import register

register(
    id='core-v0',
    entry_point='gym_core.envs:CoreEnv',
)
