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
        
        # Interfaces test widgets
        self.tests_lbl = QLabel("Testing Interfaces.")
        self.tests_lbl.setFont(self.label_font)
        self.tests_pbar = QProgressBar()

        self.repeat_tests = QPushButton("Repeat Tests")
        self.repeat_tests.setMaximumWidth(150)
        self.repeat_tests.setFont(self.label_font)
        self.repeat_tests.setStyleSheet("background-color: grey")
        self.repeat_tests.clicked.connect(self.initializePage)

        # Interfaces layout
        self.tests_layout = QVBoxLayout()
        self.tests_layout.addWidget(self.tests_lbl)
        self.tests_layout.addSpacing(25)
        self.tests_layout.addWidget(self.tests_pbar)
        self.tests_layout.addSpacing(25)
        self.tests_layout.addWidget(self.repeat_tests)

        # Hall Effect test widgets
        self.hall_effect_lbl = QLabel("Hall Effect Sensor: Red LED turns"
                                    " on when magnet is brought close to unit.")
        self.hall_effect_lbl.setFont(self.label_font)
        self.hall_effect_pass_btn = QPushButton("Pass")
        self.hall_effect_pass_btn.clicked.connect(self.hall_pass)
        self.hall_effect_fail_btn = QPushButton("Fail")
        self.hall_effect_fail_btn.clicked.connect(self.hall_fail)

        # LED test widgets
        self.led_test_lbl = QLabel("LED Test: Verify the green LED is on.")
        self.led_test_lbl.setFont(self.label_font)
        self.led_test_pass_btn = QPushButton("Pass")
        self.led_test_pass_btn.clicked.connect(self.led_pass)
        self.led_test_fail_btn = QPushButton("Fail")
        self.led_test_fail_btn.clicked.connect(self.led_fail)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(60)
        self.grid.addWidget(QLabel(), 0, 0)
        self.grid.addLayout(self.tests_layout, 1, 0)
        self.grid.addWidget(self.hall_effect_lbl, 2, 0)
        self.grid.addWidget(self.hall_effect_pass_btn, 2, 1)
        self.grid.addWidget(self.hall_effect_fail_btn, 2, 2)
        self.grid.addWidget(self.led_test_lbl, 3, 0)
        self.grid.addWidget(self.led_test_pass_btn, 3, 1)
        self.grid.addWidget(self.led_test_fail_btn, 3, 2)

        self.setLayout(self.grid)
        self.setTitle("Interfaces and LED Test")

    def initializePage(self):
        self.is_complete = False

        self.command_signal.connect(self.sm.send_command)
        self.complete_signal.connect(self.completeChanged)

        try:
            self.sm.data_ready.disconnect()
        except ValueError:
            print("already disconnected")

        self.sm.data_ready.connect(self.handle_5v_data)
        
        self.repeat_tests.setEnabled(False)
        
        self.tests_pbar.setRange(0, 2)
        self.pbar_value = 0

        self.tests_lbl.setText("Testing 5v...")
        self.command_signal.emit("5v")

    def handle_5v_data(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.handle_tac_data)
        p = "([0-9]+\.[0-9]+)"
        result = re.search(p, data)
        if result:
            value = float(result.group())
            self.tu.internal_5v_status.setText(f"Internal 5V: {value} V")
            if self.model.compare_to_limit("internal_5v", value):
                self.report.write_data("internal_5v", value, "PASS")
                self.tu.internal_5v_status.setStyleSheet(
                    self.threadlink.status_style_pass)
            else:
                self.report.write_data("internal_5v", value, "FAIL")
                self.tu.internal_5v_status.setStyleSheet(
                    self.threadlink.status_style_fail)
        else:
            QMessageBox.warning(self, "Warning!", "Bad 5 V data!")
            self.report.write_data("internal_5v", "", "FAIL")
            self.tu.internal_5v_status.setText(f"Internal 5V: NO DATA")
            self.tu.internal_5v_status.setStyleSheet(
                self.threadlink.status_style_fail)

        self.pbar_value +=1
        self.tests_pbar.setValue(self.pbar_value)
        self.tests_lbl.setText("Testing TAC ID...")
        self.command_signal.emit("tac-get-info")

    def handle_tac_data(self, data):
        p = "([0-9a-f]{8})"
        results = re.findall(p, data)
        if (results 
            and len(results) == 5
            and results[0] == self.tu.settings.value("port1_tac_id")):
            self.report.write_data("tac_connected", "", "PASS")
            self.report.write_data("eeprom_sn", results[-1], "PASS")
            self.tu.tac_id_status.setText("TAC ID: PASS")
            self.tu.tac_id_status.setStyleSheet(
                self.threadlink.status_style_pass)
        else:
            self.report.write_data("tac_connected", "", "FAIL")
            self.report.write_data("eeprom_sn", "", "FAIL")
            self.tu.tac_id_status.setText("TAC ID: FAIL")
            self.tu.tac_id_status.setStyleSheet(
                self.threadlink.status_style_fail)

        self.pbar_value += 1
        self.tests_pbar.setValue(self.pbar_value)
        self.tests_lbl.setText("Complete.")
        self.repeat_tests.setEnabled(True)

    def hall_pass(self):
        self.report.write_data("hall_effect", "", "PASS")
        self.tu.hall_effect_status.setText("Hall Effect Sensor Test: PASS")
        self.tu.hall_effect_status.setStyleSheet(
            self.threadlink.status_style_pass)
        self.hall_effect_pass_btn.setEnabled(False)
        self.hall_effect_fail_btn.setEnabled(False)

    def hall_fail(self):
        self.report.write_data("hall_effect", "", "FAIL")
        self.tu.hall_effect_status.setText("Hall Effect Sensor Test: FAIL")
        self.tu.hall_effect_status.setStyleSheet(
            self.threadlink.status_style_fail)
        self.hall_effect_pass_btn.setEnabled(False)
        self.hall_effect_fail_btn.setEnabled(False)

    def led_pass(self):
        self.report.write_data("led_test", "", "PASS")
        self.tu.led_test_status.setText("Hall Effect Sensor Test: PASS")
        self.tu.led_test_status.setStyleSheet(
            self.threadlink.status_style_pass)
        self.led_test_pass_btn.setEnabled(False)
        self.led_test_fail_btn.setEnabled(False)
        self.finished()

    def led_fail(self):
        self.report.write_data("led_test", "", "FAIL")
        self.tu.led_test_status.setText("Hall Effect Sensor Test: FAIL")
        self.tu.led_test_status.setStyleSheet(
            self.threadlink.status_style_fail)
        self.led_test_pass_btn.setEnabled(False)
        self.led_test_fail_btn.setEnabled(False)
        self.finished()

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