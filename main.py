from attacker.adaptive_attacker import AdaptiveAttacker
from environment.simulation_env import SimulationEnv
from environment.actions import ACTIONS


def run_simulation():

    env = SimulationEnv()
    attacker = AdaptiveAttacker(ACTIONS)

    episodes = 1000

    for episode in range(episodes):

        action = attacker.choose_action()

        detection, reward = env.step(action)

        attacker.update(action, reward)

        print(
            f"Step {episode} | Action: {action} | Detection: {detection} | Reward: {reward}"
        )


if __name__ == "__main__":
    run_simulation()
