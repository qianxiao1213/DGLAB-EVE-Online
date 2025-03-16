import json
import os
import sys

CONFIG_FILE = "otc_config.json"

def get_resource_path(relative_path):
    """获取打包后的资源路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def load_config():
    default_config = {
        "ws": "ws://192.168.8.129:60536/1",
        "log_dir": r"C:\Users\用户名\Documents\EVE\logs\Gamelogs",
        "listener_id": "你的ID",
        "base_intensity": 30,
        "app_max_intensity": 30,
        "A_max": 30,
        "B_max": 30,
        "damage_types": {
            "强力一击": 10, "命中": 8, "穿透": 10, "擦过": 5, "轻轻擦过": 5, "完全没有打中你": 5
        },
        "monitored_damage_types": ["强力一击", "命中", "穿透", "擦过", "轻轻擦过", "完全没有打中你"],
        "selected_patterns": ["经典"],
        "waveform_enabled": False,
        "min_intensity": 0,
        "max_intensity": 50,
        "channel": "both",
        "ticks": 10,
        "history_ids": []
    }
    config_path = get_resource_path(CONFIG_FILE)
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
            default_config.update(loaded_config)
    return default_config

def save_config(config):
    config_path = get_resource_path(CONFIG_FILE)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
