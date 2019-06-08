import re
import os.path
import avr
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
        # one_wire_id = self.addPage(OneWireMaster(self, test_utility,
        #                                          serial_manager, report))
        # cypress_id = self.addPage(CypressBLE(self, test_utility,
        #                                      serial_manager, report))
        # xmega_id = self.addPage(XmegaInterfaces(self, test_utility,
        #                                         serial_manager, model, report))
        # uart_id = self.addPage(UartPower(self, test_utility, serial_manager,
        #                                  report))
        # deep_sleep_id = self.addPage(DeepSleep(self, test_utility,
        #                                        serial_manager, model, report))
        # final_id = self.addPage(FinalPage(test_utility, report))

        self.setup_page = self.page(setup_id)
        self.program_page = self.page(program_id)
        # self.one_wire_page = self.page(one_wire_id)
        # self.cypress_page = self.page(cypress_id)
        # self.xmega_page = self.page(xmega_id)
        # self.uart_page = self.page(uart_id)
        # self.deep_sleep_page = self.page(deep_sleep_id)
        # self.final_page = self.page(final_id)

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


class OneWireMaster(QWizardPage):
    """Third QWizard page. Handles OneWire Master programming."""
    command_signal = pyqtSignal(str)
    reprogram_signal = pyqtSignal()
    file_write_signal = pyqtSignal(str)
    one_wire_test_signal = pyqtSignal()
    complete_signal = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.one_wire_lbl = QLabel()
        self.one_wire_lbl.setFont(self.label_font)
        self.one_wire_pbar = QProgressBar()

        self.layout = QVBoxLayout()
        self.layout.addStretch()
        self.layout.addWidget(self.one_wire_lbl)
        self.layout.addWidget(self.one_wire_pbar)
        self.layout.addStretch()

        self.setLayout(self.layout)
        self.setTitle("Program 1-Wire Master")

    def initializePage(self):
        self.pbar_value = 0
        self.is_complete = False
        self.command_signal.connect(self.sm.send_command)
        self.file_write_signal.connect(self.sm.write_hex_file)
        self.reprogram_signal.connect(self.sm.reprogram_one_wire)
        self.one_wire_test_signal.connect(self.sm.one_wire_test)
        self.complete_signal.connect(self.completeChanged)
        self.sm.data_ready.connect(self.send_hex_file)
        self.sm.line_written.connect(self.update_pbar)
        self.threadlink.button(QWizard.NextButton).setEnabled(False)
        self.program()

    def isComplete(self):
        return self.is_complete

    def program(self):
        self.one_wire_pbar.setRange(0, 0)
        self.reprogram_signal.emit()
        self.one_wire_lbl.setText("Erasing flash. . .")

    def send_hex_file(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.data_parser)
        self.one_wire_pbar.setRange(0, 545)
        # Check for response from board before proceeding
        pattern = "download hex records now..."
        if (re.search(pattern, data)):
            hex_files_dir = Path(self.tu.settings.value("hex_files_path"))
            hex_files_path = str(hex_files_dir.joinpath("1-wire-master.hex"))
            if (os.path.isfile(hex_files_path)):
                self.one_wire_lbl.setText("Programming 1-wire master. . .")
                self.file_write_signal.emit(hex_files_path)
            else:
                QMessageBox.warning(self, "No hex file set or bad file path.")
        else:
            QMessageBox.warning(self, "Xmega1", "Bad command response.")

    def update_pbar(self):
        self.pbar_value += 1
        self.one_wire_pbar.setValue(self.pbar_value)

    def data_parser(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.record_version)
        pattern = "lock bits set"
        if (re.search(pattern, data)):
            self.one_wire_lbl.setText("Programming complete.")
            self.one_wire_test_signal.emit()
        else:
            QMessageBox.warning(self, "Xmega2", "Bad command response.")

    def record_version(self, data):
        self.sm.data_ready.disconnect()
        pattern = "([0-9]+\.[0-9a-zA-Z]+)"
        onewire_version = re.search(pattern, data)
        if (onewire_version):
            onewire_version_val = onewire_version.group()
            self.report.write_data("onewire_ver", onewire_version_val, "PASS")
            self.one_wire_lbl.setText("Version recorded.")
            self.tu.one_wire_prog_status.setText("1-Wire Programming: PASS")
            self.tu.one_wire_prog_status.setStyleSheet(Threadlink.status_style_pass)
        else:
            self.report.write_data("onewire_ver", "N/A", "FAIL")
            self.tu.one_wire_prog_status.setText("Xmega Programming: FAIL")
            self.tu.one_wire_prog_status.setStyleSheet(Threadlink.status_style_fail)
            QMessageBox.warning(self, "XMega3", "Bad command response.")

        self.is_complete = True
        self.complete_signal.emit()


