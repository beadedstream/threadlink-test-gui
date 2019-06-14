import re
from pathlib import Path
from PyQt5.QtWidgets import (
    QWizardPage, QWizard, QLabel, QVBoxLayout, QCheckBox, QGridLayout,
    QLineEdit, QProgressBar, QPushButton, QMessageBox, QHBoxLayout,
    QApplication, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QThread


class Interfaces(QWizardPage):
    """QWizard page. Handles interface and LED testing and generating the
    output report."""

    command_signal = pyqtSignal(str)
    complete_signal = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, model, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report
        self.model = model

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        # Internal 5 V test widgets
        self.five_v_test_lbl = QLabel("Test internal 5V supply.")
        self.five_v_test_lbl.setFont(self.label_font)

        self.five_v_test_chkbx = QCheckBox()
        self.five_v_test_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.five_v_test_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.five_v_test_lbl,
             self.five_v_test_chkbx))
        self.five_v_test_chkbx.clicked.connect(self.test_5_v)

        # TAC ID test widgets
        self.tac_test_lbl = QLabel("Test TAC IDs.")
        self.tac_test_lbl.setFont(self.label_font)

        self.tac_test_chkbx = QCheckBox()
        self.tac_test_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.tac_test_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.tac_test_lbl,
                self.tac_test_chkbx))
        self.tac_test_chkbx.clicked.connect(self.test_tac)

        # Hall Effect test widgets
        self.hall_effect_lbl = QLabel("Hall Effect Sensor: Red LED turns"
                                    " on when magnet is brought close to unit.")
        self.hall_effect_lbl.setFont(self.label_font)

        self.hall_effect_chkbx = QCheckBox()
        self.hall_effect_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.hall_effect_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.hall_effect_lbl,
                self.hall_effect_chkbx))

        # LED test widgets
        self.led_test_lbl = QLabel("LED Test: Verify the green LED is on.")
        self.led_test_lbl.setFont(self.label_font)

        self.led_test_chkbx = QCheckBox()
        self.led_test_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.led_test_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.led_test_lbl,
                self.led_test_chkbx))
        self.led_test_chkbx.clicked.connect(self.finished)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(60)
        self.grid.addWidget(QLabel(), 0, 0)
        self.grid.addWidget(self.five_v_test_lbl, 1, 0)
        self.grid.addWidget(self.five_v_test_chkbx, 1, 1)
        self.grid.addWidget(self.tac_test_lbl, 2, 0)
        self.grid.addWidget(self.tac_test_chkbx, 2, 1)
        self.grid.addWidget(self.hall_effect_lbl, 3, 0)
        self.grid.addWidget(self.hall_effect_chkbx, 3, 1)
        self.grid.addWidget(self.led_test_lbl, 4, 0)
        self.grid.addWidget(self.led_test_chkbx, 4, 1)

        self.setLayout(self.grid)
        self.setTitle("Interfaces and LED Test")

    def initializePage(self):
        self.command_signal.connect(self.sm.send_command)
        self.complete_signal.connect(self.completeChanged)
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.handle_5v_data)
        self.is_complete = False

    def test_5_v(self):
        self.command_signal.emit("5v")

    def handle_5v_data(self, data):
        p = "([0-9]+\.[0-9]+)"
        result = re.search(p, data)
        if result:
            value = float(result.group())
        else:
            QMessageBox.warning(self, "Warning!", "Bad 5 V data!")
            return

        if self.model.compare_to_limit("internal_5v", value):
            self.report.write_data("internal_5v", value, "PASS")
        else:
            self.report.write_data("internal_5v", value, "FAIL")

    def test_tac(self):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.handle_tac_data)
        self.command_signal.emit("tac-get-info")

    def handle_tac_data(self, data):
        p = "([0-9a-f]{8})"
        results = re.findall(p, data)
        if (results 
            and len(results) == 5
            and results[0] == self.tu.settings.value("port1_tac_id")):
            self.report.write_data("tac_connected", "", "PASS")
            self.report.write_data("eeprom_sn", results[-1], "PASS")
        else:
            self.report.write_data("tac_connected", "", "FAIL")
            self.report.write_data("eeprom_sn", "", "FAIL")

    def finished(self):
        self.is_complete = True
        self.complete_signal.emit()

    def isComplete(self):
        """Overrides isComplete method to check if all user actions have been 
        completed and set to default the "Next" button if so."""
        if self.is_complete:
            self.threadlink.button(QWizard.CustomButton1).setDefault(False)
            self.threadlink.button(QWizard.NextButton).setDefault(True)
        return self.is_complete