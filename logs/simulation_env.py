from defender.defense_system import detect


class SimulationEnv:
    
    def __init__(self):
        # count steps of the simulation
        self.step_count = 0


    def step(self, action):
        """
        Executes an attack action and returns
        detection result and reward.
        """

        self.step_count += 1

        # send attack to defense system
        detection = detect(action)

        # assign reward based on detection
        if detection == "ALERT":
            reward = -1
        else:
            reward = 1

        return detection, reward
