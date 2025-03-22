import asyncio
import signal
import sys
from config import config, validate_config
from EVELogMonitor import EVELogMonitor
from intensity_calculator import IntensityCalculator
from otc_controller import OTCController

class MainApp:
    def __init__(self):
        """初始化程序，加载配置和组件"""
        self.config = config
        try:
            validate_config(self.config)
        except ValueError as e:
            print(f"配置错误: {e}")
            sys.exit(1)
        self.intensity_calculator = IntensityCalculator(self.config)
        self.otc_controller = OTCController(self.config)
        self.log_monitor = EVELogMonitor(self.config, self.handle_event)
        self.running = True  # 控制程序运行状态

    async def start(self):
        """启动程序"""
        try:
            print("程序启动中...")
            await self.otc_controller.connect()
            self.log_monitor.start()
            await self.waveform_loop()
        except Exception as e:
            print(f"程序运行出错: {e}")
        finally:
            await self.cleanup()

    def handle_event(self, event):
        """处理日志事件"""
        try:
            self.intensity_calculator.add_event(event)
        except Exception as e:
            print(f"处理事件出错: {e}")

    async def waveform_loop(self):
        """波形输出循环"""
        current_index = 0
        while self.running:
            try:
                if self.config["waveform_enabled"]:
                    intensity = self.intensity_calculator.update_intensity()
                    if self.config["selected_patterns"]:
                        pattern_name = self.config["selected_patterns"][current_index % len(self.config["selected_patterns"])]
                        current_index += 1
                    else:
                        pattern_name = "经典"  # 默认波形
                        print("警告: 未选择波形模式，使用默认 '经典' 模式")
                    await self.otc_controller.send_waveform(intensity, self.config["ticks"], pattern_name, self.config["channel"])
                else:
                    print("波形输出已暂停")
                    await asyncio.sleep(1)  # 可根据需求调整休眠时间
            except Exception as e:
                print(f"波形循环出错: {e}")
                await asyncio.sleep(1)  # 出错时休眠，避免高频错误

    async def cleanup(self):
        """清理资源"""
        try:
            self.log_monitor.stop()
            await self.otc_controller.disconnect()
            print("资源已清理，程序退出")
        except Exception as e:
            print(f"清理资源出错: {e}")

    def stop(self):
        """停止程序"""
        self.running = False

# 捕获 Ctrl+C 信号以优雅退出
def signal_handler(signum, frame):
    print("收到终止信号，准备退出...")
    app.stop()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app = MainApp()
    asyncio.run(app.start())
