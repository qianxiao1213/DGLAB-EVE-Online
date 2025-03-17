import asyncio
import json
import websockets

class OTCController:
    def __init__(self, config):
        self.config = config
        self.websocket = None

    async def connect(self, retries=3, delay=2, log_callback=None):
        for attempt in range(retries):
            msg = f"尝试连接 ({attempt + 1}/{retries}): {self.config['ws']}"
            if log_callback:
                log_callback(msg)
            print(msg)
            try:
                self.websocket = await asyncio.wait_for(websockets.connect(self.config["ws"]), timeout=5)
                success_msg = "WebSocket 连接成功"
                if log_callback:
                    log_callback(success_msg)
                print(success_msg)
                return True
            except Exception as e:
                error_msg = f"WebSocket 连接失败: {e}"
                if log_callback:
                    log_callback(error_msg)
                print(error_msg)
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
        final_msg = "所有连接尝试均失败，请检查地址或服务器状态"
        if log_callback:
            log_callback(final_msg)
        print(final_msg)
        return False

    async def send_waveform(self, intensity, ticks, pattern_name, channel):
        if not self.websocket:
            print("WebSocket 未连接")
            return

        app_max = self.config["app_max_intensity"]  # 例如40
        intensity_percent = min((intensity / app_max) * 100, 100)  # 转换为百分比，例如75%
        actual_intensity = min(intensity, app_max)  # 实际强度，用于日志显示

        if channel == "both":
            cmd = {
                "cmd": "set_pattern",
                "A_pattern_name": pattern_name,
                "B_pattern_name": pattern_name,
                "A_intensity": int(intensity_percent),  # 直接发送百分比值
                "B_intensity": int(intensity_percent),
                "A_ticks": ticks,
                "B_ticks": ticks
            }
        else:
            cmd = {
                "cmd": "set_pattern",
                f"{channel}_pattern_name": pattern_name,
                f"{channel}_intensity": int(intensity_percent),  # 直接发送百分比值
                f"{channel}_ticks": ticks
            }

        await self.websocket.send(json.dumps(cmd))
        print(f"发送指令: {cmd}, 实际强度={actual_intensity}, 百分比={intensity_percent:.1f}%")

    async def get_max_intensity(self):
        if not self.websocket:
            print("WebSocket 未连接")
            return

        request = {"cmd": "get_max_intensity"}
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        data = json.loads(response)
        if data.get("type") == "max_intensity":
            self.config["A_max"] = data.get("A_max", 30)
            self.config["B_max"] = data.get("B_max", 30)
            if self.config["channel"] == "A":
                self.config["app_max_intensity"] = self.config["A_max"]
            elif self.config["channel"] == "B":
                self.config["app_max_intensity"] = self.config["B_max"]
            else:  # "both"
                self.config["app_max_intensity"] = min(self.config["A_max"], self.config["B_max"])
            print(f"获取到 App 上限: A_max={self.config['A_max']}, B_max={self.config['B_max']}, 选择: {self.config['app_max_intensity']}")
        else:
            print("未获取到有效的上限，使用默认值: A_max=30, B_max=30")
            self.config["A_max"] = 30
            self.config["B_max"] = 30
            self.config["app_max_intensity"] = self.config["A_max"] if self.config["channel"] == "A" else self.config["B_max"]
