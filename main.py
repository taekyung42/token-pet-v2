import sys

from PySide6.QtWidgets import QApplication

from log_monitor import LogMonitor
from pet_widget import PetWidget
from real_usage_monitor import RealUsageMonitor


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    pet = PetWidget()
    monitor = LogMonitor()
    monitor.updated.connect(pet.on_stats_updated)

    real_usage = RealUsageMonitor()
    real_usage.updated.connect(pet.on_real_usage_updated)

    pet.show()
    monitor.start()
    real_usage.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
