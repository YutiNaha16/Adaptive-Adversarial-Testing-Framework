from defender.defense_system import detect


class SimulationEnv:

    def __init__(self):
        self.step_count = 0


    def step(self, action):

        self.step_count += 1

        detection = detect(action)

        if detection == "ALERT":
            reward = -1
        else:
            reward = 1

        return detection, reward
