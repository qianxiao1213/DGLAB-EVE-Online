# 程序主界面
import sys
import asyncio
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QComboBox, QListWidget,
                             QTextEdit, QLabel, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread
from qasync import QEventLoop, asyncSlot
from config_manager import load_config, save_config
from log_monitor import EVELogMonitor
from intensity_calculator import IntensityCalculator
from otc_controller import OTCController

class LogMonitorThread(QThread):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.monitor_file = None

    def run(self):
        if self.monitor_file:
            self.monitor.start(self.monitor_file)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EVE Online OTC 控制器")
        self.setGeometry(100, 100, 800, 900)

        self.config = load_config()
        self.intensity_calculator = IntensityCalculator(self.config)
        self.otc_controller = OTCController(self.config)
        self.log_monitor = EVELogMonitor(self.config, self.handle_event)
        self.log_thread = None
        self.running = False

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # WebSocket 地址
        ws_layout = QHBoxLayout()
        ws_layout.addWidget(QLabel("WebSocket 地址:"))
        self.ws_input = QLineEdit(self.config["ws"].replace("ws://", "").replace(":60536/1", ""))
        self.ws_input.textChanged.connect(self.update_config)  # 文本改变时更新配置
        ws_layout.addWidget(self.ws_input)
        self.connect_button = QPushButton("连接 OTC")
        self.connect_button.clicked.connect(self.connect_otc)
        ws_layout.addWidget(self.connect_button)
        self.disconnect_button = QPushButton("断开 OTC")
        self.disconnect_button.clicked.connect(self.disconnect_otc)
        self.disconnect_button.setEnabled(False)
        ws_layout.addWidget(self.disconnect_button)
        layout.addLayout(ws_layout)

        # 日志目录
        layout.addWidget(QLabel("日志目录:"))
        self.log_dir_input = QLineEdit(self.config["log_dir"])
        self.log_dir_input.textChanged.connect(self.update_config)
        layout.addWidget(self.log_dir_input)

        # 游戏ID
        layout.addWidget(QLabel("游戏ID:"))
        self.listener_id_input = QComboBox()
        self.listener_id_input.setEditable(True)
        for id in self.config["history_ids"]:
            self.listener_id_input.addItem(id)
        self.listener_id_input.setCurrentText(self.config["listener_id"])
        self.listener_id_input.currentTextChanged.connect(self.update_config)
        layout.addWidget(self.listener_id_input)

        # 基础强度
        layout.addWidget(QLabel("基础强度 (%):"))
        self.base_intensity_input = QLineEdit(str(self.config["base_intensity"]))
        self.base_intensity_input.textChanged.connect(self.update_base_intensity)
        layout.addWidget(self.base_intensity_input)

        # App 强度上限
        self.app_max_label = QLabel(f"App 强度上限: {self.config['app_max_intensity']}")
        layout.addWidget(self.app_max_label)

        # A 和 B 基础强度
        self.base_intensity_a_label = QLabel(f"A 基础强度: {self.config['base_intensity']}")
        layout.addWidget(self.base_intensity_a_label)
        self.base_intensity_b_label = QLabel(f"B 基础强度: {self.config['base_intensity']}")
        layout.addWidget(self.base_intensity_b_label)

        # A 和 B 动态强度
        self.dynamic_intensity_a_label = QLabel(f"A 动态强度: {self.config['base_intensity']}%")
        layout.addWidget(self.dynamic_intensity_a_label)
        self.dynamic_intensity_b_label = QLabel(f"B 动态强度: {self.config['base_intensity']}%")
        layout.addWidget(self.dynamic_intensity_b_label)

        # 选择监控的攻击类型
        layout.addWidget(QLabel("选择监控的攻击类型:"))
        self.damage_types_list = QListWidget()
        for dt in self.config["damage_types"]:
            item = self.damage_types_list.addItem(dt)
            self.damage_types_list.item(self.damage_types_list.count() - 1).setCheckState(
                Qt.Checked if dt in self.config["monitored_damage_types"] else Qt.Unchecked
            )
        self.damage_types_list.itemChanged.connect(self.update_config)
        layout.addWidget(self.damage_types_list)

        # 调整攻击类型强度
        layout.addWidget(QLabel("调整攻击类型强度:"))
        self.damage_intensity_inputs = {}
        for dt in self.config["damage_types"]:
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(f"{dt}:"))
            input = QLineEdit(str(self.config["damage_types"][dt]))
            input.textChanged.connect(lambda text, key=dt: self.update_damage_intensity(key, text))
            self.damage_intensity_inputs[dt] = input
            hbox.addWidget(input)
            layout.addLayout(hbox)

        # 选择波形
        layout.addWidget(QLabel("选择波形:"))
        self.patterns_list = QListWidget()
        patterns = ["经典", "冲击", "炼狱2.0", "打屁股", "固定波形0", "固定波形1", "固定波形2",
                    "固定波形3", "固定波形4", "固定波形5", "固定波形6", "固定波形7",
                    "固定波形8", "固定波形9", "固定波形10"]
        for p in patterns:
            item = self.patterns_list.addItem(p)
            self.patterns_list.item(self.patterns_list.count() - 1).setCheckState(
                Qt.Checked if p in self.config["selected_patterns"] else Qt.Unchecked
            )
        self.patterns_list.itemChanged.connect(self.update_config)
        layout.addWidget(self.patterns_list)

        # 通道选择
        layout.addWidget(QLabel("通道选择:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["both", "A", "B"])
        self.channel_combo.setCurrentText(self.config["channel"])
        self.channel_combo.currentTextChanged.connect(self.update_channel)
        layout.addWidget(self.channel_combo)

        # 日志输出
        layout.addWidget(QLabel("日志输出:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # 波形发送日志
        layout.addWidget(QLabel("波形发送日志:"))
        self.waveform_log = QTextEdit()
        self.waveform_log.setReadOnly(True)
        layout.addWidget(self.waveform_log)

        # 启动和关闭按钮
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("启动程序")
        self.start_button.clicked.connect(self.start_program)
        buttons_layout.addWidget(self.start_button)
        self.stop_button = QPushButton("关闭程序")
        self.stop_button.clicked.connect(self.stop_program)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)
        layout.addLayout(buttons_layout)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("程序初始化完成")

    def update_config(self):
        """通用配置更新函数"""
        try:
            self.config["ws"] = f"ws://{self.ws_input.text().strip()}:60536/1"
            self.config["log_dir"] = self.log_dir_input.text().strip()
            self.config["listener_id"] = self.listener_id_input.currentText().strip()
            if self.config["listener_id"] and self.config["listener_id"] not in self.config["history_ids"]:
                self.config["history_ids"].insert(0, self.config["listener_id"])
                self.listener_id_input.addItem(self.config["listener_id"])

            self.config["monitored_damage_types"] = [
                self.damage_types_list.item(i).text()
                for i in range(self.damage_types_list.count())
                if self.damage_types_list.item(i).checkState() == Qt.Checked
            ]
            self.config["selected_patterns"] = [
                self.patterns_list.item(i).text()
                for i in range(self.patterns_list.count())
                if self.patterns_list.item(i).checkState() == Qt.Checked
            ]
            save_config(self.config)  # 自动保存
            self.status_bar.showMessage("配置已自动更新并保存")
        except Exception as e:
            self.status_bar.showMessage(f"配置更新失败: {e}")

    def update_base_intensity(self, text):
        """更新基础强度"""
        try:
            intensity = int(text)
            self.config["base_intensity"] = intensity
            self.intensity_calculator.current_intensity = intensity
            self.base_intensity_a_label.setText(f"A 基础强度: {intensity}")
            self.base_intensity_b_label.setText(f"B 基础强度: {intensity}")
            self.dynamic_intensity_a_label.setText(f"A 动态强度: {intensity}%")
            self.dynamic_intensity_b_label.setText(f"B 动态强度: {intensity}%")
            self.validate_base_intensity()
            save_config(self.config)
            self.status_bar.showMessage("基础强度已更新并保存")
        except ValueError:
            self.status_bar.showMessage("基础强度必须为整数")

    def update_damage_intensity(self, key, text):
        """更新攻击类型强度"""
        try:
            self.config["damage_types"][key] = int(text)
            save_config(self.config)
            self.status_bar.showMessage(f"{key} 强度已更新并保存")
        except ValueError:
            self.status_bar.showMessage(f"{key} 强度必须为整数")

    def update_channel(self, channel):
        """更新通道选择"""
        self.config["channel"] = channel
        self.update_max_intensity_display()
        save_config(self.config)
        self.status_bar.showMessage("通道选择已更新并保存")

    @asyncSlot()
    async def connect_otc(self):
        def log_to_waveform(msg):
            self.waveform_log.append(msg)

        success = await self.otc_controller.connect(retries=3, delay=2, log_callback=log_to_waveform)
        if success:
            await self.otc_controller.get_max_intensity()
            self.config["max_intensity"] = self.config["app_max_intensity"]
            self.update_max_intensity_display()
            self.validate_base_intensity()
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.status_bar.showMessage("OTC 控制器已连接")
        else:
            self.status_bar.showMessage("OTC 控制器连接失败，请检查地址或网络")

    @asyncSlot()
    async def disconnect_otc(self):
        if self.otc_controller.websocket:
            await self.otc_controller.websocket.close()
            self.otc_controller.websocket = None
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.status_bar.showMessage("OTC 控制器已断开")
        self.intensity_calculator.current_intensity = self.config["base_intensity"]
        self.dynamic_intensity_a_label.setText(f"A 动态强度: {self.config['base_intensity']}%")
        self.dynamic_intensity_b_label.setText(f"B 动态强度: {self.config['base_intensity']}%")

    def handle_event(self, event):
        self.intensity_calculator.add_event(event)
        self.log_output.append(f"检测到事件: {event['type']} - {event['subtype']}")

    @asyncSlot()
    async def start_program(self):
        if not self.running:
            self.start_log_monitor()
            self.running = True
            self.config["waveform_enabled"] = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_bar.showMessage("程序已启动")
            await self.waveform_loop()

    @asyncSlot()
    async def stop_program(self):
        if self.running:
            if self.log_thread and self.log_thread.isRunning():
                self.log_monitor.stop()
                self.log_thread.quit()
                self.log_thread.wait()
            self.running = False
            self.config["waveform_enabled"] = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.intensity_calculator.current_intensity = self.config["base_intensity"]
            self.dynamic_intensity_a_label.setText(f"A 动态强度: {self.config['base_intensity']}%")
            self.dynamic_intensity_b_label.setText(f"B 动态强度: {self.config['base_intensity']}%")
            self.status_bar.showMessage("程序已关闭")

    def start_log_monitor(self):
        log_file = self.log_monitor.find_latest_log_file()
        if log_file:
            self.log_thread = LogMonitorThread(self.log_monitor)
            self.log_thread.monitor_file = log_file
            self.log_thread.start()
            self.status_bar.showMessage(f"日志监控已启动: {log_file}")
            self.log_output.append(f"监控文件: {log_file}")
        else:
            self.status_bar.showMessage("未找到匹配的日志文件")

    async def waveform_loop(self):
        current_index = 0
        while self.running and self.config["waveform_enabled"]:
            intensity_percent = self.intensity_calculator.update_intensity()
            a_max = self.config.get("A_max", 80)
            b_max = self.config.get("B_max", 50)
            
            if self.config["channel"] == "both":
                a_intensity = min(int(intensity_percent * a_max / 100), a_max)
                b_intensity = min(int(intensity_percent * b_max / 100), b_max)
                self.dynamic_intensity_a_label.setText(f"A 动态强度: {intensity_percent}% ({a_intensity}/{a_max})")
                self.dynamic_intensity_b_label.setText(f"B 动态强度: {intensity_percent}% ({b_intensity}/{b_max})")
            elif self.config["channel"] == "A":
                a_intensity = min(int(intensity_percent * a_max / 100), a_max)
                self.dynamic_intensity_a_label.setText(f"A 动态强度: {intensity_percent}% ({a_intensity}/{a_max})")
                self.dynamic_intensity_b_label.setText(f"B 动态强度: {self.config['base_intensity']}%")
            else:  # "B"
                b_intensity = min(int(intensity_percent * b_max / 100), b_max)
                self.dynamic_intensity_a_label.setText(f"A 动态强度: {self.config['base_intensity']}%")
                self.dynamic_intensity_b_label.setText(f"B 动态强度: {intensity_percent}% ({b_intensity}/{b_max})")

            if self.config["selected_patterns"]:
                pattern_name = self.config["selected_patterns"][current_index % len(self.config["selected_patterns"])]
                current_index += 1
            else:
                pattern_name = "经典"
            await self.otc_controller.send_waveform(intensity_percent, self.config["ticks"], pattern_name, self.config["channel"])
            self.waveform_log.append(f"发送波形: 强度={intensity_percent}%, 波形={pattern_name}")
            await asyncio.sleep(1)

    def validate_base_intensity(self):
        base_intensity_value = int(self.config["base_intensity"] * self.config["app_max_intensity"] / 100)
        if base_intensity_value > self.config["app_max_intensity"]:
            QMessageBox.warning(self, "警告",
                f"基础强度 ({base_intensity_value}) 超过 App 强度上限 ({self.config['app_max_intensity']})，请调整基础强度或上限！")

    def update_max_intensity_display(self):
        if self.config["channel"] == "A":
            max_intensity = self.config.get("A_max", 30)
        elif self.config["channel"] == "B":
            max_intensity = self.config.get("B_max", 30)
        else:  # "both"
            a_max = self.config.get("A_max", 30)
            b_max = self.config.get("B_max", 30)
            max_intensity = f"A: {a_max}, B: {b_max}"
        self.config["app_max_intensity"] = max_intensity if isinstance(max_intensity, int) else min(a_max, b_max)
        self.config["max_intensity"] = self.config["app_max_intensity"]
        self.app_max_label.setText(f"App 强度上限: {max_intensity}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()
