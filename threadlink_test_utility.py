import sys
import views
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication([])
    app.setStyle("fusion")
    window = views.ThreadlinkUtility()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()