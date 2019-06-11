import re
import avr
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
    version_check = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, model, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report
        self.model = model
        self.main_app_version = None

        self.sm.no_port_sel.connect(self.port_warning)

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.flash_statuses = {"chip_erase": "Programming boot-loader...",
                               "prog_boot": "Programming app-section...",
                               "prog_app": "Programming main-app...",
                               "prog_main": "Writing fuses...",
                               "write_fuses": "Writing lockbits...",
                               "write_lockbits": "Complete!"}

        # Widgets
        self.batch_lbl = QLabel("Connect AVR programmer to board.")
        self.batch_lbl.setFont(self.label_font)
        self.batch_chkbx = QCheckBox()
        self.batch_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.batch_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.batch_lbl, self.batch_chkbx))
        self.batch_chkbx.clicked.connect(self.check_version)

        self.batch_pbar_lbl = QLabel("Flash Xmega.")
        self.batch_pbar_lbl.setFont(self.label_font)
        self.batch_pbar = QProgressBar()

        self.xmega_disconnect_lbl = QLabel("Remove Xmega programmer from "
                                           "connector J2. Ensure serial port "
                                           "is connected in the serial menu.")
        self.xmega_disconnect_lbl.setFont(self.label_font)
        # self.xmega_disconnect_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.xmega_disconnect_chkbx = QCheckBox()
        self.xmega_disconnect_chkbx.setStyleSheet("QCheckBox::indicator \
                                                   {width: 20px; \
                                                   height: 20px}")
        self.xmega_disconnect_chkbx.clicked.connect(
            lambda: self.threadlink.checked(self.xmega_disconnect_lbl,
                                 self.xmega_disconnect_chkbx))
        self.xmega_disconnect_chkbx.clicked.connect(self.start_uart_tests)

        self.watchdog_pbar_lbl = QLabel("Resetting watchdog...")
        self.watchdog_pbar_lbl.setFont(self.label_font)
        self.watchdog_pbar = QProgressBar()
        self.watchdog_pbar.setRange(0, 1)

        # Layouts
        self.batch_pbar_layout = QVBoxLayout()
        self.batch_pbar_layout.addWidget(self.batch_pbar_lbl)
        self.batch_pbar_layout.addWidget(self.batch_pbar)

        self.watchdog_layout = QVBoxLayout()
        self.watchdog_layout.addWidget(self.watchdog_pbar_lbl)
        self.watchdog_layout.addWidget(self.watchdog_pbar)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(40)
        self.grid.addWidget(QLabel(), 0, 0)
        self.grid.addWidget(self.batch_lbl, 1, 0)
        self.grid.addWidget(self.batch_chkbx, 1, 1)
        self.grid.addLayout(self.batch_pbar_layout, 2, 0)
        self.grid.addWidget(self.xmega_disconnect_lbl, 3, 0)
        self.grid.addWidget(self.xmega_disconnect_chkbx, 3, 1)
        self.grid.addLayout(self.watchdog_layout, 4, 0)

        self.setLayout(self.grid)
        self.setTitle("Xmega Programming and Verification")

    def initializePage(self):
        at_path = self.tu.settings.value("atprogram_file_path")
        hex_path = Path(self.tu.settings.value("hex_files_path"))
        self.flash = avr.FlashThreadlink(at_path, hex_path)
        self.flash_thread = QThread()
        self.flash.moveToThread(self.flash_thread)
        self.flash_thread.start()

        self.command_signal.connect(self.sm.send_command)
        self.sleep_signal.connect(self.sm.sleep)
        self.complete_signal.connect(self.completeChanged)
        self.flash_signal.connect(self.flash.flash)
        self.version_check.connect(self.sm.version_check)

        self.sm.version_signal.connect(self.compare_version)
        self.sm.no_version.connect(self.no_version)

        self.flash.command_succeeded.connect(self.flash_update)
        self.flash.command_failed.connect(self.flash_failed)
        self.flash.flash_finished.connect(self.flash_finished)
        self.flash.process_error_signal.connect(self.process_error)
        self.flash.file_not_found_signal.connect(self.file_not_found)
        self.flash.version_signal.connect(self.set_main_app_version)

        self.threadlink.button(QWizard.NextButton).setEnabled(False)
        self.threadlink.button(QWizard.NextButton).setAutoDefault(False)
        # self.xmega_disconnect_chkbx.setEnabled(False)

        self.batch_pbar.setValue(0)

        self.flash_counter = 0

        # Flag for tracking page completion and allowing the next button
        # to be re-enabled.
        self.is_complete = False

    def process_error(self):
        """Creates a QMessagebox warning for an AVR programming error."""
        QMessageBox.warning(self, "Warning!", "Programming Error: Check" 
                            " AVR connection and hex files location!")
        self.threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.initializePage()

    def file_not_found(self):
        """Creates a QMessageBox warning when config files are not set."""
        QMessageBox.warning(self, "Warning!", "File not found! Check "
                            "configuration settings for correct file "
                            "locations.")
        self.threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        # self.initializePage()

    def port_warning(self):
        """Creates a QMessagebox warning when no serial port selected."""
        QMessageBox.warning(self, "Warning!", "No serial port selected!")
        self.threadlink.unchecked(self.xmega_disconnect_lbl,
                       self.xmega_disconnect_chkbx)
        self.watchdog_pbar.setRange(0, 1)

    def set_main_app_version(self, version):
        self.main_app_version = version

    def check_version(self):
        # Check file paths to make sure files exist.
        self.flash.check_files()

        # Check main app version
        self.version_check.emit()

    def compare_version(self, version: str):
        if self.main_app_version == version:
            QMessageBox.warning(self, "Warning!", "Board and file versions"
                                " are the same, skipping programming.")
            self.batch_pbar_lbl.setText("Complete.")
            self.batch_pbar.setValue(6)
        else:
            self.start_flash()

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
        self.tu.xmega_prog_status.setStyleSheet(self.threadlink.status_style_fail)
        self.tu.xmega_prog_status.setText("XMega Programming: FAIL")

    def flash_finished(self):
        """Handles case where flash programming is successful."""

        self.xmega_disconnect_chkbx.setEnabled(True)
        self.tu.xmega_prog_status.setStyleSheet(self.threadlink.status_style_pass)
        self.tu.xmega_prog_status.setText("XMega Programming: PASS")
        self.flash_thread.quit()
        self.flash_thread.wait()

    def start_uart_tests(self):
        self.sm.data_ready.connect(self.watchdog_handler)
        self.watchdog_pbar.setRange(0, 0)
        self.command_signal.emit("watchdog")

    def watchdog_handler(self, data):
        self.sm.data_ready.disconnect()
        # self.sm.data_ready.connect(self.app_off)
        self.watchdog_pbar.setRange(0, 1)
        self.watchdog_pbar.setValue(1)
        pattern = "([0-9]+\.[0-9a-zA-Z]+)"
        try:
            matches = re.findall(pattern, data)
            bootloader_version = matches[0]
            app_version = matches[1]
        except IndexError:
            QMessageBox.warning(self, "Warning",
                                "Error in serial data.")
            self.report.write_data("xmega_bootloader", "", "FAIL")
            self.report.write_data("xmega_app", "", "FAIL")
            self.watchdog_pbar.setRange(0, 1)
            self.watchdog_pbar.setValue(0)
            self.threadlink.unchecked(self.xmega_disconnect_lbl,
                           self.xmega_disconnect_chkbx)
            return
        bootloader_version = bootloader_version.strip("\r\n")
        app_version = app_version.strip("\r\n")
        self.report.write_data("xmega_bootloader", bootloader_version, "PASS")
        self.report.write_data("xmega_app", app_version, "PASS")
