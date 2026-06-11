import pandas as pd

df = pd.read_json("logs/attack_logs.json", lines=True)

print("\nDetection Summary:\n")

print(df.groupby("action")["detection"].value_counts())