class CypressBLE(QWizardPage):
    """Fourth QWizard page. Handles Cypress BLE tests."""
    command_signal = pyqtSignal(str)
    complete_signal = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.ble_lbl = QLabel("Run the Cypress programming utility to "
                              "program the CYBLE-224116 BLE module.")
        self.ble_lbl.setFont(self.label_font)
        self.ble_btn_pass = QPushButton("PASS")
        self.ble_btn_pass.setMaximumWidth(75)
        self.ble_btn_fail = QPushButton("FAIL")
        self.ble_btn_fail.setMaximumWidth(75)
        self.ble_btn_pass.clicked.connect(self.ble_pass)
        self.ble_btn_fail.clicked.connect(self.ble_fail)

        self.psoc_disconnect_lbl = QLabel()
        self.psoc_disconnect_lbl.setTextFormat(Qt.RichText)
        self.psoc_disconnect_lbl.setFont(self.label_font)
        self.psoc_disconnect_lbl.setText( 
            "Disconnect the PSoC programmer from J1 (backside) and sit the "
            "board all<br/>"
            "the way down into the test fixture pushing against the pogo pins.")
        # self.psoc_disconnect_lbl = QLabel("Disconnect the PSoC programmer "
        #                                   "from J1.")
        self.psoc_disconnect_chkbx = QCheckBox()
        self.psoc_disconnect_chkbx.setStyleSheet("QCheckBox::indicator \
                                                 {width: 20px; height: 20px}")
        self.psoc_disconnect_chkbx.clicked.connect(
            lambda: D505.checked(self.psoc_disconnect_lbl,
                                 self.psoc_disconnect_chkbx))

        self.pwr_cycle_lbl = QLabel("Power cycle DUT (unplug and replug "
                                    "the battery).")
        self.pwr_cycle_lbl.setFont(self.label_font)
        self.pwr_cycle_chkbx = QCheckBox()
        self.pwr_cycle_chkbx.setStyleSheet("QCheckBox::indicator {width: 20px; \
                                        height: 20px}")
        self.pwr_cycle_chkbx.clicked.connect(
            lambda: D505.checked(self.pwr_cycle_lbl, self.pwr_cycle_chkbx))

        self.bt_comm_lbl = QLabel("Verify communication to 505 with "
                                  "bluetooth device.")
        self.bt_comm_lbl.setFont(self.label_font)
        self.bt_comm_btn_pass = QPushButton("PASS")
        self.bt_comm_btn_pass.setMaximumWidth(75)
        self.bt_comm_btn_fail = QPushButton("FAIL")
        self.bt_comm_btn_fail.setMaximumWidth(75)
        self.bt_comm_btn_pass.clicked.connect(self.bt_comm_pass)
        self.bt_comm_btn_fail.clicked.connect(self.bt_comm_fail)

        self.leds_lbl = QLabel("Verify the blue & green LEDs are working.")
        self.leds_lbl.setFont(self.label_font)
        self.leds_chkbx = QCheckBox()
        self.leds_chkbx.setStyleSheet("QCheckBox::indicator {width: 20px; \
                                        height: 20px}")
        self.leds_chkbx.clicked.connect(
            lambda: D505.checked(self.leds_lbl, self.leds_chkbx))
        self.leds_chkbx.clicked.connect(self.psoc_version)

        self.psoc_pbar = QProgressBar()
        self.psoc_pbar_lbl = QLabel("PSoC version")
        self.psoc_pbar_lbl.setFont(self.label_font)

        self.psoc_layout = QVBoxLayout()
        self.psoc_layout.addWidget(self.psoc_pbar_lbl)
        self.psoc_layout.addWidget(self.psoc_pbar)

        self.uart_wire_lbl = QLabel("Plug in UART power wire before going to "
                                    "the next step.")
        self.uart_wire_lbl.setFont(self.label_font)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(25)
        self.grid.setVerticalSpacing(50)
        self.grid.addWidget(self.ble_lbl, 0, 0)
        self.grid.addWidget(self.ble_btn_pass, 0, 1)
        self.grid.addWidget(self.ble_btn_fail, 0, 2)
        self.grid.addWidget(self.psoc_disconnect_lbl, 1, 0)
        self.grid.addWidget(self.psoc_disconnect_chkbx, 1, 1)
        self.grid.addWidget(self.pwr_cycle_lbl, 2, 0)
        self.grid.addWidget(self.pwr_cycle_chkbx, 2, 1)
        self.grid.addWidget(self.bt_comm_lbl, 3, 0)
        self.grid.addWidget(self.bt_comm_btn_pass, 3, 1)
        self.grid.addWidget(self.bt_comm_btn_fail, 3, 2)
        self.grid.addWidget(self.leds_lbl, 4, 0)
        self.grid.addWidget(self.leds_chkbx, 4, 1)
        self.grid.addLayout(self.psoc_layout, 5, 0)
        self.grid.addWidget(self.uart_wire_lbl, 6, 0)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addLayout(self.grid)
        self.hbox.addStretch()

        self.layout = QVBoxLayout()
        self.layout.addStretch()
        self.layout.addLayout(self.hbox)
        self.layout.addStretch()

        self.setLayout(self.layout)
        self.setTitle("Cypress BLE")

    def initializePage(self):
        self.is_complete = False
        self.command_signal.connect(self.sm.send_command)
        self.complete_signal.connect(self.completeChanged)
        self.threadlink.button(QWizard.NextButton).setEnabled(False)

    def ble_pass(self):
        self.tu.ble_prog_status.setText("BLE Programming: PASS")
        self.tu.ble_prog_status.setStyleSheet(
            Threadlink.status_style_pass)
        self.ble_lbl.setStyleSheet("QLabel {color: grey}")
        self.report.write_data("ble_prog", "", "PASS")
        self.ble_btn_pass.setEnabled(False)
        self.ble_btn_fail.setEnabled(False)

    def ble_fail(self):
        self.tu.ble_prog_status.setText("BLE Programming: FAIL")
        self.tu.ble_prog_status.setStyleSheet(
            Threadlink.status_style_fail)
        self.ble_lbl.setStyleSheet("QLabel {color: grey}")
        self.report.write_data("ble_prog", "", "FAIL")
        self.ble_btn_pass.setEnabled(False)
        self.ble_btn_fail.setEnabled(False)

    def bt_comm_pass(self):
        self.tu.bluetooth_test_status.setText("Bluetooth Test: PASS")
        self.tu.bluetooth_test_status.setStyleSheet(
            Threadlink.status_style_pass)
        self.bt_comm_lbl.setStyleSheet("QLabel {color: grey}")
        self.report.write_data("bt_comms", "", "PASS")
        self.bt_comm_btn_pass.setEnabled(False)
        self.bt_comm_btn_fail.setEnabled(False)

    def bt_comm_fail(self):
        self.tu.bluetooth_test_status.setText("Bluetooth Test: FAIL")
        self.tu.bluetooth_test_status.setStyleSheet(
            Threadlink.status_style_fail)
        self.bt_comm_lbl.setStyleSheet("QLabel {color: grey}")
        self.report.write_data("bt_comms", "", "FAIL")
        self.bt_comm_btn_pass.setEnabled(False)
        self.bt_comm_btn_fail.setEnabled(False)

    def psoc_version(self):
        self.sm.data_ready.connect(self.parse_data)
        self.psoc_pbar.setRange(0, 0)
        self.psoc_pbar_lbl.setText("Checking PSoC version...")
        self.command_signal.emit("psoc-version")

    def parse_data(self, data):
        self.sm.data_ready.disconnect()
        pattern = "([0-9)+.([0-9])+.([0-9])+"
        version = re.search(pattern, data)
        if (version):
            self.report.write_data("ble_ver", version.group(), "PASS")
        else:
            QMessageBox.warning(self, "PSOC Version", "Bad command response.")
            self.report.write_data("ble_ver", "", "FAIL")

        self.psoc_pbar.setRange(0, 1)
        self.psoc_pbar.setValue(1)
        self.psoc_pbar_lbl.setText("Received PSoC version.")
        self.is_complete = True
        self.complete_signal.emit()

    def isComplete(self):
        return self.is_complete


