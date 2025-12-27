import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "system.json")

with open(CONFIG_PATH, "r") as f:
    SYSTEM_CONFIG = json.load(f)
