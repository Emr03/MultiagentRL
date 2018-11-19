from comet_ml import Experiment
import torch
import numpy as np
import multiprocessing

class BaseModel:

    def __init__(self, use_gpu=True, track_results=True):
        """
        Initializes comet tracking and cuda gpu
        """
        super().__init__()
        self.experiment = Experiment(api_key='1jl4lQOnJsVdZR6oekS6WO5FI', project_name=self.__class__.__name__,
                                     auto_param_logging=False, auto_metric_logging=False,
                                     disabled=track_results)
        self.use_gpu = use_gpu

        self.device = torch.device('cuda:0' if torch.cuda.is_available() and use_gpu else 'cpu')
        self.params = {}

    def set_params(self):
        """
        Create parameter dictionary from necessary parameters and logs them to comet.
        Requires that model has initialized these necessary parameters i.e. run this at the end of the init
        """
        self.params.update({
            "num_agents": self.n_agents,
            "batch_size": self.batch_size,
            "seq_len": self.seq_len,
            "discount": self.discount,
            "n_agents": self.env.n,
            "h_size": self.h_size,
            "lr_critic": self.lr_critic,
            "lr_actor": self.lr_actor,
        })
        self.experiment.log_multiple_params(self.params)

    def gather_batch(self):
        """
        Fills data buffer with (o, o', s, s', a, r) tuples generated from simulating environment
        """
        count = 0
        rewards = []
        while count < self.batch_size:
            # initialize action to noop
            actions = torch.zeros(self.n_agents, self.env.action_size)
            actions[:, 0] = 1
            np.random.seed()
            curr_agent_obs, curr_global_state, reward = self.env.reset()

            for t in range(self.seq_len):
                # for each agent, save observation, compute next action
                for n in range(self.n_agents):
                    pi = self.policy(curr_agent_obs[n], actions[n, :], n).cpu()
                    # sample action from pi, convert to one-hot vector
                    action_idx = torch.multinomial(pi, num_samples=1)
                    actions[n, :] = torch.zeros(self.action_size).scatter(0, action_idx, 1)

                # get observations, by executing current joint action
                # TODO add parallelism
                next_agent_obs, next_global_state, reward = self.env.step(actions)
                self.buffer.add_to_buffer(t, curr_agent_obs, next_agent_obs, curr_global_state, next_global_state,
                                           actions, reward)
                curr_agent_obs, curr_global_state = next_agent_obs, next_global_state
                rewards.append(reward)

            count += self.seq_len
        print("Mean reward for this batch: {0:10.3}".format(np.mean(rewards)))
        return np.mean(rewards)

    def train(self):
        """
        Train model
        """
        metrics = {}
        for e in range(self.epochs):
            metrics["Reward"] = self.gather_batch()
            metrics["Critic Loss"], metrics["Agent Loss"] = self.update(e)

            self.experiment.log_multiple_metrics(metrics)
            self.experiment.set_step(e)
