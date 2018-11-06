"""
Train agents for particle environment using COMA
"""
from comet_ml import Experiment
from coma import COMA
import marl_env
import torch
import time
import numpy as np
import matplotlib.pyplot as plt

def gather_rollouts(coma, eps):
    """
    gathers rollouts under the current policy
    :param coma: instance of COMA model
    :param eps:
    :return:
    """
    # Step 1: generate batch_size rollouts
    for i in range(coma.params['batch_size']):

        # initialize action to noop
        joint_action = torch.zeros((coma.n_agents, coma.action_size))
        joint_action[:, 0] = 1
        coma.env.reset()

        for t in range(coma.params['seq_len']):

            # get observations, by executing current joint action
            obs_n, reward_n, done_n, info_n = coma.env.step(joint_action)

            # they all get the same reward, save the reward
            coma.reward_seq_pl[i, t] = reward_n[0]

            # save the joint action for training
            coma.joint_action_pl[i, t, :] = joint_action.flatten()

            # for each agent, save observation, compute next action
            for n in range(coma.n_agents):
                # one-hot agent index
                agent_idx = np.zeros(coma.n_agents)
                agent_idx[n] = 1

                # use the observation to construct global state
                # the global state consists of positions + velocity of agents, first 4 elements from obs
                coma.global_state_pl[i, t, n * 4:4 * n + 4] = torch.from_numpy(obs_n[n][0:4])

                # get distribution over actions, concatenate observation and prev action
                obs_action = np.concatenate((obs_n[n][0:coma.obs_size], joint_action[n, :], agent_idx))
                actor_input = torch.from_numpy(obs_action).view(1, 1, -1).type(torch.FloatTensor)

                # save the actor input for training
                coma.actor_input_pl[n][i, t, :] = actor_input

                pi = coma.actor.forward(actor_input, eps)

                # sample action from pi, convert to one-hot vector
                action_idx = (torch.multinomial(pi[0, 0, :], num_samples=1)).numpy()
                action = torch.zeros(coma.action_size)
                action[action_idx] = 1
                joint_action[n, :] = action

            # get the absolute landmark positions for the global state
            coma.global_state_pl[i, t, coma.n_agents * 4:] = torch.from_numpy(np.array(
                [landmark.state.p_pos for landmark in coma.env.world.landmarks]).flatten())

    # concatenate the joint action, global state, set network inputs to torch tensors
    coma.joint_action_state_pl = torch.cat((coma.joint_action_pl, coma.global_state_pl), dim=-1)

    coma.joint_action_state_pl.requires_grad_(True)
    # print the reward at the last timestep
    # print('reward', np.mean(np.sum(coma.reward_seq_pl, axis=1)))
    coma.metrics['mean_reward'] = np.mean(np.sum(coma.reward_seq_pl, axis=1))

def visualize(coma):

    joint_action = torch.zeros((coma.n_agents, coma.action_size))
    joint_action[:, 0] = 1
    coma.env.reset()

    for t in range(coma.params['seq_len']):
        coma.env.render()
        time.sleep(0.25)
        # get observations
        obs_n, reward_n, done_n, info_n = env.step(joint_action)

        # reset the joint action, one-hot representation
        joint_action = np.zeros((coma.n_agents, coma.action_size))

        # for each agent, save observation, compute next action
        for n in range(coma.n_agents):
            # one-hot agent index
            agent_idx = np.zeros(coma.n_agents)
            agent_idx[n] = 1

            # get distribution over actions
            obs_action = np.concatenate((obs_n[n][0:coma.obs_size], joint_action[n, :], agent_idx))
            actor_input = torch.from_numpy(obs_action).view(1, 1, -1).type(torch.FloatTensor)

            pi = coma.actor.forward(actor_input, eps=0)

            # sample action from pi, convert to one-hot vector
            action_idx = (torch.multinomial(pi[0, 0, :], num_samples=1)).numpy()
            action = np.zeros(coma.action_size)
            action[action_idx] = 1
            joint_action[n, :] = action

if __name__ == "__main__":

    env = marl_env.make_env('simple_spread')

    n_agents = 3
    n_landmarks = 3

    coma = COMA(env=env, batch_size=50, seq_len=20, discount=0.9, n_agents=2, action_size=5, obs_size=9,
                     state_size=12, h_size=128)

    experiment = Experiment(api_key='1jl4lQOnJsVdZR6oekS6WO5FI', project_name="COMA", \
                                auto_param_logging=False, auto_metric_logging=False,
                                log_graph=False, log_env_details=False, parse_args=False,
                                auto_output_logging=False)
    experiment.log_multiple_params(coma.params)
    #

    # visualize(coma)
    try:
        for e in range(400):
            if e % 20 == 0:
                print('e', e)
                coma.update_target()


            gather_rollouts(coma, eps=max(0.5 - e*0.00005, 0.05))

            coma.fit_critic(lam=0.5)
            coma.fit_actor(eps=max(0.5 - e*0.00005, 0.05))

            print("reward: {0:5.2f}, actor loss: {1:5.2f}, critic loss: {2:5.2f}".format(
                coma.metrics['mean_reward'],
                coma.metrics['mean_actor_loss'],
                coma.metrics['mean_critic_loss']))

            experiment.set_step(e)
            experiment.log_multiple_metrics(coma.metrics)
    except KeyboardInterrupt:
        pass
    # finally:
    #     plt.plot(coma.metrics['mean_reward'], 'b')
    #     plt.plot(coma.metrics['mean_actor_loss'], 'g')
    #     plt.plot(coma.metrics['mean_critic_loss'], 'r')
    #     plt.show()
    #     visualize(coma)





