#实时监控 EVE Online 的游戏日志文件，解析攻击事件。
import os
import time
import re
import threading

class EVELogMonitor:
    def __init__(self, config, callback):
        self.config = config
        self.callback = callback
        self.running = False
        self.thread = None

    def find_latest_log_file(self):
        log_dir = self.config["log_dir"]
        if not os.path.exists(log_dir):
            print(f"日志目录不存在: {log_dir}")
            return None
        log_files = [f for f in os.listdir(log_dir) if f.endswith(".txt")]
        if not log_files:
            print(f"未找到日志文件在: {log_dir}")
            return None
        latest_file = max(log_files, key=lambda f: os.path.getctime(os.path.join(log_dir, f)))
        return os.path.join(log_dir, latest_file)

    def start(self, log_file):
        self.running = True
        self.thread = threading.Thread(target=self._monitor, args=(log_file,), daemon=True)
        self.thread.start()
        print(f"开始监控日志文件: {log_file}")

    def _monitor(self, log_file):
        last_position = 0
        with open(log_file, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)
            last_position = f.tell()
        while self.running:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()
                    for line in new_lines:
                        event = self.parse_line(line)
                        if event:
                            print(f"解析到事件: {event}")
                            self.callback(event)
            except Exception as e:
                print(f"读取日志文件时出错: {e}")
            time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("日志监控已停止")

    def parse_line(self, line):
        line = line.strip()
        if "(combat)" not in line.lower():
            return None

        attack_patterns = {
            "强力一击": r"(强力一击|Critical Hit)",
            "命中": r"(命中|Hit)",
            "穿透": r"(穿透|Penetrates)",
            "擦过": r"(擦过|Glances)",
            "轻轻擦过": r"(轻轻擦过|Lightly Hits)",
            "完全没有打中你": r"(完全没有打中你|Misses Completely)",
            "致命一击": r"(致命一击|Wrecks)"
        }

        for attack_type, pattern in attack_patterns.items():
            match = re.search(r"<color=0xff00ffff>.*?<font size=10>对</font>.*?- " + pattern, line, re.IGNORECASE)
            if match and attack_type in self.config["monitored_reward_types"]:
                return {"type": "player_attack", "subtype": attack_type}

            match = re.search(r"<color=0xffcc0000>.*?<font size=10>来自</font>.*?- " + pattern, line, re.IGNORECASE)
            if match and attack_type in self.config["monitored_damage_types"]:
                return {"type": "damage", "subtype": attack_type}

        if "完全没有打中你" in line and "完全没有打中你" in self.config["monitored_damage_types"]:
            return {"type": "damage", "subtype": "完全没有打中你"}

        if "你的" in line and "完全没有打中" in line and "完全没有打中你" in self.config["monitored_reward_types"]:
            return {"type": "player_attack", "subtype": "完全没有打中你"}

        return None
