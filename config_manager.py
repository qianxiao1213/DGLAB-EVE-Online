import json
import os
from config import validate_config

CONFIG_FILE = "otc_config.json"

def load_config():
    default_config = {
        "ws": "ws://192.168.8.129:60536/1",
        "log_dir": os.path.expanduser(r"~\Documents\EVE\logs\Gamelogs"),  # 动态获取用户目录
        "listener_id": "YOUR_LISTENER_ID",  # 请替换为实际ID
        "base_intensity": 20,
        "app_max_intensity": 30,
        "A_max": 30,
        "B_max": 30,
        "damage_types": {
            "强力一击": 10, "命中": 8, "穿透": 10, "擦过": 5, "轻轻擦过": 5, "完全没有打中你": 5
        },
        "reward_types": {
            "强力一击": 10, "命中": 8, "穿透": 10, "擦过": 5, "轻轻擦过": 5, "完全没有打中你": 5
        },
        "monitored_damage_types": ["强力一击", "命中", "穿透", "擦过", "轻轻擦过", "完全没有打中你"],
        "monitored_reward_types": ["强力一击", "命中", "穿透"],
        "selected_patterns": ["经典"],
        "waveform_enabled": False,
        "min_intensity": 0,
        "max_intensity": 30,
        "channel": "both",
        "ticks": 10,
        "history_ids": []
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
    except Exception as e:
        print(f"加载配置失败: {e}")
    validate_config(default_config)  # 验证配置
    return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存配置失败: {e}")
