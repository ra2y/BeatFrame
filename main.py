from ui import BeatFrameApp
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = BeatFrameApp()
window.show()
sys.exit(app.exec())