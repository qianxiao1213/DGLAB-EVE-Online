import sys
import asyncio
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QComboBox, QListWidget, QListWidgetItem,
                             QTextEdit, QLabel, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, QTimer
from qasync import QEventLoop, asyncSlot
from intensity_calculator import IntensityCalculator  # 导入强度计算模块
from EVELogMonitor import EVELogMonitor  # 导入日志监控模块
from otc_controller import OTCController  # 导入 OTC 控制器模块

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

        self.config = self.load_config()
        self.intensity_calculator = IntensityCalculator(self.config)
        self.otc_controller = OTCController(self.config)
        self.log_monitor = EVELogMonitor(self.config, self.handle_event)
        self.log_thread = None
        self.running = False

        self.init_ui()

    def load_config(self):
        CONFIG_FILE = "otc_config.json"
        default_config = {
            "ws_ip": "",  # 只存 IP 部分
            "ws": "",     # 完整的 WebSocket URL
            "log_dir": "",
            "listener_id": "",
            "base_intensity": 0,
            "app_max_intensity": None,  # 初始为 None，表示未获取
            "A_max": None,              # 初始为 None
            "B_max": None,              # 初始为 None
            "damage_types": {
                "强力一击": 10, "命中": 8, "穿透": 10, "擦过": 5, "轻轻擦过": 5, "完全没有打中你": 5
            },
            "reward_types": {
                "强力一击": 10, "命中": 8, "穿透": 10, "擦过": 5, "轻轻擦过": 5, "完全没有打中你": 5
            },
            "monitored_damage_types": [],
            "monitored_reward_types": [],
            "selected_patterns": ["经典"],
            "waveform_enabled": False,
            "min_intensity": 0,
            "max_intensity": 30,  # 仅用于显示默认值
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
        return default_config

    def save_config(self):
        CONFIG_FILE = "otc_config.json"
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.status_bar.showMessage(f"保存配置失败: {e}")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # WebSocket IP 输入
        ws_layout = QHBoxLayout()
        ws_layout.addWidget(QLabel("WebSocket IP:"))
        self.ws_input = QLineEdit(self.config["ws_ip"] or "192.168.8.129")
        self.ws_input.textChanged.connect(self.queue_config_update)
        ws_layout.addWidget(self.ws_input)
        self.connect_button = QPushButton("连接 OTC")
        self.connect_button.clicked.connect(self.connect_otc)
        ws_layout.addWidget(self.connect_button)
        self.disconnect_button = QPushButton("断开 OTC")
        self.disconnect_button.clicked.connect(self.disconnect_otc)
        self.disconnect_button.setEnabled(False)
        ws_layout.addWidget(self.disconnect_button)
        layout.addLayout(ws_layout)

        # 日志目录输入
        layout.addWidget(QLabel("日志目录:"))
        self.log_dir_input = QLineEdit(self.config["log_dir"])
        self.log_dir_input.textChanged.connect(self.queue_config_update)
        layout.addWidget(self.log_dir_input)

        # 用户ID输入
        layout.addWidget(QLabel("游戏ID:"))
        self.listener_id_input = QComboBox()
        self.listener_id_input.setEditable(True)
        for id in self.config["history_ids"]:
            self.listener_id_input.addItem(id)
        self.listener_id_input.setCurrentText(self.config["listener_id"])
        self.listener_id_input.currentTextChanged.connect(self.queue_config_update)
        layout.addWidget(self.listener_id_input)

        # 基础强度输入
        layout.addWidget(QLabel("基础强度:"))
        self.base_intensity_input = QLineEdit(str(self.config["base_intensity"]))
        self.base_intensity_input.textChanged.connect(self.update_base_intensity)
        layout.addWidget(self.base_intensity_input)

        self.app_max_label = QLabel(f"App 强度上限: {self.config['app_max_intensity']}")
        layout.addWidget(self.app_max_label)

        self.base_intensity_a_label = QLabel(f"A 基础强度: {self.config['base_intensity']}")
        layout.addWidget(self.base_intensity_a_label)
        self.base_intensity_b_label = QLabel(f"B 基础强度: {self.config['base_intensity']}")
        layout.addWidget(self.base_intensity_b_label)

        self.dynamic_intensity_a_label = QLabel(f"A 动态强度: {self.config['base_intensity']}")
        layout.addWidget(self.dynamic_intensity_a_label)
        self.dynamic_intensity_b_label = QLabel(f"B 动态强度: {self.config['base_intensity']}")
        layout.addWidget(self.dynamic_intensity_b_label)

        # 攻击类型选择
        layout.addWidget(QLabel("选择监控的攻击类型（NPC对玩家）:"))
        self.damage_types_list = QListWidget()
        for dt in self.config["damage_types"]:
            item = QListWidgetItem(dt)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if dt in self.config["monitored_damage_types"] else Qt.Unchecked)
            self.damage_types_list.addItem(item)
        self.damage_types_list.itemChanged.connect(self.queue_config_update)
        layout.addWidget(self.damage_types_list)

        # 奖励类型选择
        layout.addWidget(QLabel("选择监控的奖励类型（玩家对NPC）:"))
        self.reward_types_list = QListWidget()
        for rt in self.config["reward_types"]:
            item = QListWidgetItem(rt)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if rt in self.config["monitored_reward_types"] else Qt.Unchecked)
            self.reward_types_list.addItem(item)
        self.reward_types_list.itemChanged.connect(self.queue_config_update)
        layout.addWidget(self.reward_types_list)

        # 攻击强度调整
        self.damage_intensity_layout = QVBoxLayout()
        layout.addWidget(QLabel("调整攻击类型强度（NPC对玩家）:"))
        self.damage_intensity_inputs = {}
        for dt in self.config["damage_types"]:
            self.add_damage_intensity_input(dt)
        layout.addLayout(self.damage_intensity_layout)

        # 奖励强度调整
        self.reward_intensity_layout = QVBoxLayout()
        layout.addWidget(QLabel("调整奖励类型强度（玩家对NPC）:"))
        self.reward_intensity_inputs = {}
        for rt in self.config["reward_types"]:
            self.add_reward_intensity_input(rt)
        layout.addLayout(self.reward_intensity_layout)

        # 波形选择
        layout.addWidget(QLabel("选择波形:"))
        self.patterns_list = QListWidget()
        patterns = ["经典", "冲击", "炼狱2.0", "打屁股", "固定波形0", "固定波形1", "固定波形2",
                    "固定波形3", "固定波形4", "固定波形5", "固定波形6", "固定波形7",
                    "固定波形8", "固定波形9", "固定波形10"]
        for p in patterns:
            item = QListWidgetItem(p)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if p in self.config["selected_patterns"] else Qt.Unchecked)
            self.patterns_list.addItem(item)
        self.patterns_list.itemChanged.connect(self.queue_config_update)
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

        # 波形日志
        layout.addWidget(QLabel("波形发送日志:"))
        self.waveform_log = QTextEdit()
        self.waveform_log.setReadOnly(True)
        layout.addWidget(self.waveform_log)

        # 按钮
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("启动程序")
        self.start_button.clicked.connect(self.start_program)
        buttons_layout.addWidget(self.start_button)
        self.stop_button = QPushButton("关闭程序")
        self.stop_button.clicked.connect(self.stop_program)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)
        layout.addLayout(buttons_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("程序初始化完成，请输入配置")

        self.config_update_timer = QTimer()
        self.config_update_timer.setSingleShot(True)
        self.config_update_timer.timeout.connect(self.update_config)

    def queue_config_update(self):
        self.config_update_timer.start(500)

    def add_damage_intensity_input(self, dt):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(f"{dt}:"))
        input = QLineEdit(str(self.config["damage_types"][dt]))
        input.textChanged.connect(lambda text, key=dt: self.update_damage_intensity(key, text))
        self.damage_intensity_inputs[dt] = input
        hbox.addWidget(input)
        self.damage_intensity_layout.addLayout(hbox)

    def add_reward_intensity_input(self, rt):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(f"{rt}:"))
        input = QLineEdit(str(self.config["reward_types"][rt]))
        input.textChanged.connect(lambda text, key=rt: self.update_reward_intensity(key, text))
        self.reward_intensity_inputs[rt] = input
        hbox.addWidget(input)
        self.reward_intensity_layout.addLayout(hbox)

    def update_config(self):
        try:
            self.config["ws_ip"] = self.ws_input.text().strip()
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
            self.config["monitored_reward_types"] = [
                self.reward_types_list.item(i).text()
                for i in range(self.reward_types_list.count())
                if self.reward_types_list.item(i).checkState() == Qt.Checked
            ]
            self.config["selected_patterns"] = [
                self.patterns_list.item(i).text()
                for i in range(self.patterns_list.count())
                if self.patterns_list.item(i).checkState() == Qt.Checked
            ]
            self.save_config()
            self.status_bar.showMessage("配置已自动更新并保存")
        except Exception as e:
            self.status_bar.showMessage(f"配置更新失败: {e}")

    def update_base_intensity(self, text):
        try:
            intensity = int(text)
            if intensity < 0:
                raise ValueError("基础强度不能为负数")
            self.config["base_intensity"] = intensity
            self.intensity_calculator.base_intensity = intensity
            self.base_intensity_a_label.setText(f"A 基础强度: {intensity}")
            self.base_intensity_b_label.setText(f"B 基础强度: {intensity}")
            self.validate_base_intensity()
            self.save_config()
            self.status_bar.showMessage("基础强度已更新并保存")
        except ValueError as e:
            self.status_bar.showMessage(f"基础强度无效: {e}")

    def update_damage_intensity(self, key, text):
        try:
            self.config["damage_types"][key] = int(text)
            self.save_config()
            self.status_bar.showMessage(f"{key} 强度已更新并保存")
        except ValueError:
            self.status_bar.showMessage(f"{key} 强度必须为整数")

    def update_reward_intensity(self, key, text):
        try:
            self.config["reward_types"][key] = int(text)
            self.save_config()
            self.status_bar.showMessage(f"{key} 奖励强度已更新并保存")
        except ValueError:
            self.status_bar.showMessage(f"{key} 奖励强度必须为整数")

    def update_channel(self, channel):
        self.config["channel"] = channel
        # 如果已连接，重新获取最大强度
        if self.otc_controller.websocket:
            asyncio.ensure_future(self.otc_controller.get_max_intensity())
        self.update_max_intensity_display()
        self.intensity_calculator.app_max_intensity = self.config["app_max_intensity"]
        self.save_config()
        self.status_bar.showMessage("通道选择已更新并保存")

    def validate_config(self):
        if not self.config["ws_ip"]:
            raise ValueError("WebSocket IP 不能为空")
        if not self.config["log_dir"] or not os.path.exists(self.config["log_dir"]):
            raise ValueError(f"日志目录无效或不存在: {self.config['log_dir']}")
        if not self.config["listener_id"]:
            raise ValueError("游戏ID 不能为空")
        if self.config["base_intensity"] < 0:
            raise ValueError("基础强度必须为非负整数")

    @asyncSlot()
    async def connect_otc(self):
        def log_to_waveform(msg):
            self.waveform_log.append(msg)
        try:
            self.validate_config()
            self.config["ws"] = f"ws://{self.config['ws_ip']}:60536/1"
            success = await self.otc_controller.connect(retries=3, delay=2, log_callback=log_to_waveform)
            if success:
                await self.otc_controller.get_max_intensity()
                self.update_max_intensity_display()
                self.validate_base_intensity()
                self.connect_button.setEnabled(False)
                self.disconnect_button.setEnabled(True)
                self.status_bar.showMessage("OTC 控制器已连接")
            else:
                self.status_bar.showMessage("OTC 控制器连接失败，请检查地址或网络")
        except ValueError as e:
            self.status_bar.showMessage(f"配置错误: {e}")
        except Exception as e:
            self.status_bar.showMessage(f"连接 OTC 失败: {e}")

    @asyncSlot()
    async def disconnect_otc(self):
        try:
            if self.otc_controller.websocket:
                await self.otc_controller.websocket.close()
                self.otc_controller.websocket = None
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.status_bar.showMessage("OTC 控制器已断开")
            self.intensity_calculator.reset()
            self.dynamic_intensity_a_label.setText(f"A 动态强度: {self.config['base_intensity']}")
            self.dynamic_intensity_b_label.setText(f"B 动态强度: {self.config['base_intensity']}")
        except Exception as e:
            self.status_bar.showMessage(f"断开 OTC 失败: {e}")

    def handle_event(self, event):
        try:
            self.intensity_calculator.add_event(event)
            if event["type"] == "player_attack":
                self.log_output.append(f"检测到玩家攻击: {event['type']} - {event['subtype']}")
            else:
                self.log_output.append(f"检测到事件: {event['type']} - {event['subtype']}")
        except Exception as e:
            self.log_output.append(f"处理事件出错: {e}")

    @asyncSlot()
    async def start_program(self):
        try:
            if not self.running:
                self.validate_config()
                ws_url = f"ws://{self.config['ws_ip']}:60536/1"  # 自动补全
                self.otc_controller.ws_url = ws_url
                self.start_log_monitor()
                self.running = True
                self.config["waveform_enabled"] = True
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.status_bar.showMessage("程序已启动")
                await self.waveform_loop()
        except ValueError as e:
            self.status_bar.showMessage(f"配置错误: {e}")
        except Exception as e:
            self.status_bar.showMessage(f"启动程序失败: {e}")

    @asyncSlot()
    async def stop_program(self):
        try:
            if self.running:
                if self.log_thread and self.log_thread.isRunning():
                    self.log_monitor.stop()
                    self.log_thread.quit()
                    self.log_thread.wait(2000)
                self.running = False
                self.config["waveform_enabled"] = False
                await asyncio.sleep(0.1)
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.intensity_calculator.reset()
                self.dynamic_intensity_a_label.setText(f"A 动态强度: {self.config['base_intensity']}")
                self.dynamic_intensity_b_label.setText(f"B 动态强度: {self.config['base_intensity']}")
                self.status_bar.showMessage("程序已关闭")
        except Exception as e:
            self.status_bar.showMessage(f"关闭程序失败: {e}")

    def start_log_monitor(self):
        try:
            log_file = self.log_monitor.find_latest_log_file()
            if log_file:
                self.log_thread = LogMonitorThread(self.log_monitor)
                self.log_thread.monitor_file = log_file
                self.log_thread.start()
                self.status_bar.showMessage(f"日志监控已启动: {log_file}")
                self.log_output.append(f"监控文件: {log_file}")
            else:
                self.status_bar.showMessage("未找到匹配的日志文件")
        except Exception as e:
            self.status_bar.showMessage(f"日志监控启动失败: {e}")

    async def waveform_loop(self):
        current_index = 0
        while self.running and self.config["waveform_enabled"]:
            try:
                intensity = self.intensity_calculator.update_intensity()
                app_max = self.config["app_max_intensity"]
                intensity_percent = min((intensity / app_max) * 100, 100)
                a_max = self.config.get("A_max") if self.config.get("A_max") is not None else 30
                b_max = self.config.get("B_max") if self.config.get("B_max") is not None else 30

                if self.config["channel"] == "both":
                    self.dynamic_intensity_a_label.setText(f"A 动态强度: {min(intensity, a_max)} ({intensity_percent:.1f}%)")
                    self.dynamic_intensity_b_label.setText(f"B 动态强度: {min(intensity, b_max)} ({intensity_percent:.1f}%)")
                elif self.config["channel"] == "A":
                    self.dynamic_intensity_a_label.setText(f"A 动态强度: {min(intensity, a_max)} ({intensity_percent:.1f}%)")
                    self.dynamic_intensity_b_label.setText(f"B 动态强度: {self.config['base_intensity']}")
                else:
                    self.dynamic_intensity_a_label.setText(f"A 动态强度: {self.config['base_intensity']}")
                    self.dynamic_intensity_b_label.setText(f"B 动态强度: {min(intensity, b_max)} ({intensity_percent:.1f}%)")

                pattern_name = self.config["selected_patterns"][current_index % len(self.config["selected_patterns"])] if self.config["selected_patterns"] else "经典"
                current_index += 1
                await self.otc_controller.send_waveform(intensity, self.config["ticks"], pattern_name, self.config["channel"])
                self.waveform_log.append(f"发送波形: 强度={intensity}, 百分比={intensity_percent:.1f}%, 波形={pattern_name}")
                await asyncio.sleep(1)
            except Exception as e:
                self.waveform_log.append(f"波形循环出错: {e}")

    def validate_base_intensity(self):
        if self.config["base_intensity"] > self.config["app_max_intensity"]:
            QMessageBox.warning(self, "警告", f"基础强度 ({self.config['base_intensity']}) 超过 App 强度上限 ({self.config['app_max_intensity']})，请调整！")

    def update_max_intensity_display(self):
        # 如果未获取到实际值，使用默认值 30 仅用于显示
        a_max = self.config.get("A_max") if self.config.get("A_max") is not None else 30
        b_max = self.config.get("B_max") if self.config.get("B_max") is not None else 30
        if self.config["channel"] == "A":
            max_intensity = a_max
        elif self.config["channel"] == "B":
            max_intensity = b_max
        else:
            max_intensity = min(a_max, b_max)
        self.config["app_max_intensity"] = max_intensity
        self.app_max_label.setText(f"App 强度上限: {self.config['app_max_intensity']}")
        # 同步到 IntensityCalculator 和 OTCController
        self.intensity_calculator.app_max_intensity = self.config["app_max_intensity"]
        self.otc_controller.config["app_max_intensity"] = self.config["app_max_intensity"]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()
