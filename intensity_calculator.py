import time

class IntensityCalculator:
    def __init__(self, config):
        self.config = config
        self.current_intensity = config["base_intensity"]
        self.damage_buffer = []
        self.attack_buffer = []
        self.special_buffer = []
        self.last_update_time = time.time()

    def add_event(self, event):
        print(f"收到事件: {event}")
        if event["type"] == "damage" and event["subtype"] in self.config["monitored_damage_types"]:
            self.damage_buffer.append(event["subtype"])

    def update_intensity(self):
        current_time = time.time()
        if current_time - self.last_update_time >= 1:
            if self.damage_buffer:
                damage_increase = sum(
                    self.config["damage_types"].get(dt, 0)
                    for dt in self.damage_buffer
                )
                print(f"计算强度增加: {damage_increase}, 当前缓冲区: {self.damage_buffer}")
                self.current_intensity = self.config["base_intensity"] + damage_increase
                self.current_intensity = max(self.config["min_intensity"],
                                           min(self.current_intensity, 100))
                self.damage_buffer.clear()
            else:
                self.current_intensity = self.config["base_intensity"]
                print("无新事件，恢复基础强度")
            self.last_update_time = current_time
        return int(self.current_intensity)
