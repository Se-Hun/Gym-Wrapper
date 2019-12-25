import gym
import gym_core

from BioAIR.Drones.Node import Node
import os

Node_list = []

if __name__ == "__main__":
    # generate Node object
    origin = Node(0, os.getcwd() + '/config_origin.ini', 'simple_test4')
    destination = Node(0, os.getcwd() + '/config_destination.ini', 'simple_test4')
    node1 = Node(0, os.getcwd() + '/config_drone1.ini', 'simple_test4')
    node2 = Node(0, os.getcwd() + '/config_drone2.ini', 'simple_test4')

    Node_list.append(origin)
    Node_list.append(destination)
    Node_list.append(node1)
    Node_list.append(node2)

    # Each drone has their own node object and run.
    # origin.run(0)
    # destination.run(0)
    # node1.run(0)
    # node2.run(0)

    # Running Gym-Wrapper
    env = gym.make('core-v0')
    for i_episode in range(20):
        observation = env.reset()
        for t in range(100):
            env.render(nodes=Node_list)
            print(observation)
            action = env.action_space.sample()
            observation, reward, done, info = env.step(action)
            if done:
                print("Episode finished after {} timesteps".format(t+1))
                break;
    env.close()
