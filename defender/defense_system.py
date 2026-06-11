import random

# Detection probabilities for different attack actions
DETECTION_RULES = {
    "PORT_SCAN": 0.9,
    "LOGIN_ATTEMPT": 0.3,
    "PRIV_ESC": 0.8,
    "LATERAL_MOVE": 0.5,
    "FILE_ACCESS": 0.2,
    "DATA_EXFIL": 0.7
}


def detect(action):
    """
    Simulates a security defense system detecting an attack action.
    Returns ALERT if detected, otherwise NO_ALERT.
    """

    probability = DETECTION_RULES.get(action, 0.5)

    if random.random() < probability:
        return "ALERT"

    return "NO_ALERT"
