# main.py 主程序，集成所有模块并运行

import asyncio
from config import config
from log_monitor import EVELogMonitor
from intensity_calculator import IntensityCalculator
from otc_controller import OTCController

class MainApp:
    def __init__(self):
        self.config = config
        self.intensity_calculator = IntensityCalculator(self.config)
        self.otc_controller = OTCController(self.config)
        self.log_monitor = EVELogMonitor(self.config, self.handle_event)

    async def start(self):
        """启动程序"""
        await self.otc_controller.connect()
        self.log_monitor.start()
        await self.waveform_loop()

    def handle_event(self, event):
        """处理日志事件"""
        self.intensity_calculator.add_event(event)

    async def waveform_loop(self):
        """波形输出循环"""
        current_index = 0
        while True:
            if self.config["waveform_enabled"]:
                intensity = self.intensity_calculator.update_intensity()
                if self.config["selected_patterns"]:
                    pattern_name = self.config["selected_patterns"][current_index % len(self.config["selected_patterns"])]
                    current_index += 1
                else:
                    pattern_name = "经典"  # 默认波形
                await self.otc_controller.send_waveform(intensity, self.config["ticks"], pattern_name, self.config["channel"])
            else:
                print("波形输出已暂停")
                await asyncio.sleep(1)

if __name__ == "__main__":
    app = MainApp()
    asyncio.run(app.start())