class XmegaInterfaces(QWizardPage):
    """Fifth QWizard page. Tests Xmega programming interfaces."""
    complete_signal = pyqtSignal()
    command_signal = pyqtSignal(str)
    sleep_signal = pyqtSignal(int)
    imei_signal = pyqtSignal()
    flash_test_signal = pyqtSignal()
    gps_test_signal = pyqtSignal()
    serial_test_signal = pyqtSignal(str)
    rtc_test_signal = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, model, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.model = model
        self.report = report

        self.complete_signal.connect(self.completeChanged)
        self.command_signal.connect(self.sm.send_command)
        self.imei_signal.connect(self.sm.iridium_command)
        self.flash_test_signal.connect(self.sm.flash_test)
        self.gps_test_signal.connect(self.sm.gps_test)
        self.serial_test_signal.connect(self.sm.set_serial)
        self.rtc_test_signal.connect(self.sm.rtc_test)

        self.sm.flash_test_succeeded.connect(self.flash_pass)
        self.sm.flash_test_failed.connect(self.flash_fail)
        self.sm.gps_test_succeeded.connect(self.gps_pass)
        self.sm.gps_test_failed.connect(self.gps_fail)
        self.sm.serial_test_succeeded.connect(self.serial_pass)
        self.sm.serial_test_failed.connect(self.serial_fail)
        self.sm.rtc_test_succeeded.connect(self.rtc_pass)
        self.sm.rtc_test_failed.connect(self.rtc_fail)

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.xmega_lbl = QLabel("Testing Xmega interfaces.")
        self.xmega_lbl.setFont(self.label_font)
        self.xmega_pbar = QProgressBar()

        self.repeat_tests = QPushButton("Repeat Tests")
        self.repeat_tests.setMaximumWidth(150)
        self.repeat_tests.setFont(self.label_font)
        self.repeat_tests.setStyleSheet("background-color: grey")
        self.repeat_tests.clicked.connect(self.initializePage)

        self.layout = QVBoxLayout()
        self.layout.addStretch()
        self.layout.addWidget(self.xmega_lbl)
        self.layout.addWidget(self.xmega_pbar)
        self.layout.addSpacing(230)
        self.layout.addWidget(self.repeat_tests)
        self.layout.addStretch()
        self.layout.setAlignment(Qt.AlignHCenter)

        self.setLayout(self.layout)
        self.setTitle("XMega Interfaces")

    def initializePage(self):
        self.is_complete = False
        self.page_pass_status = True
        self.sm.data_ready.connect(self.check_serial)

        self.xmega_pbar.setRange(0, 9)
        self.xmega_pbar.setValue(0)
        self.xmega_pbar_counter = 0

        self.threadlink.button(QWizard.NextButton).setEnabled(False)
        self.repeat_tests.setEnabled(False)
        self.xmega_lbl.setText("Checking serial number. . .")

        self.tu.xmega_inter_status.setText("Xmega Interfaces:_____")

        self.command_signal.emit(f"serial {self.tu.pcba_sn}")

    def page_pass(self):
        self.tu.xmega_inter_status.setText("Xmega Interfaces: PASS")
        self.tu.xmega_inter_status.setStyleSheet(
            Threadlink.status_style_pass)

    def page_fail(self):
        self.tu.xmega_inter_status.setText("Xmega Interfaces: FAIL")
        self.tu.xmega_inter_status.setStyleSheet(
            Threadlink.status_style_fail)
        self.page_pass_status = False

    def check_serial(self):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.verify_batv)
        self.serial_test_signal.emit(self.tu.pcba_sn)

    def serial_pass(self, serial_num):
        self.report.write_data("serial_match", serial_num, "PASS")
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.xmega_lbl.setText("Verifying battery voltage. . .")
        self.command_signal.emit("bat_v")

    def serial_fail(self, data):
        self.report.write_data("serial_match", data, "FAIL")
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.page_fail()
        self.xmega_lbl.setText("Verifying battery voltage. . .")
        self.command_signal.emit("bat_v")

    def verify_batv(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.verify_modem)
        pattern = "([0-9])+.([0-9])+"
        if (re.search(pattern, data)):
            bat_v = float(re.search(pattern, data).group())
            value_pass = self.model.compare_to_limit("bat_v", bat_v)
            if (value_pass):
                self.report.write_data("bat_v", bat_v, "PASS")
            else:
                self.report.write_data("bat_v", bat_v, "FAIL")
                self.page_fail()
        else:
            QMessageBox.warning(self, "BatV Error",
                                "Serial error or bad value")
            self.report.write_data("bat_v", "", "FAIL")
            self.page_fail()

        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.xmega_lbl.setText("Checking IMEI number. . .")
        self.imei_signal.emit()

    def verify_modem(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.verify_board_id)
        pattern = "([0-9]){15}"
        m = re.search(pattern, data)
        if (m):
            imei = m.group()
            if (imei == self.tu.settings.value("iridium_imei")):
                self.report.write_data("iridium_match", imei, "PASS")
            else:
                self.report.write_data("iridium_match", imei, "FAIL")
                self.page_fail()
        else:
            QMessageBox.warning(self, "Iridium Modem Error",
                                "Serial error or bad value")
            self.report.write_data("iridium_match", "", "FAIL")
            self.page_fail()

        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.xmega_lbl.setText("Verifying board id. . .")
        self.command_signal.emit("board_id")

    def verify_board_id(self, data):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.verify_tac)
        pattern = r"([0-9A-Fa-f][0-9A-Fa-f]\s+){7}([0-9A-Fa-f][0-9A-Fa-f]){1}"
        if (re.search(pattern, data)):
            board_id = re.search(pattern, data).group()
            if (board_id[-2:] == "28"):
                self.report.write_data("board_id", board_id, "PASS")
            else:
                self.report.write_data("board_id", board_id, "FAIL")
                self.page_fail()
        else:
            QMessageBox.warning(self, "Board ID Error",
                                "Serial error or bad value")
            self.report.write_data("board_id", "", "FAIL")
            self.page_fail()

        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.xmega_lbl.setText("Checking TAC ports. . .")
        self.command_signal.emit("tac-get-info")

    def verify_tac(self, data):
        data = data.split("\n")

        try:
            port1 = data[2][0:8]
            port2 = data[7][0:8]
            port3 = data[12][0:8]
            port4 = data[17][0:8]

            if not (port1 == self.tu.settings.value("port1_tac_id") and
                    port2 == self.tu.settings.value("port2_tac_id") and
                    port3 == self.tu.settings.value("port3_tac_id") and
                    port4 == self.tu.settings.value("port4_tac_id")):
                self.report.write_data("tac_connected", "", "FAIL")
                self.page_fail()
            else:
                self.report.write_data("tac_connected", "", "PASS")

        except IndexError:
            QMessageBox.warning(self, "TAC Connection",
                                "Serial error or bad value")
            self.report.write_data("tac_connected", "", "FAIL")
            self.page_fail()

        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.xmega_lbl.setText("Checking flash. . .")
        self.flash_test_signal.emit()

    def flash_pass(self):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.snow_depth)
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.report.write_data("flash_comms", "", "PASS")
        self.xmega_lbl.setText("Testing alarm. . .")
        self.rtc_test_signal.emit()

    def flash_fail(self):
        self.sm.data_ready.disconnect()
        self.sm.data_ready.connect(self.snow_depth)
        QMessageBox.warning(self, "Flash", "Flash test failed!")
        self.report.write_data("flash_comms", "", "FAIL")
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.xmega_lbl.setText("Testing alarm. . .")
        self.page_fail()
        self.rtc_test_signal.emit()

    def rtc_pass(self):
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.report.write_data("rtc_alarm", "", "PASS")
        self.xmega_lbl.setText("Checking GPS connection. . .")
        self.gps_test_signal.emit()

    def rtc_fail(self):
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.report.write_data("rtc_alarm", "", "FAIL")
        self.xmega_lbl.setText("Checking GPS connection. . .")
        self.page_fail()
        self.gps_test_signal.emit()

    def gps_pass(self):
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.report.write_data("gps_comms", "", "PASS")
        self.xmega_lbl.setText("Checking range finder. . .")
        self.command_signal.emit("snow-depth")

    def gps_fail(self):
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.report.write_data("gps_comms", "", "FAIL")
        self.xmega_lbl.setText("Checking range finder. . .")
        self.page_fail()
        self.command_signal.emit("snow-depth")

    def snow_depth(self, data):
        self.sm.data_ready.disconnect()
        pattern = r"[0-9]+\scm"
        if (re.search(pattern, data)):
            value_string = re.search(pattern, data).group()
            # Get rid of units
            distance = value_string[:-3]
            self.report.write_data("sonic_connected", distance, "PASS")
        else:
            self.report.write_data("sonic_connected", "", "FAIL")
            QMessageBox.warning(self, "Sonic Connection",
                                "Serial error or bad value")
            self.page_fail()
        self.xmega_pbar_counter += 1
        self.xmega_pbar.setValue(self.xmega_pbar_counter)
        self.is_complete = True
        self.xmega_lbl.setText("Complete.")
        self.complete_signal.emit()

    def isComplete(self):
        if self.is_complete:
            self.repeat_tests.setEnabled(True)
            if self.page_pass_status:
                self.page_pass()

        return self.is_complete


