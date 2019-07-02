import re
import os.path
from pathlib import Path
from PyQt5.QtWidgets import (
    QWizardPage, QWizard, QLabel, QVBoxLayout, QCheckBox, QGridLayout,
    QLineEdit, QProgressBar, QPushButton, QMessageBox, QHBoxLayout,
    QApplication, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from setup import Setup
from program import Program
from interfaces import Interfaces
from final_page import FinalPage


class Threadlink(QWizard):
    """QWizard class for the Threadlink board. Sets up the QWizard page and adds the
    individual QWizardPage subpages for each set of tests."""

    status_style_pass = """QLabel {background: #8cff66;
                        border: 2px solid grey; font-size: 20px}"""
    status_style_fail = """QLabel {background: #ff5c33;
                        border: 2px solid grey; font-size: 20px}"""

    def __init__(self, test_utility, model, serial_manager, report):
        super().__init__()
        self.abort_btn = QPushButton("Abort")
        self.abort_btn.clicked.connect(self.abort)
        self.setButton(QWizard.CustomButton1, self.abort_btn)
        self.button(QWizard.FinishButton).clicked.connect(self.finish)

        qbtn_layout = [QWizard.Stretch, QWizard.NextButton,
                       QWizard.FinishButton, QWizard.CustomButton1]
        self.setButtonLayout(qbtn_layout)

        self.button(QWizard.NextButton).setEnabled(False)

        # This fixes a bug in the default style which hides the QWizard
        # buttons until the window is resized.
        self.setWizardStyle(0)

        setup_id = self.addPage(Setup(self, test_utility, serial_manager,
                                      model, report))
        program_id = self.addPage(Program(self, test_utility, serial_manager,
                                            model, report))
        interfaces_id = self.addPage(Interfaces(self, test_utility, 
                                                serial_manager, model, report))
        final_id = self.addPage(FinalPage(self, test_utility, report))

        self.setup_page = self.page(setup_id)
        self.program_page = self.page(program_id)
        self.interfaces_page = self.page(interfaces_id)
        self.final_page = self.page(final_id)

        self.tu = test_utility
        self.report = report

    def abort(self):
        """Prompt user for confirmation and abort test if confirmed."""

        msg = "Are you sure you want to cancel the test?"
        confirmation = QMessageBox.question(self, "Abort Test?", msg,
                                            QMessageBox.Yes,
                                            QMessageBox.No)
        if confirmation == QMessageBox.Yes:
            self.tu.initUI()
        else:
            pass

    def finish(self):
        """Reinitialize the TestUtility main page when tests are finished."""

        self.tu.initUI()

    @staticmethod
    def checked(lbl, chkbx):
        """Utility function for formatted a checked Qcheckbox."""

        if chkbx.isChecked():
            chkbx.setEnabled(False)
            lbl.setStyleSheet("QLabel {color: grey}")

    @staticmethod
    def unchecked(lbl, chkbx):
        """Utility function for formatting an unchecked Qcheckbox."""

        if chkbx.isChecked():
            chkbx.setEnabled(True)
            chkbx.setChecked(False)
            lbl.setStyleSheet("QLabel {color: black}")
