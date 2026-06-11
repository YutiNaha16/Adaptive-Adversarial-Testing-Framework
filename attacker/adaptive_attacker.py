import random
import numpy as np


class AdaptiveAttacker:

    def __init__(self, actions):

        self.actions = actions

        # Q values for each action
        self.q_table = np.zeros(len(actions))

        # learning rate
        self.learning_rate = 0.1

        # exploration rate
        self.epsilon = 0.2


    def choose_action(self):
        """
        Choose an action using epsilon-greedy strategy
        """

        if random.random() < self.epsilon:
            return random.choice(self.actions)

        return self.actions[np.argmax(self.q_table)]


    def update(self, action, reward):
        """
        Update Q values based on reward
        """

        index = self.actions.index(action)

        self.q_table[index] = (
            self.q_table[index]
            + self.learning_rate * reward
        )