class UartPower(QWizardPage):
    """Sixth QWizard page. Handles UART power and LED tests."""
    complete_signal = pyqtSignal()
    command_signal = pyqtSignal(str)

    def __init__(self, threadlink, test_utility, serial_manager, report):
        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.report = report

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.uart_pwr_lbl = QLabel("Remove battery power.")
        self.uart_pwr_lbl.setFont(self.label_font)
        self.uart_pwr_chkbx = QCheckBox()
        self.uart_pwr_chkbx.setStyleSheet("QCheckBox::indicator {width: 20px; "
                                          "height: 20px}")
        self.uart_pwr_chkbx.clicked.connect(
            lambda: D505.checked(self.uart_pwr_lbl, self.uart_pwr_chkbx))
        self.uart_pwr_chkbx.clicked.connect(self.verify_uart)

        self.uart_pbar_lbl = QLabel("Verify UART interface")
        self.uart_pbar_lbl.setFont(self.label_font)
        self.uart_pbar = QProgressBar()

        self.red_led_lbl = QLabel("Bring magnet over Hall-Effect sensor and"
                                  " verify red LED blinks.")
        self.red_led_lbl.setFont(self.label_font)
        self.red_led_chkbx = QCheckBox()
        self.red_led_chkbx.setStyleSheet("QCheckBox::indicator {width: 20px; \
                                        height: 20px}")
        self.red_led_chkbx.clicked.connect(
            lambda: D505.checked(self.red_led_lbl, self.red_led_chkbx))
        self.red_led_chkbx.clicked.connect(self.hall_effect)

        self.leds_lbl = QLabel("Remove UART power connection and reconnect the"
                               " battery.")
        self.leds_lbl.setWordWrap(True)
        self.leds_lbl.setFont(self.label_font)
        self.leds_chkbx = QCheckBox()
        self.leds_chkbx.setStyleSheet("QCheckBox::indicator {width: 20px; \
                                        height: 20px}")
        self.leds_chkbx.clicked.connect(
            lambda: D505.checked(self.leds_lbl, self.leds_chkbx))
        self.leds_chkbx.clicked.connect(self.page_complete)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(75)
        self.grid.setVerticalSpacing(25)
        self.grid.addWidget(self.uart_pwr_lbl, 0, 0)
        self.grid.addWidget(self.uart_pwr_chkbx, 0, 1)
        self.grid.addWidget(QLabel(), 1, 0)
        self.grid.addWidget(self.uart_pbar_lbl, 2, 0)
        self.grid.addWidget(self.uart_pbar, 3, 0)
        self.grid.addWidget(QLabel(), 4, 0)
        self.grid.addWidget(self.red_led_lbl, 5, 0)
        self.grid.addWidget(self.red_led_chkbx, 5, 1)
        self.grid.addWidget(self.leds_lbl, 6, 0)
        self.grid.addWidget(self.leds_chkbx, 6, 1)

        self.layout = QVBoxLayout()
        self.layout.addStretch()
        self.layout.addLayout(self.grid)
        self.layout.addStretch()

        self.setLayout(self.layout)
        self.setTitle("UART Power")

    def initializePage(self):
        self.is_complete = False
        self.complete_signal.connect(self.completeChanged)
        self.command_signal.connect(self.sm.send_command)
        self.threadlink.button(QWizard.NextButton).setEnabled(False)
        self.red_led_chkbx.setEnabled(False)
        self.leds_chkbx.setEnabled(False)

    def verify_uart(self):
        self.sm.data_ready.connect(self.rx_psoc)
        self.uart_pbar.setRange(0, 0)
        self.uart_pbar_lbl.setText("Verifying UART interface...")
        self.command_signal.emit("psoc-version")

    def rx_psoc(self, data):
        self.sm.data_ready.disconnect()
        pattern = "([0-9)+.([0-9])+.([0-9])+"
        version = re.search(pattern, data)
        if (version):
            self.uart_pbar.setRange(0, 1)
            self.uart_pbar.setValue(1)
            self.uart_pbar_lbl.setText("UART interface functional.")
            self.uart_pbar_lbl.setStyleSheet("QLabel {color: grey}")
            self.report.write_data("uart_comms", "", "PASS")
        else:
            QMessageBox.warning(self, "UART Power", "Bad command response.")
            self.report.write_data("uart_comms", "", "FAIL")
        self.red_led_chkbx.setEnabled(True)

    def hall_effect(self):
        self.tu.hall_effect_status.setText(
            "Hall Effect Sensor Test: PASS")
        self.tu.hall_effect_status.setStyleSheet(
            Threadlink.status_style_pass)
        self.leds_chkbx.setEnabled(True)

    def isComplete(self):
        return self.is_complete

    def page_complete(self):
        self.tu.led_test_status.setText("LED Test: PASS")
        self.report.write_data("led_test", "", "PASS")
        self.tu.led_test_status.setStyleSheet(
            Threadlink.status_style_pass)
        self.is_complete = True
        self.complete_signal.emit()


