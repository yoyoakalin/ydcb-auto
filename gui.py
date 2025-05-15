import sys
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QComboBox, QPushButton, QTextEdit, 
                            QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import win32gui
import win32con
import win32api
from screen import capture_application_window
from paddleocr import PaddleOCR
from PIL import Image
import logging
import numpy as np
from datetime import datetime
import os
import subprocess

# 创建日志记录器
def setup_logger():
    # 创建logs目录（如果不存在）
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 生成日志文件名，包含时间戳
    log_filename = f'logs/ocr_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class OCRThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, window_title):
        super().__init__()
        self.window_title = window_title
        self.is_running = True
        self.logger = logging.getLogger()
        self.recognition_interval = 2  # 默认识别间隔为2秒
        self.last_click_time = 0  # 记录上次点击时间
        
        # 任务状态
        self.TASK_START_DUNGEON = "开始秘境"
        self.TASK_WAIT_WHISTLE = "等待吹响"
        self.TASK_WHISTLE_FIGHT = "吹响打怪"
        self.current_task = self.TASK_START_DUNGEON

    def click_at_position(self, x, y):
        """在指定位置模拟鼠标左键点击"""
        try:
            # 获取窗口句柄
            hwnd = win32gui.FindWindow(None, self.window_title)
            if hwnd == 0:
                self.logger.error(f"未找到窗口: {self.window_title}")
                return False
                
            # 获取窗口位置
            rect = win32gui.GetWindowRect(hwnd)
            # 获取窗口客户区域位置
            client_rect = win32gui.GetClientRect(hwnd)
            
            # 计算窗口边框和标题栏的偏移
            border_width = ((rect[2] - rect[0]) - client_rect[2]) // 2
            title_height = (rect[3] - rect[1]) - client_rect[3] - border_width
            
            # 计算相对于窗口客户区域的点击位置
            click_x = rect[0] + border_width + int(x)
            click_y = rect[1] + title_height + int(y)
            
            self.logger.info(f"窗口位置: {rect}, 客户区域: {client_rect}")
            self.logger.info(f"边框宽度: {border_width}, 标题栏高度: {title_height}")
            self.logger.info(f"原始坐标: ({x}, {y}), 计算后坐标: ({click_x}, {click_y})")
            
            # 激活窗口
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)  # 等待窗口激活
            
            # 移动鼠标并点击
            win32api.SetCursorPos((click_x, click_y))
            time.sleep(0.1)  # 等待鼠标移动
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, click_x, click_y, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, click_x, click_y, 0, 0)
            
            self.last_click_time = time.time()
            self.logger.info(f"已点击位置: ({click_x}, {click_y})")
            return True
        except Exception as e:
            self.logger.error(f"点击操作失败: {str(e)}")
            return False

    def handle_start_dungeon_task(self, result):
        """处理开始秘境任务"""
        for line in result[0]:
            text = line[1][0]  # 识别的文本
            confidence = line[1][1]  # 置信度
            
            # 检查是否识别到"自动骰子"
            if ("自动骰子" in text or "自动般子" in text) and confidence > 0.5:
                # 计算中心点
                center_x = np.mean([p[0] for p in line[0]])
                center_y = np.mean([p[1] for p in line[0]])
                
                self.logger.info(f"识别到目标文本: {text} (置信度: {confidence:.2f})")
                self.update_signal.emit(f"识别到目标文本: {text} (置信度: {confidence:.2f})")
                
                # 点击自动骰子
                if self.click_at_position(center_x, center_y):
                    self.update_signal.emit("已点击'自动骰子'位置")
                    # 切换到等待吹响任务
                    self.current_task = self.TASK_WAIT_WHISTLE
                    self.recognition_interval = 10  # 设置识别间隔为10秒
                    self.logger.info("切换到等待吹响任务")
                    return True
        return False

    def handle_wait_whistle_task(self, result):
        """处理等待吹响任务"""
        found_whistle = False
        
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            
            # 检查是否识别到"自动投掷骰子中"
            if ("自动投掷骰子中" in text or "自动投掷般子中" in text) and confidence > 0.5:
                self.logger.info(f"识别到目标文本: {text} (置信度: {confidence:.2f})")
                self.update_signal.emit(f"识别到目标文本: {text} (置信度: {confidence:.2f})")
            
            # 检查是否识别到"吹响"
            if "吹响" in text and confidence > 0.5:
                found_whistle = True
                self.logger.info(f"识别到目标文本: {text} (置信度: {confidence:.2f})")
                self.update_signal.emit(f"识别到目标文本: {text} (置信度: {confidence:.2f})")
                
                # 计算中心点
                center_x = np.mean([p[0] for p in line[0]])
                center_y = np.mean([p[1] for p in line[0]])
                
                # 点击吹响
                if self.click_at_position(center_x, center_y):
                    self.update_signal.emit(f"已点击'吹响'位置: ({center_x}, {center_y})")
                    time.sleep(0.5)  # 每次点击后稍微等待一下
        
        # 如果识别到任何"吹响"文本，切换到吹响打怪任务
        if found_whistle:
            self.current_task = self.TASK_WHISTLE_FIGHT
            self.recognition_interval = 3  # 设置识别间隔为3秒
            self.logger.info("切换到吹响打怪任务")
            return True
            
        return False

    def handle_whistle_fight_task(self, result):
        """处理吹响打怪任务"""
        percent_box = None
        confirm_box = None
        
        # 查找包含"增加"、"减少"和"确定"文本
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            
            self.logger.info(f"识别到文本: {text} (置信度: {confidence:.2f})")
            
            if ("增加" in text or "减少" in text) and confidence > 0.7:
                percent_box = line[0]
                self.logger.info(f"找到目标文本: {text}")
            elif text == "确定" and confidence > 0.7:
                confirm_box = line[0]
                self.logger.info(f"找到目标文本: {text}")
        
        # 点击包含"增加"或"减少"的文本
        if percent_box:
            center_x = np.mean([p[0] for p in percent_box])
            center_y = np.mean([p[1] for p in percent_box])
            self.logger.info(f"准备点击'增加/减少'文本位置: ({center_x}, {center_y})")
            
            # 尝试点击，最多重试3次
            if self.click_at_position(center_x, center_y):
                self.logger.info(f"成功点击'增加/减少'文本位置: ({center_x}, {center_y})")
                self.update_signal.emit("已点击'增加/减少'文本位置")
        
        # 点击"确定"文本
        if confirm_box:
            center_x = np.mean([p[0] for p in confirm_box])
            center_y = np.mean([p[1] for p in confirm_box])
            self.logger.info(f"准备点击'确定'文本位置: ({center_x}, {center_y})")
            
            # 尝试点击，最多重试3次
            for i in range(3):
                if self.click_at_position(center_x, center_y):
                    self.logger.info(f"成功点击'确定'文本位置: ({center_x}, {center_y})")
                    self.update_signal.emit("已点击'确定'文本位置")
                    
                    # 等待并校验点击是否成功
                    time.sleep(1.5)
                    # 重新截图识别
                    img = capture_application_window(self.window_title)
                    if img:
                        img_array = np.array(img)
                        check_result = self.ocr.ocr(img_array, cls=True)
                        if check_result:
                            # 检查是否还能识别到"确定"文本
                            found = False
                            for line in check_result[0]:
                                if line[1][0] == "确定" and line[1][1] > 0.7:
                                    found = True
                                    break
                            if not found:
                                self.logger.info("校验成功：确定按钮已消失")
                                # 完成本轮任务，重新开始
                                self.current_task = self.TASK_START_DUNGEON
                                self.recognition_interval = 2
                                self.logger.info("完成本轮任务，重新开始")
                                return True
                            else:
                                self.logger.warning("校验失败：确定按钮仍然存在，重试点击")
                                continue
                    time.sleep(0.5)
                else:
                    self.logger.warning(f"第{i+1}次点击'确定'失败，重试...")
                    time.sleep(0.5)
        
        return False

    def run(self):
        try:
            # 创建PaddleOCR对象，优化配置
            self.logger.info("正在初始化OCR引擎...")
            self.update_signal.emit("正在初始化OCR引擎...")
            ocr = PaddleOCR(
                use_angle_cls=True,  # 使用方向分类
                lang="ch",           # 中文模型
                use_gpu=True,        # 使用GPU
                det_db_thresh=0.3,   # 文本检测阈值
                det_db_box_thresh=0.5,  # 文本检测框阈值
                det_db_unclip_ratio=1.6,  # 文本检测框扩张比例
                rec_char_dict_path=None,  # 使用默认字典
                show_log=False       # 关闭日志输出
            )
            self.logger.info("OCR引擎初始化完成")

            while self.is_running:
                try:
                    # 截图
                    self.logger.info(f"正在截取窗口 '{self.window_title}' 的截图")
                    img = capture_application_window(self.window_title)
                    img_array = np.array(img)

                    # OCR识别
                    self.logger.info("开始OCR识别")
                    result = ocr.ocr(img_array, cls=True)

                    if result:
                        text_count = len(result[0])
                        self.logger.info(f"识别到 {text_count} 个文本区域")
                        self.logger.info(f"当前任务状态: {self.current_task}")
                        
                        # 根据当前任务状态处理识别结果
                        if self.current_task == self.TASK_START_DUNGEON:
                            self.handle_start_dungeon_task(result)
                        elif self.current_task == self.TASK_WAIT_WHISTLE:
                            self.handle_wait_whistle_task(result)
                        elif self.current_task == self.TASK_WHISTLE_FIGHT:
                            self.handle_whistle_fight_task(result)
                    else:
                        self.logger.info("未识别到任何文本")

                    time.sleep(self.recognition_interval)  # 使用动态识别间隔

                except Exception as e:
                    error_msg = f"识别过程出错: {str(e)}"
                    self.logger.error(error_msg)
                    self.update_signal.emit(error_msg)
                    time.sleep(1)

        except Exception as e:
            error_msg = f"OCR引擎初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_signal.emit(error_msg)

        self.finished_signal.emit()

    def stop(self):
        self.logger.info("停止OCR识别")
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ocr_thread = None
        self.logger = logging.getLogger()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('OCR窗口识别工具')
        self.setGeometry(100, 100, 800, 600)

        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建窗口选择部分
        window_layout = QHBoxLayout()
        window_label = QLabel('选择窗口:')
        self.window_combo = QComboBox()
        self.refresh_button = QPushButton('刷新窗口列表')
        self.refresh_button.clicked.connect(self.refresh_windows)
        window_layout.addWidget(window_label)
        window_layout.addWidget(self.window_combo)
        window_layout.addWidget(self.refresh_button)
        layout.addLayout(window_layout)

        # 创建按钮部分
        button_layout = QHBoxLayout()
        self.start_button = QPushButton('开始识别')
        self.stop_button = QPushButton('停止识别')
        self.start_button.clicked.connect(self.start_ocr)
        self.stop_button.clicked.connect(self.stop_ocr)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        # 创建控制台输出部分
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        # 初始化窗口列表
        self.refresh_windows()
        self.logger.info("GUI界面初始化完成")

    def refresh_windows(self):
        self.window_combo.clear()
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(title)
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)
        self.window_combo.addItems(windows)
        self.logger.info(f"已刷新窗口列表，共找到 {len(windows)} 个窗口")

    def start_ocr(self):
        if not self.window_combo.currentText():
            self.logger.warning("未选择窗口")
            QMessageBox.warning(self, '警告', '请先选择一个窗口！')
            return

        self.logger.info(f"开始识别窗口: {self.window_combo.currentText()}")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.window_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)

        self.ocr_thread = OCRThread(self.window_combo.currentText())
        self.ocr_thread.update_signal.connect(self.update_console)
        self.ocr_thread.finished_signal.connect(self.ocr_finished)
        self.ocr_thread.start()

    def stop_ocr(self):
        if self.ocr_thread:
            self.logger.info("用户停止OCR识别")
            self.ocr_thread.stop()
            self.ocr_thread.wait()
            self.ocr_finished()

    def update_console(self, message):
        self.console.append(message)

    def ocr_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.window_combo.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.logger.info("OCR识别已停止")

    def click_text(self, text, confidence=0.7):
        """点击指定文本的中心位置"""
        try:
            # 获取屏幕截图
            screenshot = self.capture_window()
            if screenshot is None:
                return False
            
            # 使用PaddleOCR进行文字识别
            result = self.ocr.ocr(screenshot, cls=True)
            
            # 查找目标文本
            target_box = None
            for line in result[0]:
                if line[1][0] == text and line[1][1] > confidence:
                    target_box = line[0]
                    break
            
            if target_box:
                # 计算中心点坐标
                center_x = int((target_box[0][0] + target_box[2][0]) / 2)
                center_y = int((target_box[0][1] + target_box[2][1]) / 2)
                
                # 点击中心点
                win32api.SetCursorPos((center_x, center_y))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.logger.info(f"点击文本 '{text}' 的中心点: ({center_x}, {center_y})")
                return True
            else:
                self.logger.warning(f"未找到文本: {text}")
                return False
                
        except Exception as e:
            self.logger.error(f"点击文本时出错: {str(e)}")
            return False

    def start_recognition(self):
        """开始识别"""
        try:
            # 获取选中的窗口句柄
            window_title = self.window_combo.currentText()
            if not window_title:
                QMessageBox.warning(self, "警告", "请先选择要识别的窗口")
                return
            
            # 获取窗口句柄
            hwnd = win32gui.FindWindow(None, window_title)
            if not hwnd:
                QMessageBox.warning(self, "警告", "未找到指定窗口")
                return
            
            # 将窗口置顶
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)  # 等待窗口置顶
            
            # 点击"吹响"文本
            if self.click_text("吹响"):
                # 等待3秒
                time.sleep(3)
                self.logger.info("等待3秒")
                
                # 再次截图识别
                screenshot = self.capture_window()
                if screenshot is None:
                    return
                
                result = self.ocr.ocr(screenshot, cls=True)
                
                # 查找"%"和"确定"文本
                percent_box = None
                confirm_box = None
                
                for line in result[0]:
                    if line[1][0] == "%" and line[1][1] > 0.7:
                        percent_box = line[0]
                    elif line[1][0] == "确定" and line[1][1] > 0.7:
                        confirm_box = line[0]
                
                # 点击"%"文本
                if percent_box:
                    center_x = int((percent_box[0][0] + percent_box[2][0]) / 2)
                    center_y = int((percent_box[0][1] + percent_box[2][1]) / 2)
                    win32api.SetCursorPos((center_x, center_y))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.1)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    self.logger.info(f"点击'%'文本的中心点: ({center_x}, {center_y})")
                
                # 点击"确定"文本
                if confirm_box:
                    center_x = int((confirm_box[0][0] + confirm_box[2][0]) / 2)
                    center_y = int((confirm_box[0][1] + confirm_box[2][1]) / 2)
                    win32api.SetCursorPos((center_x, center_y))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.1)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    self.logger.info(f"点击'确定'文本的中心点: ({center_x}, {center_y})")
            
        except Exception as e:
            self.logger.error(f"识别过程出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"识别过程出错: {str(e)}")

if __name__ == '__main__':
    # 设置日志记录器
    logger = setup_logger()
    logger.info("程序启动")
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 