import sys

from PySide6.QtWidgets import QApplication

from uI.app import Window


app = QApplication(sys.argv)

window = Window()
window.show()

sys.exit(app.exec())