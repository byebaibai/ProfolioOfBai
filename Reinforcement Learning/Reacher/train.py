import collections

import numpy as np
from unityagents import UnityEnvironment

from agent import *
from config import *


def train(agent, env, n_episodes=30000, max_t=10000):
    # get the default brain
    brain_name = env.brain_names[0]

    scores = []  # list containing scores from each episode
    scores_window = collections.deque(maxlen=100)  # last 100 scores

    for i_episode in range(1, 1 + n_episodes):
        env_info = env.reset(train_mode=True)[brain_name]
        state = env_info.vector_observations[0]
        score = 0

        for i in range(max_t):
            action = agent.act(state)
            env_info = env.step(action)[brain_name]
            next_state = env_info.vector_observations[0]
            reward = env_info.rewards[0]
            done = env_info.local_done[0]
            agent.step(state, action, reward, next_state, done)
            score += reward
            state = next_state
            if (done):
                break
        for _ in range(args.update_iteration):
            agent.learn()
        scores_window.append(score)
        scores.append(score)
        print('\rEpisode {}\tMean Score: {:.2f}'.format(i_episode, np.mean(scores_window)), end="")
        if i_episode % 100 == 0:
            print('\rEpisode {}\tMean Score: {:.2f}'.format(i_episode, np.mean(scores_window)))
        if np.mean(scores_window) >= 30.0:
            print('\nEnvironment solved in {:d} episodes!\tMean Score: {:.2f}'.format(i_episode - 100,
                                                                                      np.mean(scores_window)))
            np.save('scores_{}.npy'.format( i_episode - 100), np.array(scores))
            agent.save('actor_checkpoint_{}.pth'.format(i_episode - 100),'critic_checkpoint_{}.pth'.format(i_episode - 100))
            break
    print('TRAIN DONE!')
if __name__ == '__main__':
    env = UnityEnvironment(file_name=args.unity)

    agent = Agent(33,4,1)

    train(agent, env)