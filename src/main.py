import sys
import os
import traceback
import logging

src_dir = os.getcwd()
sys.path.insert(0, src_dir)
sys.path.insert(0, os.path.join(src_dir, 'ui'))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from qfluentwidgets import setTheme, Theme, NavigationItemPosition, FluentIcon
from app import PurifyAIApp

# 导入日志模块
from utils.logger import get_logger, setup_root_logger_for_console

# 配置根日志器
setup_root_logger_for_console(level=logging.DEBUG)
logger = get_logger(__name__)

# 全局异常捕获
def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    logger.critical("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    # 保存到文件
    with open('error_log.txt', 'a', encoding='utf-8') as f:
        f.write(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        f.write('\n')

sys.excepthook = handle_exception

def main():
    logger.info("[应用:START] PurifyAI 应用程序启动中...")
    logger.info(f"[应用:SYSTEM] Python版本: {sys.version}")
    logger.info(f"[应用:SYSTEM] 工作目录: {os.getcwd()}")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    setTheme(Theme.LIGHT)

    logger.info("[应用:WINDOW] 正在创建主窗口...")

    try:
        window = PurifyAIApp(app)
        window.setWindowTitle('PurifyAI - 智能清理工具')
        window.resize(1100, 750)
        window.show()
        logger.info("[应用:WINDOW] 主窗口创建并显示成功")
    except Exception as e:
        logger.error(f"[应用:WINDOW] 创建主窗口失败: {e}")
        logger.debug(traceback.format_exc())
        raise

    logger.info("[应用:READY] 应用程序准备就绪，进入主事件循环")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
