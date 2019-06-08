from pathlib import Path
from PyQt5.QtWidgets import (
    QWizardPage, QWizard, QLabel, QVBoxLayout, QCheckBox, QGridLayout,
    QLineEdit, QProgressBar, QPushButton, QMessageBox, QHBoxLayout,
    QApplication, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal


class Program(QWizardPage):
    """Second QWizard page. Handles Xmega programming, watchdog reset and 
    one-wire master programming."""

    command_signal = pyqtSignal(str)
    sleep_signal = pyqtSignal(int)
    complete_signal = pyqtSignal()
    flash_signal = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, model, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report
        self.model = model

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
            lambda: Threadlink.checked(self.batch_lbl, self.batch_chkbx))
        self.batch_chkbx.clicked.connect(self.start_flash)

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
            lambda: D505.checked(self.xmega_disconnect_lbl,
                                 self.xmega_disconnect_chkbx))
        self.xmega_disconnect_chkbx.clicked.connect(self.start_uart_tests)

        self.watchdog_pbar_lbl = QLabel("Resetting watchdog...")
        self.watchdog_pbar_lbl.setFont(self.label_font)
        self.watchdog_pbar = QProgressBar()
        self.watchdog_pbar.setRange(0, 1)

        self.app0_pbar_lbl = QLabel("Set 'app 0'.")
        self.app0_pbar_lbl.setFont(self.label_font)
        self.app0_pbar = QProgressBar()

        self.supply_5v_input_lbl = QLabel("Measure and record the 5 V supply "
                                          "(bottom side of C55):")
        self.supply_5v_input_lbl.setFont(self.label_font)
        self.supply_5v_input = QLineEdit()
        self.supply_5v_input.setEnabled(False)
        self.supply_5v_unit = QLabel("V")
        self.supply_5v_unit.setFont(self.label_font)
        self.supply_5v_input_btn = QPushButton("Submit")
        self.supply_5v_input_btn.setEnabled(False)
        self.supply_5v_input_btn.clicked.connect(self.user_value_handler)

        self.ble_parallel_lbl = QLabel("To save time, you can start "
                                       "programming the BLE after recording "
                                       "the 5V supply!")
        self.ble_parallel_lbl.setFont(self.label_font)

        self.supply_5v_pbar_lbl = QLabel("Testing supply 5v...")
        self.supply_5v_pbar_lbl.setFont(self.label_font)
        self.supply_5v_pbar = QProgressBar()
        self.supply_5v_pbar.setRange(0, 1)

        # Layouts
        self.batch_pbar_layout = QVBoxLayout()
        self.batch_pbar_layout.addWidget(self.batch_pbar_lbl)
        self.batch_pbar_layout.addWidget(self.batch_pbar)

        self.app0_layout = QVBoxLayout()
        self.app0_layout.addWidget(self.app0_pbar_lbl)
        self.app0_layout.addWidget(self.app0_pbar)

        self.watchdog_layout = QVBoxLayout()
        self.watchdog_layout.addWidget(self.watchdog_pbar_lbl)
        self.watchdog_layout.addWidget(self.watchdog_pbar)

        self.supply_5v_layout = QHBoxLayout()
        self.supply_5v_layout.addWidget(self.supply_5v_input_lbl)
        self.supply_5v_layout.addSpacing(25)
        self.supply_5v_layout.addWidget(self.supply_5v_input)
        self.supply_5v_layout.addSpacing(25)
        self.supply_5v_layout.addWidget(self.supply_5v_unit)
        self.supply_5v_layout.addStretch()
        self.supply_5v_layout.addWidget(self.supply_5v_input_btn)

        self.supply_5v_pbar_layout = QVBoxLayout()
        self.supply_5v_pbar_layout.addWidget(self.supply_5v_pbar_lbl)
        self.supply_5v_pbar_layout.addWidget(self.supply_5v_pbar)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(40)
        self.grid.addWidget(QLabel(), 0, 0)
        self.grid.addWidget(self.batch_lbl, 1, 0)
        self.grid.addWidget(self.batch_chkbx, 1, 1)
        self.grid.addLayout(self.batch_pbar_layout, 2, 0)
        self.grid.addWidget(self.xmega_disconnect_lbl, 3, 0)
        self.grid.addWidget(self.xmega_disconnect_chkbx, 3, 1)
        self.grid.addLayout(self.watchdog_layout, 4, 0)
        self.grid.addLayout(self.app0_layout, 5, 0)
        self.grid.addLayout(self.supply_5v_layout, 6, 0)
        self.grid.addWidget(self.ble_parallel_lbl, 7, 0)
        self.grid.addLayout(self.supply_5v_pbar_layout, 8, 0)

        self.setLayout(self.grid)
        self.setTitle("Xmega Programming and Verification")

    def initializePage(self):
        at_path = self.tu.settings.value("atprogram_file_path")
        hex_path = Path(self.tu.settings.value("hex_files_path"))
        self.flash = avr.FlashD505(at_path, hex_path)
        self.flash_thread = QThread()
        self.flash.moveToThread(self.flash_thread)
        self.flash_thread.start()

        self.command_signal.connect(self.sm.send_command)
        self.sleep_signal.connect(self.sm.sleep)
        self.complete_signal.connect(self.completeChanged)
        self.flash_signal.connect(self.flash.flash)

        self.flash.command_succeeded.connect(self.flash_update)
        self.flash.command_failed.connect(self.flash_failed)
        self.flash.flash_finished.connect(self.flash_finished)
        self.flash.process_error_signal.connect(self.process_error)
        self.flash.file_not_found_signal.connect(self.file_not_found)

        self.threadlink.button(QWizard.NextButton).setEnabled(False)
        self.threadlink.button(QWizard.NextButton).setAutoDefault(False)
        self.xmega_disconnect_chkbx.setEnabled(False)

        self.batch_pbar.setValue(0)

        self.flash_counter = 0

        # Flag for tracking page completion and allowing the next button
        # to be re-enabled.
        self.is_complete = False

    def process_error(self):
        """Creates a QMessagebox warning for an AVR programming error."""

        QMessageBox.warning(self, "Warning!", "Programming Error: Check" 
                            " AVR connection and hex files location!")
        Threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.initializePage()

    def file_not_found(self):
        """Creates a QMessageBox warning when config files are not set."""

        QMessageBox.warning(self, "Warning!", "File not found! Check "
                            "configuration settings for correct file "
                            "locations.")
        Threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.initializePage()

    def port_warning(self):
        """Creates a QMessagebox warning when no serial port selected."""

        QMessageBox.warning(self, "Warning!", "No serial port selected!")
        Threadlink.unchecked(self.xmega_disconnect_lbl,
                       self.xmega_disconnect_chkbx)
        self.watchdog_pbar.setRange(0, 1)

    def isComplete(self):
        """Overrides isComplete method to check if all user actions have been 
        completed and set to default the "Next" button if so."""

        if self.is_complete:
            self.threadlink.button(QWizard.CustomButton1).setDefault(False)
            self.threadlink.button(QWizard.NextButton).setDefault(True)
        return self.is_complete

    def start_flash(self):
        """Starts flash test by emitting command."""

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

        QMessageBox.warning(self, "Flashing D505",
                            f"Command {cmd_text} failed!")
        Threadlink.unchecked(self.batch_lbl, self.batch_chkbx)
        self.batch_pbar_lbl.setText("Flash Xmega")
        self.tu.xmega_prog_status.setStyleSheet(Threadlink.status_style_fail)
        self.tu.xmega_prog_status.setText("XMega Programming: FAIL")

    def flash_finished(self):
        """Handles case where flash programming is successful."""

        self.xmega_disconnect_chkbx.setEnabled(True)
        self.tu.xmega_prog_status.setStyleSheet(Threadlink.status_style_pass)
        self.tu.xmega_prog_status.setText("XMega Programming: PASS")
        self.flash_thread.quit()
        self.flash_thread.wait()

    def start_uart_tests(self):
        self.sm.data_ready.connect(self.watchdog_handler)
        self.watchdog_pbar.setRange(0, 0)
        self.command_signal.emit("watchdog")

    def watchdog_handler(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.app_off)
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
            D505.unchecked(self.xmega_disconnect_lbl,
                           self.xmega_disconnect_chkbx)
            return
        bootloader_version = bootloader_version.strip("\r\n")
        app_version = app_version.strip("\r\n")
        self.report.write_data("xmega_bootloader", bootloader_version, "PASS")
        self.report.write_data("xmega_app", app_version, "PASS")

        self.app0_pbar.setRange(0, 0)
        self.app0_pbar_lbl.setText("Sending 'app 0' command...")
        self.command_signal.emit("app 0")

    def app_off(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.uart_5v1_handler)

        self.app0_pbar.setRange(0, 1)
        self.app0_pbar.setValue(1)
        self.app0_pbar_lbl.setText("Sent 'app 0' command.")

        self.command_signal.emit("5V 1")

    def uart_5v1_handler(self, data):
        self.sm.data_ready.disconnect()
        self.supply_5v_input.setEnabled(True)
        self.supply_5v_input_btn.setEnabled(True)

    def user_value_handler(self):
        self.sm.data_ready.connect(self.uart_5v_handler)
        self.supply_5v_input.setEnabled(False)
        self.supply_5v_pbar.setRange(0, 0)
        try:
            supply_5v_val = float(self.supply_5v_input.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Bad Input Value!")
            return
        value_pass = self.model.compare_to_limit("supply_5v", supply_5v_val)

        if(value_pass):
            self.report.write_data("supply_5v", supply_5v_val, "PASS")
            self.tu.supply_5v_status.setStyleSheet(
                Threadlink.status_style_pass)
        else:
            self.report.write_data("supply_5v", supply_5v_val, "FAIL")
            self.tu.supply_5v_status.setStyleSheet(
                Threadlink.status_style_fail)

        self.tu.supply_5v_status.setText(
            f"5V Supply: {supply_5v_val} V")

        self.command_signal.emit("5V")
        self.supply_5v_input_btn.setEnabled(False)

    def uart_5v_handler(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.uart_5v0_handler)
        data = data.strip("\n").split("\n")
        try:
            uart_5v_val = float(data[1].strip("\n"))
        except ValueError:
            QMessageBox.warning(self, "Warning",
                                "Error in serial data.")
            return

        value_pass = self.model.compare_to_limit("uart_5v", uart_5v_val)

        if (value_pass):
            self.report.write_data("uart_5v", uart_5v_val, "PASS")
            self.tu.uart_5v_status.setStyleSheet(Threadlink.status_style_pass)
        else:
            self.report.write_data("uart_5v", uart_5v_val, "FAIL")
            self.tu.uart_5v_status.setStyleSheet(Threadlink.status_style_fail)

        self.tu.uart_5v_status.setText(f"5V UART {uart_5v_val} V")
        self.command_signal.emit("5V 0")

    def uart_5v0_handler(self, data):
        self.sm.data_ready.disconnect()
        self.sm.sleep_finished.connect(self.sleep_handler)
        self.sleep_signal.emit(20)

    def sleep_handler(self):
        self.sm.sleep_finished.disconnect()
        self.sm.data_ready.connect(self.final_5v_handler)
        self.command_signal.emit("5V")

    def final_5v_handler(self, data):
        self.sm.data_ready.disconnect()
        self.supply_5v_pbar.valueChanged.connect(self.completeChanged)
        self.supply_5v_pbar.setRange(0, 1)
        self.supply_5v_pbar.setValue(1)
        data = data.strip("\n").split("\n")
        try:
            uart_off_val = float(data[1].strip("\n"))
        except ValueError:
            QMessageBox.warning(self, "Warning",
                                "Error in serial data.")
            return
        value_pass = self.model.compare_to_limit("off_5v", uart_off_val)

        if (value_pass):
            self.report.write_data("off_5v", uart_off_val, "PASS")
            self.tu.uart_off_status.setStyleSheet(Threadlink.status_style_pass)
            self.supply_5v_pbar_lbl.setText("Complete.")
        else:
            self.report.write_data("off_5v", uart_off_val, "FAIL")
            self.tu.uart_off_status.setStyleSheet(Threadlink.status_style_fail)
            self.supply_5v_pbar_lbl.setText("Failed.")

        self.tu.uart_off_status.setText(f"5 V Off: {uart_off_val} V")
        self.is_complete = True
        self.complete_signal.emit()