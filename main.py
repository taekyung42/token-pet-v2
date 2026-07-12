import sys

if sys.platform == "win32":
    # Must run before QApplication exists. Without this, a frozen
    # (PyInstaller) exe isn't declared per-monitor-DPI-aware, so Windows
    # renders the window at 96 DPI and then bitmap-stretches it to fit each
    # monitor's actual scale factor -- that's what makes the sprite look
    # blurry *and* oversized on a high-DPI laptop panel while looking fine
    # on a low-DPI external monitor.
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from log_monitor import LogMonitor
from pet_widget import PetWidget
from real_usage_monitor import RealUsageMonitor


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    real_usage = RealUsageMonitor()

    pet = PetWidget(real_usage_monitor=real_usage)
    monitor = LogMonitor()
    monitor.updated.connect(pet.on_stats_updated)

    real_usage.updated.connect(pet.on_real_usage_updated)

    pet.show()
    monitor.start()
    real_usage.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
