class IntensityCalculator:
    def __init__(self, config):
        self.config = config
        self.base_intensity = config.get("base_intensity", 0)
        self.current_intensity = self.base_intensity
        self.max_intensity_a = config.get("A_max", 30)
        self.max_intensity_b = config.get("B_max", 30)
        self.app_max_intensity = config.get("app_max_intensity", 30)
        self.events = []
        self.total_increment = 0
        self.total_decrement = 0
        self.decay_rate = 0.9  # 每次更新时衰减 10%

    def add_event(self, event):
        try:
            if not isinstance(event, dict) or 'type' not in event or 'subtype' not in event:
                print(f"无效的事件格式: {event}")
                return
            self.events.append(event)
            # 重置单次增量和减量，只基于当前事件计算
            increment = 0
            decrement = 0
            if event["type"] == "damage" and event["subtype"] in self.config["monitored_damage_types"]:
                increment = self.config.get("damage_types", {}).get(event["subtype"], 0)
                increment = min(99, increment)  # 限制单次增量不超过 99
                print(f"强度增加: {event['subtype']} (+{increment})")
            elif event["type"] == "player_attack" and event["subtype"] in self.config["monitored_reward_types"]:
                decrement = self.config.get("reward_types", {}).get(event["subtype"], 0)
                decrement = min(99, decrement)  # 限制单次减量不超过 99
                print(f"强度减少: {event['subtype']} (-{decrement})")

            # 累加本次事件的增量和减量，并应用衰减
            self.total_increment = min(99, max(0, self.total_increment * self.decay_rate + increment))
            self.total_decrement = min(99, max(0, self.total_decrement * self.decay_rate + decrement))
            self.update_intensity()
        except Exception as e:
            print(f"处理事件时出错: {e}")

    def update_intensity(self):
        try:
            # 计算当前强度，确保不小于 0
            raw_intensity = self.base_intensity + self.total_increment - self.total_decrement
            self.current_intensity = max(0, min(raw_intensity, self.app_max_intensity))  # 限制在 [0, app_max_intensity]
            print(
                f"计算强度: 基础={self.base_intensity}, 增量={self.total_increment:.1f}, 减量={self.total_decrement:.1f}, 总和={self.current_intensity}")
            return self.current_intensity
        except Exception as e:
            print(f"更新强度时出错: {e}")
            return self.current_intensity

    def reset(self):
        try:
            self.current_intensity = self.base_intensity
            self.total_increment = 0
            self.total_decrement = 0
            self.events = []
        except Exception as e:
            print(f"重置时出错: {e}")
