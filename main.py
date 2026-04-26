from ui import BeatFrameApp
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
import sys

app = QApplication(sys.argv)
app.setWindowIcon(QIcon("soundicon.png"))

window = BeatFrameApp()
window.show()
sys.exit(app.exec())