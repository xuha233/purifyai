from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QCheckBox, QTabWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import shutil
from qfluentwidgets import StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton, PrimaryPushButton, ProgressBar

class AppDataScanThread(QThread):
    progress_signal = pyqtSignal(str)
    folder_found_signal = pyqtSignal(str, str, str, str, str)
    finished_signal = pyqtSignal()

    def __init__(self, folder_types):
        super().__init__()
        self.folder_types = folder_types

    def run(self):
        for folder_type in self.folder_types:
            self.progress_signal.emit(f"正在扫描: {folder_type}...")
            appdata_path = os.environ.get(folder_type + "APPDATA", "")
            if not appdata_path:
                continue
            if not os.path.exists(appdata_path):
                continue
            try:
                for item in os.listdir(appdata_path):
                    item_path = os.path.join(appdata_path, item)
                    if os.path.isdir(item_path):
                        self.scan_folder(item, item_path, folder_type)
            except:
                pass
        self.progress_signal.emit("扫描完成")
        self.finished_signal.emit()

    def scan_folder(self, name, path, folder_type):
        try:
            size = self.get_folder_size(path)
            size_str = self.format_size(size)
            risk_level = self.assess_risk(name, path, size)
            self.folder_found_signal.emit(name, path, size_str, folder_type, risk_level)
        except:
            pass

    def assess_risk(self, name, path, size):
        name_lower = name.lower()
        safe_keywords = ["cache", "temp", "tmp", "logs", "prefetch", "log", "crash", "dump"]
        for keyword in safe_keywords:
            if keyword in name_lower:
                return "安全"
        dangerous_keywords = ["config", "settings", "data", "save", "backup", "profile"]
        for keyword in dangerous_keywords:
            if keyword in name_lower:
                return "危险"
        return "疑似"