import re
import avr
from packaging.version import LegacyVersion
from pathlib import Path
from PyQt5.QtWidgets import (
    QWizardPage, QWizard, QLabel, QVBoxLayout, QCheckBox, QGridLayout,
    QLineEdit, QProgressBar, QPushButton, QMessageBox, QHBoxLayout,
    QApplication, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QThread


class Program(QWizardPage):
    """Second QWizard page. Handles Xmega programming, watchdog reset and 
    one-wire master programming."""

    command_signal = pyqtSignal(str)
    sleep_signal = pyqtSignal(int)
    complete_signal = pyqtSignal()
    flash_signal = pyqtSignal()
    board_version_check = pyqtSignal()
    test_one_wire = pyqtSignal()
    reprogram_one_wire = pyqtSignal()
    file_write_signal = pyqtSignal(str)

    def __init__(self, threadlink, test_utility, serial_manager, model, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report
        self.model = model
        self.main_app_file_version = None
        self.one_wire_file_version = None
        self.one_wire_file_path = None

        self.sm.no_port_sel.connect(self.port_warning)
        self.sm.no_port_sel_batch.connect(self.port_warning_batch)
        self.sm.no_port_sel_onewire.connect(self.port_warning_onewire)
        self.sm.serial_error_signal.connect(self.serial_error)

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.flash_statuses = {"chip_erase": "Programming boot-loader...",
                               "prog_boot": "Programming app-section...",
                               "prog_app": "Programming main-app...",
                               "prog_main": "Writing fuses...",
                               "write_fuses": "Writing lockbits...",
                               "write_lockbits": "Complete."}

        # Widgets
        self.batch_lbl = QLabel("Connect AVR programmer to board and ensure "
                                "serial port selected in menu.")
        self.batch_lbl.setFont(self.label_font)
        self.batch_chkbx = QCheckBox()
        self.batch_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.batch_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.batch_lbl, self.batch_chkbx))
        self.batch_chkbx.clicked.connect(self.check_hex_file_version)

        self.batch_pbar_lbl = QLabel("Flash Xmega.")
        self.batch_pbar_lbl.setFont(self.label_font)
        self.batch_pbar = QProgressBar()

        self.watchdog_pbar_lbl = QLabel("Resetting watchdog...")
        self.watchdog_pbar_lbl.setFont(self.label_font)
        self.watchdog_pbar = QProgressBar()
        self.watchdog_pbar.setRange(0, 1)

        self.one_wire_pbar_lbl = QLabel("Program OneWire Master")
        self.one_wire_pbar_lbl.setFont(self.label_font)
        self.one_wire_pbar = QProgressBar()

        # Layouts
        self.batch_pbar_layout = QVBoxLayout()
        self.batch_pbar_layout.addWidget(self.batch_pbar_lbl)
        self.batch_pbar_layout.addWidget(self.batch_pbar)

        self.watchdog_layout = QVBoxLayout()
        self.watchdog_layout.addWidget(self.watchdog_pbar_lbl)
        self.watchdog_layout.addWidget(self.watchdog_pbar)

        self.one_wire_pbar_layout = QVBoxLayout()
        self.one_wire_pbar_layout.addWidget(self.one_wire_pbar_lbl)
        self.one_wire_pbar_layout.addWidget(self.one_wire_pbar)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(75)
        self.grid.addWidget(QLabel(), 0, 0)
        self.grid.addWidget(self.batch_lbl, 1, 0)
        self.grid.addWidget(self.batch_chkbx, 1, 1)
        self.grid.addLayout(self.batch_pbar_layout, 2, 0)
        self.grid.addLayout(self.watchdog_layout, 3, 0)
        self.grid.addLayout(self.one_wire_pbar_layout, 4, 0)

        self.setLayout(self.grid)
        self.setTitle("Xmega Programming and Verification")

    def initializePage(self):
        self.pbar_value = 0

        at_path = self.tu.settings.value("atprogram_file_path")
        hex_path = Path(self.tu.settings.value("hex_files_path"))
        self.flash = avr.FlashThreadlink(at_path, hex_path)
        self.flash_thread = QThread()
        self.flash.moveToThread(self.flash_thread)
        self.flash_thread.start()

        self.flash.set_commands()

        self.command_signal.connect(self.sm.send_command)
        self.sleep_signal.connect(self.sm.sleep)
        self.complete_signal.connect(self.completeChanged)
        self.flash_signal.connect(self.flash.flash)
        self.board_version_check.connect(self.sm.version_check)

        self.sm.version_signal.connect(self.compare_version)
        self.sm.no_version.connect(self.no_version)
        self.sm.line_written.connect(self.update_pbar)
        self.sm.file_not_found_signal.connect(self.file_not_found)
        self.sm.generic_error_signal.connect(self.generic_error)
        self.test_one_wire.connect(self.sm.one_wire_test)
        self.reprogram_one_wire.connect(self.sm.reprogram_one_wire)
        self.file_write_signal.connect(self.sm.write_hex_file)

        self.flash.command_succeeded.connect(self.flash_update)
        self.flash.command_failed.connect(self.flash_failed)
        self.flash.flash_finished.connect(self.flash_finished)
        self.flash.process_error_signal.connect(self.process_error)
        self.flash.file_not_found_signal.connect(self.file_not_found)
        self.flash.version_signal.connect(self.set_versions)

        self.threadlink.button(QWizard.NextButton).setEnabled(False)
        self.threadlink.button(QWizard.NextButton).setAutoDefault(False)

        self.batch_pbar.setValue(0)

        self.flash_counter = 0

        # Flag for tracking page completion and allowing the next button
        # to be re-enabled.
        self.is_complete = False

    def generic_error(self, error):
        QMessageBox.warning(self, "Warning", error)

    def serial_error(self):
        QMessageBox.warning(self, "Warning!", "Serial error!")

    def process_error(self):
        """Creates a QMessagebox warning for an AVR programming error."""
        QMessageBox.warning(self, "Warning!", "Programming Error: Check" 
                            " AVR connection!")
        self.threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.flash_thread.quit()
        self.flash_thread.wait()
        self.initializePage()

    def file_not_found(self, file):
        """Creates a QMessageBox warning when config files are not set."""
        QMessageBox.warning(self, "Warning!", f"File {file} not found! Check "
                            "configuration settings for correct file "
                            "locations.")
        self.threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.flash_thread.quit()
        self.flash_thread.wait()
        self.initializePage()

    def port_warning(self):
        QMessageBox.warning(self, "Warning!", "No serial port selected!")

    def port_warning_batch(self):
        """Creates a QMessagebox warning when no serial port selected."""
        QMessageBox.warning(self, "Warning!", "No serial port selected!")
        self.threadlink.unchecked(self.batch_lbl,
                       self.batch_chkbx)
        self.batch_pbar.setRange(0, 1)

    def port_warning_onewire(self):
        """Creates a QMessagebox warning when no serial port selected."""
        QMessageBox.warning(self, "Warning!", "No serial port selected!")
        self.watchdog_pbar.setRange(0, 1)
        self.flash_thread.quit()
        self.flash_thread.wait()
        self.initializePage()

    def check_hex_file_version(self):
        """Checks hex file paths to make sure files exist, finds the main app
        hex file with the latest version and starts the version check on the
        board."""
        self.flash.check_files()
        self.flash.set_commands()

    def set_versions(self, main_app_ver, one_wire_file, one_wire_ver):
        """Set a variable to have the most recent version of the main app.
        Start the check of what version the board is running."""
        self.main_app_file_version = main_app_ver
        self.one_wire_file_path = one_wire_file
        self.one_wire_file_version = one_wire_ver

        # Check board version.
        self.board_version_check.emit()

    def compare_version(self, version: str):
        """Compare main app file version and board version using 
        packaging.version LegacyVersion and flash the board with the file if
        the file version is higher than the board version."""
        if LegacyVersion(self.main_app_file_version) > LegacyVersion(version):
            self.start_flash()
        else:
            QMessageBox.warning(self, "Warning!", "File version is not newer "
                                "than board version; skipping...")
            self.tu.xmega_prog_status.setStyleSheet(
                self.threadlink.status_style_pass)
            self.tu.xmega_prog_status.setText("XMega Programming: PASS")

            self.batch_pbar_lbl.setText("Complete.")
            self.batch_pbar.setRange(0, 1)
            self.batch_pbar.setValue(1)
            self.start_watchdog_reset()

    def no_version(self):
        self.start_flash()

    def isComplete(self):
        """Overrides isComplete method to check if all user actions have been 
        completed and set to default the "Next" button if so."""
        if self.is_complete:
            self.threadlink.button(QWizard.CustomButton1).setDefault(False)
            self.threadlink.button(QWizard.NextButton).setDefault(True)
        return self.is_complete

    def start_flash(self):
        """Starts flash by emitting command."""
        self.batch_pbar_lbl.setText("Erasing flash...")
        self.batch_pbar.setRange(0, 6)
        self.flash_signal.emit()

    def flash_update(self, cmd_text):
        """Updates the flash programming progressbar."""

        self.batch_pbar_lbl.setText(self.flash_statuses[cmd_text])
        self.flash_counter += 1
        self.batch_pbar.setValue(self.flash_counter)

    def flash_failed(self, cmd_text):
        """Handles case where flash programming failed."""

        QMessageBox.warning(self, "Flashing Threadlink",
                            f"Command {cmd_text} failed!")
        self.threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.tu.xmega_prog_status.setStyleSheet(
            self.threadlink.status_style_fail)
        self.tu.xmega_prog_status.setText("XMega Programming: FAIL")

    def flash_finished(self):
        """Handles case where flash programming is successful."""
        self.threadlink.checked(self.batch_lbl, self.batch_chkbx)
        self.tu.xmega_prog_status.setStyleSheet(self.threadlink.status_style_pass)
        self.tu.xmega_prog_status.setText("XMega Programming: PASS")
        self.flash_thread.quit()
        self.flash_thread.wait()
        self.start_watchdog_reset()

    def start_watchdog_reset(self):
        self.sm.data_ready.connect(self.watchdog_handler)
        self.watchdog_pbar.setRange(0, 0)
        self.command_signal.emit("watchdog")

    def watchdog_handler(self, data):
        self.sm.data_ready.disconnect()
        pattern = r'firmware version "RS485 BRIDGE MAIN APP [0-9]+\.[0-9]+[a-z]"'
        pattern_version = r"([0-9]+\.[0-9]+[a-z])"
        if not re.search(pattern, data):
            QMessageBox.warning(self, "Warning",
                                "Error in serial data.")
            self.watchdog_pbar.setRange(0, 1)
            self.watchdog_pbar.setValue(0)
            return
        xmega_version = re.search(pattern_version, data).group()
        self.report.write_data("xmega_app", xmega_version, "PASS")
        self.watchdog_pbar.setRange(0, 1)
        self.watchdog_pbar.setValue(1)
        self.watchdog_pbar_lbl.setText("Complete.")
        self.start_one_wire_programming()

    def start_one_wire_programming(self):
        self.sm.data_ready.connect(self.one_wire_version)
        self.test_one_wire.emit()
        self.one_wire_pbar_lbl.setText("Checking version...")

    def one_wire_version(self, data):
        self.sm.data_ready.disconnect()
        pattern = r"([0-9]+\.[0-9]+[a-z])"

        if re.search(pattern, data):
            one_wire_ver = re.search(pattern, data).group()
        else:
            one_wire_ver = None

        if (LegacyVersion(self.one_wire_file_version) > LegacyVersion(one_wire_ver)
            or not one_wire_ver):
            self.one_wire_pbar_lbl.setText("Erasing flash. . .")
            self.sm.data_ready.connect(self.send_hex_file)
            self.reprogram_one_wire.emit()
        else:
            QMessageBox.warning(self, "Warning!", "File version is not newer "
                                "than board version; skipping...")
            self.report.write_data("one_wire_ver", one_wire_ver, "PASS")
            self.tu.one_wire_prog_status.setText("1-Wire Programming: PASS")
            self.tu.one_wire_prog_status.setStyleSheet(
                self.threadlink.status_style_pass)
            self.one_wire_pbar_lbl.setText("Complete.")
            self.one_wire_pbar.setRange(0, 1)
            self.one_wire_pbar.setValue(1)
            self.is_complete = True
            self.complete_signal.emit()

    def send_hex_file(self, data):
        self.sm.data_ready.disconnect()

        # Get file length
        count = 0
        with open(self.one_wire_file_path, "r") as f:
            for line in f:
                count += 1
        self.one_wire_pbar.setRange(0, count)
        # Check for response from board before proceeding
        pattern = "download hex records now..."

        if (re.search(pattern, data)):
            self.one_wire_pbar_lbl.setText("Programming 1-wire master. . .")
            self.sm.data_ready.connect(self.data_parser)
            self.file_write_signal.emit(self.one_wire_file_path)
        else:
            QMessageBox.warning(self, "Xmega1", "Bad command response.")

    def update_pbar(self):
        self.pbar_value += 1
        self.one_wire_pbar.setValue(self.pbar_value)

    def data_parser(self, data):
        self.sm.data_ready.disconnect()
        pattern = "lock bits set"
        if (re.search(pattern, data)):
            self.one_wire_pbar_lbl.setText("Programming complete.")
            self.sm.data_ready.connect(self.record_version)
            self.test_one_wire.emit()
        else:
            QMessageBox.warning(self, "Xmega2", "Bad command response.")

    def record_version(self, data):
        self.sm.data_ready.disconnect()
        pattern = r"([0-9]+\.[0-9a-zA-Z]+)"
        onewire_version = re.search(pattern, data)

        if (onewire_version):
            onewire_version_val = onewire_version.group()
            self.report.write_data("one_wire_ver", onewire_version_val, "PASS")
            self.one_wire_pbar_lbl.setText("Version recorded.")
            self.tu.one_wire_prog_status.setText("1-Wire Programming: PASS")
            self.tu.one_wire_prog_status.setStyleSheet(
                self.threadlink.status_style_pass)
        else:
            self.report.write_data("one_wire_ver", "N/A", "FAIL")
            self.tu.one_wire_prog_status.setText("Xmega Programming: FAIL")
            self.tu.one_wire_prog_status.setStyleSheet(
                self.threadlink.status_style_fail)
            QMessageBox.warning(self, "XMega3", "Bad command response.")

        self.is_complete = True
        self.complete_signal.emit()