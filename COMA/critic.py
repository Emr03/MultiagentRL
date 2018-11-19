#!/usr/bin/python3

import torch
import numpy as np
import torch.nn as nn

""" The Global, Centralized Critic. This is able to observe all states and actions and approximates the 
Q function for state, joint-action pair.

Inconsistencies are possible with the 'efficient' version of the critic, 
Use as target network (briefly mentioned in the appendix of the paper)
"""

class Critic(torch.nn.Module):
    """
    Vanilla global Q-function,
    input is joint state, joint action
    outputs the Q-value for that state-action pair
    """
    def __init__(self, input_size, hidden_size, device):

        super(Critic, self).__init__()
        self.input_size = input_size
        self.device = device

        self.mlp = nn.Sequential(
            nn.Linear( self.input_size, hidden_size),
            nn.Linear(hidden_size, hidden_size),
            nn.Linear(hidden_size, 1)
        )
        self.to(self.device)

    def forward(self, state_action):
        """
        :param state_action: joint action, global state
        :return: Q-value for the joint state
        """
        return self.mlp(state_action)

def unit_test():
    test_critic = Critic(10, 256)
    batch_size = 6
    state_action = torch.randn((batch_size, 10))
    output = test_critic.forward(state_action)
    if (output.shape == (batch_size, 1)):
        print("PASSED")

    print(output.shape)

    print(output.grad_fn)
    output.backward(torch.ones((6, 1)))
    for param in test_critic.parameters():
        print(param.grad)

if __name__ == "__main__":
    unit_test()