class DeepSleep(QWizardPage):
    """Seventh QWizard page. Handles deep sleep tests."""
    command_signal = pyqtSignal(str)
    complete_signal = pyqtSignal()

    def __init__(self, threadlink, test_utility, serial_manager, model, report):
        LINE_EDIT_WIDTH = 75
        RIGHT_SPACING = 50
        LEFT_SPACING = 50

        super().__init__()

        self.threadlink = threadlink
        self.tu = test_utility
        self.sm = serial_manager
        self.model = model
        self.report = report

        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        self.setStyleSheet("QCheckBox::indicator {width: 20px;"
                           "height: 20px}")

        self.ble_lbl = QLabel("Ensure BLE interface is disconnected or off.")
        self.ble_lbl.setFont(self.label_font)
        self.ble_chkbx = QCheckBox()
        self.ble_chkbx.clicked.connect(
            lambda: D505.checked(self.ble_lbl, self.ble_chkbx))

        self.input_i_lbl = QLabel()
        self.input_i_lbl.setTextFormat(Qt.RichText)
        self.input_i_lbl.setFont(self.label_font)
        self.input_i_lbl.setText(
            "Switch current meter to <b>uA</b> and record input current.")
        self.sleep_btn = QPushButton("Sleep Mode")
        self.sleep_btn.clicked.connect(self.sleep_command)
        self.input_i_input = QLineEdit()
        self.input_i_input.setFixedWidth(LINE_EDIT_WIDTH)
        self.input_i_unit = QLabel("uA")

        self.solar_lbl = QLabel()
        self.solar_lbl.setTextFormat(Qt.RichText)
        self.solar_lbl.setText(
            "Switch current meter <font color='red'>back to mA.</font><br/>"
            "Turn on solar panel simulating power supply.<br/>"
            "Use 0.7 V with the current limit set at 2 A.")
        self.solar_lbl.setFont(self.label_font)
        self.solar_chkbx = QCheckBox()
        self.solar_chkbx.clicked.connect(lambda: D505.checked(
            self.solar_lbl, self.solar_chkbx))

        self.solar_v_lbl = QLabel("Record solar charger voltage at Q22 pin 3.")
        self.solar_v_lbl.setFont(self.label_font)
        self.solar_v_input = QLineEdit()
        self.solar_v_input.setFixedWidth(LINE_EDIT_WIDTH)
        self.solar_v_unit = QLabel("V")
        self.solar_v_unit.setFont(self.label_font)

        self.solar_i_lbl = QLabel("Record solar charger current.")
        self.solar_i_lbl.setFont(self.label_font)
        self.solar_i_input = QLineEdit()
        self.solar_i_input.setFixedWidth(LINE_EDIT_WIDTH)
        self.solar_i_unit = QLabel("mA")
        self.solar_i_unit.setFont(self.label_font)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setMaximumWidth(75)
        self.submit_button.clicked.connect(self.parse_data)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.submit_button)
        self.btn_layout.addSpacing(RIGHT_SPACING + 5)

        self.ble_layout = QHBoxLayout()
        self.ble_layout.addSpacing(LEFT_SPACING)
        self.ble_layout.addWidget(self.ble_lbl)
        self.ble_layout.addStretch()
        self.ble_layout.addWidget(self.ble_chkbx)
        self.ble_layout.addSpacing(RIGHT_SPACING)

        self.input_i_layout = QHBoxLayout()
        self.input_i_layout.addSpacing(LEFT_SPACING)
        self.input_i_layout.addWidget(self.input_i_lbl)
        self.input_i_layout.addSpacing(50)
        self.input_i_layout.addWidget(self.sleep_btn)
        self.input_i_layout.addStretch()
        self.input_i_layout.addWidget(self.input_i_input)
        self.input_i_layout.addWidget(self.input_i_unit)
        self.input_i_layout.addSpacing(RIGHT_SPACING - 16)

        self.solar_layout = QHBoxLayout()
        self.solar_layout.addSpacing(LEFT_SPACING)
        self.solar_layout.addWidget(self.solar_lbl)
        self.solar_layout.addStretch()
        self.solar_layout.addWidget(self.solar_chkbx)
        self.solar_layout.addSpacing(RIGHT_SPACING)

        self.solar_v_layout = QHBoxLayout()
        self.solar_v_layout.addSpacing(LEFT_SPACING)
        self.solar_v_layout.addWidget(self.solar_v_lbl)
        self.solar_v_layout.addStretch()
        self.solar_v_layout.addWidget(self.solar_v_input)
        self.solar_v_layout.addWidget(self.solar_v_unit)
        self.solar_v_layout.addSpacing(RIGHT_SPACING - 10)

        self.solar_i_layout = QHBoxLayout()
        self.solar_i_layout.addSpacing(LEFT_SPACING)
        self.solar_i_layout.addWidget(self.solar_i_lbl)
        self.solar_i_layout.addStretch()
        self.solar_i_layout.addWidget(self.solar_i_input)
        self.solar_i_layout.addWidget(self.solar_i_unit)
        self.solar_i_layout.addSpacing(RIGHT_SPACING - 26)

        self.layout = QVBoxLayout()
        self.layout.addStretch()
        self.layout.addLayout(self.ble_layout)
        self.layout.addSpacing(25)
        self.layout.addLayout(self.input_i_layout)
        self.layout.addSpacing(25)
        self.layout.addLayout(self.solar_layout)
        self.layout.addSpacing(25)
        self.layout.addLayout(self.solar_v_layout)
        self.layout.addSpacing(25)
        self.layout.addLayout(self.solar_i_layout)
        self.layout.addSpacing(25)
        self.layout.addLayout(self.btn_layout)
        self.layout.addStretch()

        self.setLayout(self.layout)
        self.setTitle("Deep Sleep")

    def initializePage(self):
        self.is_complete = False
        self.command_signal.connect(self.sm.send_command)
        self.complete_signal.connect(self.completeChanged)
        self.sm.data_ready.connect(self.command_finished)
        self.threadlink.button(QWizard.NextButton).setEnabled(False)

    def sleep_command(self):
        self.command_signal.emit("pClock-off")
        self.sleep_btn.setEnabled(False)

    def command_finished(self):
        self.sleep_btn.setEnabled(True)

    def parse_data(self):
        try:
            deep_sleep_i = float(self.input_i_input.text())
            solar_v = float(self.solar_v_input.text())
            solar_i = float(self.solar_i_input.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Bad Input Value!")
            return

        deep_sleep_i_pass = self.model.compare_to_limit("deep_sleep_i",
                                                        deep_sleep_i)
        solar_i_pass = self.model.compare_to_limit("solar_i_min", solar_i)
        solar_v_pass = self.model.compare_to_limit("solar_v", solar_v)

        if deep_sleep_i_pass:
            self.report.write_data("deep_sleep_i", deep_sleep_i, "PASS")
            self.tu.deep_sleep_i_status.setStyleSheet(Threadlink.status_style_pass)
        else:
            self.report.write_data("deep_sleep_i", deep_sleep_i, "FAIL")
            self.tu.deep_sleep_i_status.setStyleSheet(Threadlink.status_style_fail)

        if solar_i_pass:
            self.report.write_data("solar_i", solar_i, "PASS")
            self.tu.solar_charge_i_status.setStyleSheet(Threadlink.status_style_pass)
        else:
            self.report.write_data("solar_i", solar_i, "FAIL")
            self.tu.solar_charge_i_status.setStyleSheet(Threadlink.status_style_fail)

        if solar_v_pass:
            self.report.write_data("solar_v", solar_v, "PASS")
            self.tu.solar_charge_v_status.setStyleSheet(Threadlink.status_style_pass)
        else:
            self.report.write_data("solar_v", solar_v, "FAIL")
            self.tu.solar_charge_v_status.setStyleSheet(Threadlink.status_style_fail)

        # Set status text values
        self.tu.deep_sleep_i_status.setText(
            f"Deep Sleep Current: {deep_sleep_i} uA")
        self.tu.solar_charge_i_status.setText(
            f"Solar Charge Current: {solar_i} mA")
        self.tu.solar_charge_v_status.setText(
            f"Solar Charge Voltage: {solar_v} V")

        self.submit_button.setEnabled(False)
        self.input_i_lbl.setStyleSheet("QLabel {color: grey}")
        self.solar_i_lbl.setStyleSheet("QLabel {color: grey}")
        self.solar_v_lbl.setStyleSheet("QLabel {color: grey}")
        self.is_complete = True
        self.complete_signal.emit()

    def isComplete(self):
        return self.is_complete


class FinalPage(QWizardPage):
    """Final QWizard page, displays test resutl."""
    def __init__(self, test_utility, report):
        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        super().__init__()

        self.tu = test_utility
        self.report = report

    def initializePage(self):
        # Check test result
        report_file_path = self.tu.settings.value("report_file_path")
        self.report.set_file_location(report_file_path)
        self.report.generate_report()

        test_result = self.report.test_result

        if test_result == "PASS":
            self.test_status = "Successful"
        else:
            self.test_status = "Failed"

        self.test_status_labl = QLabel(f"Test {self.test_status}!")
        self.test_status_labl.setFont(self.label_font)
        self.break_down_lbl = QLabel("Remove power and disconnect all"
                                     " peripherals from DUT.")
        self.break_down_lbl.setFont(self.label_font)

        self.layout = QVBoxLayout()
        self.layout.addStretch()
        self.layout.addWidget(self.test_status_labl)
        self.layout.addSpacing(25)
        self.layout.addWidget(self.break_down_lbl)
        self.layout.addStretch()
        self.layout.setAlignment(Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setTitle("Test Completed")
