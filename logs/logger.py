kimport json

LOG_FILE = "logs/attack_logs.json"

def log_event(step, action, detection, reward):

    event = {
        "step": step,
        "action": action,
        "detection": detection,
        "reward": reward
    }

    with open(LOG_FILE, "a") as f:
        json.dump(event, f)
        f.write("\n")
