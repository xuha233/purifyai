"""
Pytest configuration for PyQt5 tests

Ensures QApplication instance is available for signal handling
"""
import sys
import os
import pytest

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    """Fixture to provide QApplication for all tests"""
    from PyQt5.QtWidgets import QApplication, qApp
    app = qApp
    if not app:
        app = QApplication(sys.argv)
    yield app


def qt_wait_for_signal(signal, timeout=10000, check_interval=50):
    """Wait for a Qt signal to be emitted

    Args:
        signal: The pyqtSignal to wait for
        timeout: Maximum wait time in milliseconds
        check_interval: Check interval in milliseconds

    Returns:
        True if signal was emitted, False on timeout
    """
    from PyQt5.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    received = []

    def on_signal(*args, **kwargs):
        received.append(True)
        loop.quit()

    signal.connect(on_signal)
    QTimer.singleShot(timeout, loop.quit)

    loop.exec_()
    signal.disconnect(on_signal)

    return len(received) > 0
