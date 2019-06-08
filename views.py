import os
import re
import threadlink
import serialmanager
import model
import report
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout, QApplication, QLabel,
    QLineEdit, QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
    QMessageBox, QAction, QActionGroup, QFileDialog, QDialog, QMenu,
    QDesktopWidget
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QSettings, Qt, QThread

VERSION_NUM = "0.1.0"

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800

ABOUT_TEXT = f"""
             PCB assembly test utility for threadlink boards. 
             Copyright Beaded Streams, 2019.
             v{VERSION_NUM}
             """


class InvalidMsgType(Exception):
    pass


class ThreadlinkUtility(QMainWindow):
    """Main class for the PCBA Test Utility.
    
    Creates main window for the program, the file menu, status bar, and the 
    settings/configuration window.
    """
    def __init__(self):
        super().__init__()
        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)
        self.config_font = QFont(self.system_font, 12)
        self.config_path_font = QFont(self.system_font, 12)

        self.settings = QSettings("BeadedStream", "Threadlink TestUtility")

        settings_defaults = {
            "port1_tac_id": "",
            "port2_tac_id": "",
            "port3_tac_id": "",
            "port4_tac_id": "",
            "hex_files_path": "/path/to/hex/files",
            "report_file_path": "/path/to/report/folder",
            "atprogram_file_path": "/path/to/atprogram.exe"
        }

        for key in settings_defaults:
            if not self.settings.value(key):
                self.settings.setValue(key, settings_defaults[key])

        self.sm = serialmanager.SerialManager()
        self.serial_thread = QThread()
        self.sm.moveToThread(self.serial_thread)
        self.serial_thread.start()

        self.m = model.Model()
        self.r = report.Report()

        self.sm.port_unavailable_signal.connect(self.port_unavailable)

        # Part number : [serial prefix, procedure class]
        self.product_data = {
            "45211-01": ["THL", threadlink.Threadlink],
        }
        # Create program actions.
        self.config = QAction("Settings", self)
        self.config.setShortcut("Ctrl+E")
        self.config.setStatusTip("Program Settings")
        self.config.triggered.connect(self.configuration)

        self.quit = QAction("Quit", self)
        self.quit.setShortcut("Ctrl+Q")
        self.quit.setStatusTip("Exit Program")
        self.quit.triggered.connect(self.close)

        self.about_tu = QAction("About Threadlink Utility", self)
        self.about_tu.setShortcut("Ctrl+U")
        self.about_tu.setStatusTip("About Program")
        self.about_tu.triggered.connect(self.about_program)

        self.aboutqt = QAction("About Qt", self)
        self.aboutqt.setShortcut("Ctrl+I")
        self.aboutqt.setStatusTip("About Qt")
        self.aboutqt.triggered.connect(self.about_qt)

        # Create menubar
        self.menubar = self.menuBar()
        self.file_menu = self.menubar.addMenu("&File")
        self.file_menu.addAction(self.config)
        self.file_menu.addAction(self.quit)

        self.serial_menu = self.menubar.addMenu("&Serial")
        self.serial_menu.installEventFilter(self)
        self.ports_menu = QMenu("&Ports", self)
        self.serial_menu.addMenu(self.ports_menu)
        self.ports_menu.aboutToShow.connect(self.populate_ports)
        self.ports_group = QActionGroup(self)
        self.ports_group.triggered.connect(self.connect_port)

        self.help_menu = self.menubar.addMenu("&Help")
        self.help_menu.addAction(self.about_tu)
        self.help_menu.addAction(self.aboutqt)

        self.initUI()
        self.center()

    def center(self):
        """Centers the application on the screen the mouse pointer is
        currently on."""
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(
            QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())
        
    def resource_path(self, relative_path):
        """Gets the path of the application relative root path to allow us
        to find the logo."""
        if hasattr(sys, '_MEIPASS'):
             return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def initUI(self):
        """"Sets up the UI."""
        RIGHT_SPACING = 350
        LINE_EDIT_WIDTH = 200
        self.central_widget = QWidget()

        self.tester_id_lbl = QLabel("Please enter tester ID: ")
        self.tester_id_lbl.setFont(self.label_font)
        self.pcba_pn_lbl = QLabel("Please select PCBA part number: ")
        self.pcba_pn_lbl.setFont(self.label_font)
        self.pcba_sn_lbl = QLabel("Please enter or scan DUT serial number: ")
        self.pcba_sn_lbl.setFont(self.label_font)

        self.tester_id_input = QLineEdit()
        self.pcba_sn_input = QLineEdit()
        self.tester_id_input.setFixedWidth(LINE_EDIT_WIDTH)
        self.pcba_sn_input.setFixedWidth(LINE_EDIT_WIDTH)

        self.pcba_pn_input = QComboBox()
        self.pcba_pn_input.addItem("45211-01")
        self.pcba_pn_input.setFixedWidth(LINE_EDIT_WIDTH)

        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedWidth(200)
        self.start_btn.setAutoDefault(True)
        self.start_btn.clicked.connect(self.parse_values)

        self.logo_img = QPixmap(self.resource_path("h_logo.png"))
        self.logo_img = self.logo_img.scaledToWidth(600)
        self.logo = QLabel()
        self.logo.setPixmap(self.logo_img)

        hbox_logo = QHBoxLayout()
        hbox_logo.addStretch()
        hbox_logo.addWidget(self.logo)
        hbox_logo.addStretch()

        hbox_test_id = QHBoxLayout()
        hbox_test_id.addStretch()
        hbox_test_id.addWidget(self.tester_id_lbl)
        hbox_test_id.addWidget(self.tester_id_input)
        hbox_test_id.addSpacing(RIGHT_SPACING)

        hbox_pn = QHBoxLayout()
        hbox_pn.addStretch()
        hbox_pn.addWidget(self.pcba_pn_lbl)
        hbox_pn.addWidget(self.pcba_pn_input)
        hbox_pn.addSpacing(RIGHT_SPACING)

        hbox_sn = QHBoxLayout()
        hbox_sn.addStretch()
        hbox_sn.addWidget(self.pcba_sn_lbl)
        hbox_sn.addWidget(self.pcba_sn_input)
        hbox_sn.addSpacing(RIGHT_SPACING)

        hbox_start_btn = QHBoxLayout()
        hbox_start_btn.addStretch()
        hbox_start_btn.addWidget(self.start_btn)
        hbox_start_btn.addSpacing(RIGHT_SPACING)

        vbox = QVBoxLayout()
        vbox.addStretch()
        vbox.addLayout(hbox_logo)
        vbox.addSpacing(100)
        vbox.addLayout(hbox_test_id)
        vbox.addSpacing(50)
        vbox.addLayout(hbox_pn)
        vbox.addSpacing(50)
        vbox.addLayout(hbox_sn)
        vbox.addSpacing(50)
        vbox.addLayout(hbox_start_btn)
        vbox.addStretch()

        self.central_widget.setLayout(vbox)
        self.setCentralWidget(self.central_widget)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowTitle("BeadedStream Manufacturing Threadlink Test Utility")

    def create_messagebox(self, type, title, text, info_text):
        """A helper method for creating message boxes."""
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
        msgbox.setInformativeText(info_text)
        if type == "Warning":
            msgbox.setIcon(QMessageBox.Warning)
        elif type == "Error":
            msgbox.setIcon(QMessageBox.Error)
        elif type == "Information":
            msgbox.setIcon(QMessageBox.Information)
        else:
            raise InvalidMsgType
        return msgbox

    def about_program(self):
        """Displays information about the program."""
        QMessageBox.about(self, "About Threadlink Test Utility", ABOUT_TEXT)

    def about_qt(self):
        """Displays information about Qt."""
        QMessageBox.aboutQt(self, "About Qt")

    def populate_ports(self):
        """Populates ports menu from connected COM ports."""
        ports = serialmanager.SerialManager.scan_ports()
        self.ports_menu.clear()

        if not ports:
            self.ports_menu.addAction("None")
            self.sm.close_port()

        for port in ports:
            port_description = port.description
            action = self.ports_menu.addAction(port_description)
            port_name = port.device
            if self.sm.is_connected(port_name):
                action.setCheckable(True)
                action.setChecked(True)
            self.ports_group.addAction(action)

    def connect_port(self, action: QAction):
        """Connects to a COM port by parsing the text from a clicked QAction
        menu object."""

        p = "COM[0-9]+"
        m = re.search(p, action.text())
        if m:
            port_name = m.group()
            if (self.sm.is_connected(port_name)):
                action.setChecked
            self.sm.open_port(port_name)
        else:
            QMessageBox.warning(self, "Warning", "Invalid port selection!")

    def port_unavailable(self):
        """Displays warning message about unavailable port."""
        QMessageBox.warning(self, "Warning", "Port unavailable!")

    def parse_values(self):
        """Parses and validates input values from the start page."""
        self.tester_id = self.tester_id_input.text().upper()
        self.pcba_pn = self.pcba_pn_input.currentText()
        self.pcba_sn = self.pcba_sn_input.text().upper()

        if (self.tester_id and self.pcba_pn and self.pcba_sn):

            # The serial number should be seven characters long and start with
            # the specific prefix for the given product.
            if (self.pcba_sn[0:3] == self.product_data[self.pcba_pn][0] and
                    len(self.pcba_sn) == 7):
                self.r.write_data("tester_id", self.tester_id, "PASS")
                self.r.write_data("pcba_sn", self.pcba_sn, "PASS")
                self.r.write_data("pcba_pn", self.pcba_pn, "PASS")
            else:
                self.err_msg = self.create_messagebox("Warning", "Error",
                                                      "Error",
                                                      "Bad serial number!")
                self.err_msg.show()
                return
        else:
            self.err_msg = self.create_messagebox("Warning", "Error",
                                                  "Error", "Missing value!")
            self.err_msg.show()
            return

        self.start_procedure()

    def start_procedure(self):
        """Sets up procedure layout by creating test statuses and initializing
        the appropriate board class (currently D505, potentially others in 
        the future)."""
        central_widget = QWidget()

        status_lbl_stylesheet = ("QLabel {border: 2px solid grey;"
                                 "color: black; font-size: 20px}")
        status_style_pass = """QLabel {background: #8cff66;
                                border: 2px solid grey; font-size: 20px}"""

        # ______Labels______
        self.tester_id_status = QLabel(f"Tester ID: {self.tester_id}")
        self.pcba_pn_status = QLabel(f"PCBA PN: {self.pcba_pn}")
        self.pcba_sn_status = QLabel(f"PCBA SN: {self.pcba_sn}")
        self.input_i_status = QLabel(f"Input Current: _____ mA")
        self.supply_5v_status = QLabel("5V Supply: _____V")
        self.output_2p5v_status = QLabel("2.5V Output: _____V")
        self.supply_1p8v_status = QLabel("1.8V Supply: _____V")

        self.xmega_prog_status = QLabel("XMega Programming: _____")
        self.uart_5v_status = QLabel("5V UART: _____ V")
        self.uart_off_status = QLabel("5V Off: _____ V")
        self.one_wire_prog_status = QLabel("1-Wire Master Programming:_____")
        self.ble_prog_status = QLabel("BLE Programming:_____")
        self.bluetooth_test_status = QLabel("Bluetooth Test:_____")
        self.xmega_inter_status = QLabel("Xmega Interfaces:_____")
        self.hall_effect_status = QLabel("Hall Effect Sensor Test:_____")
        self.led_test_status = QLabel("LED Test:_____")
        self.solar_charge_v_status = QLabel("Solar Charge Voltage:_____V")
        self.solar_charge_i_status = QLabel("Solar Charge Current:_____mA")
        self.deep_sleep_i_status = QLabel("Deep Sleep Current:_____uA")

        self.tester_id_status.setStyleSheet(status_style_pass)
        self.pcba_pn_status.setStyleSheet(status_style_pass)
        self.pcba_sn_status.setStyleSheet(status_style_pass)
        self.input_i_status.setStyleSheet(status_lbl_stylesheet)
        self.supply_5v_status.setStyleSheet(status_lbl_stylesheet)
        self.output_2p5v_status.setStyleSheet(status_lbl_stylesheet)
        self.supply_1p8v_status.setStyleSheet(status_lbl_stylesheet)

        self.xmega_prog_status.setStyleSheet(status_lbl_stylesheet)
        self.supply_5v_status.setStyleSheet(status_lbl_stylesheet)
        self.uart_5v_status.setStyleSheet(status_lbl_stylesheet)
        self.uart_off_status.setStyleSheet(status_lbl_stylesheet)
        self.one_wire_prog_status.setStyleSheet(status_lbl_stylesheet)
        self.ble_prog_status.setStyleSheet(status_lbl_stylesheet)
        self.bluetooth_test_status.setStyleSheet(status_lbl_stylesheet)
        self.xmega_inter_status.setStyleSheet(status_lbl_stylesheet)
        self.hall_effect_status.setStyleSheet(status_lbl_stylesheet)
        self.led_test_status.setStyleSheet(status_lbl_stylesheet)
        self.solar_charge_v_status.setStyleSheet(status_lbl_stylesheet)
        self.solar_charge_i_status.setStyleSheet(status_lbl_stylesheet)
        self.deep_sleep_i_status.setStyleSheet(status_lbl_stylesheet)

        # ______Layout______
        status_vbox1 = QVBoxLayout()
        status_vbox1.setSpacing(10)
        status_vbox1.addWidget(self.tester_id_status)
        status_vbox1.addWidget(self.pcba_pn_status)
        status_vbox1.addWidget(self.pcba_sn_status)
        status_vbox1.addWidget(self.input_i_status)
        status_vbox1.addWidget(self.supply_5v_status)
        status_vbox1.addWidget(self.output_2p5v_status)
        status_vbox1.addWidget(self.supply_1p8v_status)

        status_vbox1.addWidget(self.xmega_prog_status)
        status_vbox1.addWidget(self.supply_5v_status)
        status_vbox1.addWidget(self.uart_5v_status)
        status_vbox1.addWidget(self.uart_off_status)
        status_vbox1.addWidget(self.one_wire_prog_status)
        status_vbox1.addWidget(self.ble_prog_status)
        status_vbox1.addWidget(self.bluetooth_test_status)
        status_vbox1.addWidget(self.xmega_inter_status)
        status_vbox1.addWidget(self.hall_effect_status)
        status_vbox1.addWidget(self.led_test_status)
        status_vbox1.addWidget(self.solar_charge_v_status)
        status_vbox1.addWidget(self.solar_charge_i_status)
        status_vbox1.addWidget(self.deep_sleep_i_status)
        status_vbox1.addStretch()

        status_group = QGroupBox("Test Statuses")
        status_group.setFont(self.label_font)
        status_group.setLayout(status_vbox1)

        # Use the product data dictionary to call the procdure class that
        # corresponds to the part number. Create an instance of it passing it
        # the instances of test_utility, model, serial_manager and report.
        self.procedure = self.product_data[self.pcba_pn][1](self, self.m,
                                                            self.sm, self.r)

        grid = QGridLayout()
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 15)
        grid.addWidget(status_group, 0, 0, Qt.AlignTop)
        grid.addWidget(self.procedure, 0, 1)

        # layout = QHBoxLayout()
        # layout.addWidget(self.procedure)

        central_widget.setLayout(grid)

        self.setCentralWidget(central_widget)

    def configuration(self):
        """Sets up configuration/settings window elements."""
        FILE_BTN_WIDTH = 30

        self.settings_widget = QDialog(self)

        port1_lbl = QLabel("Port 1 TAC ID:")
        port1_lbl.setFont(self.config_font)
        self.port1_tac_id = QLineEdit(self.settings.value("port1_tac_id"))
        port2_lbl = QLabel("Port 2 TAC ID:")
        port2_lbl.setFont(self.config_font)
        self.port2_tac_id = QLineEdit(self.settings.value("port2_tac_id"))
        port3_lbl = QLabel("Port 3 TAC ID:")
        port3_lbl.setFont(self.config_font)
        self.port3_tac_id = QLineEdit(self.settings.value("port3_tac_id"))
        port4_lbl = QLabel("Port 4 TAC ID:")
        port4_lbl.setFont(self.config_font)
        self.port4_tac_id = QLineEdit(self.settings.value("port4_tac_id"))

        port_layout = QGridLayout()
        port_layout.addWidget(port1_lbl, 0, 0)
        port_layout.addWidget(self.port1_tac_id, 0, 1)
        port_layout.addWidget(port2_lbl, 1, 0)
        port_layout.addWidget(self.port2_tac_id, 1, 1)
        port_layout.addWidget(port3_lbl, 2, 0)
        port_layout.addWidget(self.port3_tac_id, 2, 1)
        port_layout.addWidget(port4_lbl, 3, 0)
        port_layout.addWidget(self.port4_tac_id, 3, 1)

        port_group = QGroupBox("TAC IDs")
        port_group.setLayout(port_layout)

        self.hex_btn = QPushButton("[...]")
        self.hex_btn.setFixedWidth(FILE_BTN_WIDTH)
        self.hex_btn.clicked.connect(self.set_hex_dir)
        self.hex_lbl = QLabel("Choose the location of hex files: ")
        self.hex_lbl.setFont(self.config_font)
        self.hex_path_lbl = QLabel(self.settings.value("hex_files_path"))
        self.hex_path_lbl.setFont(self.config_path_font)
        self.hex_path_lbl.setStyleSheet("QLabel {color: blue}")

        self.report_btn = QPushButton("[...]")
        self.report_btn.setFixedWidth(FILE_BTN_WIDTH)
        self.report_btn.clicked.connect(self.set_report_location)
        self.report_lbl = QLabel("Set report save location: ")
        self.report_lbl.setFont(self.config_font)
        self.report_path_lbl = QLabel(self.settings.value("report_file_path"))
        self.report_path_lbl.setFont(self.config_path_font)
        self.report_path_lbl.setStyleSheet("QLabel {color: blue}")

        self.atprogram_btn = QPushButton("[...]")
        self.atprogram_btn.setFixedWidth(FILE_BTN_WIDTH)
        self.atprogram_btn.clicked.connect(self.choose_atprogram_file)
        self.atprogram_lbl = QLabel("Select atprogram.exe.")
        self.atprogram_lbl.setFont(self.config_font)
        self.atprogram_path_lbl = QLabel(self.settings.value(
            "atprogram_file_path"))
        self.atprogram_path_lbl.setFont(self.config_path_font)
        self.atprogram_path_lbl.setStyleSheet("QLabel {color: blue}")

        save_loc_layout = QGridLayout()
        save_loc_layout.addWidget(self.hex_lbl, 0, 0)
        save_loc_layout.addWidget(self.hex_btn, 0, 1)
        save_loc_layout.addWidget(self.hex_path_lbl, 1, 0)
        save_loc_layout.addWidget(self.report_lbl, 2, 0)
        save_loc_layout.addWidget(self.report_btn, 2, 1)
        save_loc_layout.addWidget(self.report_path_lbl, 3, 0)
        save_loc_layout.addWidget(self.atprogram_lbl, 4, 0)
        save_loc_layout.addWidget(self.atprogram_btn, 4, 1)
        save_loc_layout.addWidget(self.atprogram_path_lbl, 5, 0)

        save_loc_group = QGroupBox("Save Locations")
        save_loc_group.setLayout(save_loc_layout)

        apply_btn = QPushButton("Apply Settings")
        apply_btn.clicked.connect(self.apply_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancel_settings)

        button_layout = QHBoxLayout()
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(apply_btn)

        hbox_top = QHBoxLayout()
        hbox_top.addWidget(port_group)

        hbox_bottom = QHBoxLayout()
        # hbox_bottom.addStretch()
        hbox_bottom.addWidget(save_loc_group)
        # hbox_bottom.addStretch()

        grid = QGridLayout()
        grid.addLayout(hbox_top, 0, 0)
        grid.addLayout(hbox_bottom, 1, 0)
        grid.addLayout(button_layout, 2, 0)
        grid.setHorizontalSpacing(100)

        self.settings_widget.setLayout(grid)
        self.settings_widget.setWindowTitle("Threadlink Configuration Settings")
        self.settings_widget.show()
        # self.settings_widget.resize(800, 600)

        # frameGm = self.frameGeometry()
        # screen = QApplication.desktop().screenNumber(
        #     QApplication.desktop().cursor().pos())
        # centerPoint = QApplication.desktop().screenGeometry(screen).center()
        # frameGm.moveCenter(centerPoint)
        # self.settings_widget.move(frameGm.topLeft())

    def set_hex_dir(self):
        """Opens file dialog for selecting the hex files directory."""

        hex_files_path = QFileDialog.getExistingDirectory(
            self,
            "Select hex files directory."
        )
        self.hex_path_lbl.setText(hex_files_path)

    def set_report_location(self):
        """Opens file dialog for setting the save location for the report."""

        report_dir = QFileDialog.getExistingDirectory(
            self,
            "Select report save location."
        )
        self.report_path_lbl.setText(report_dir)

    def choose_atprogram_file(self):
        """Opens file dialog for selecting the atprogram executable."""

        atprogram_file_path = QFileDialog.getOpenFileName(
            self,
            "Select atprogram.exe.",
            "",
            "Application (*.exe)"
        )[0]
        self.atprogram_path_lbl.setText(atprogram_file_path)

    def cancel_settings(self):
        """Close the settings widget without applying changes."""

        self.settings_widget.close()

    def apply_settings(self):
        """Read user inputs and apply settings."""

        tac_ports = {
            "port1_tac_id": self.port1_tac_id,
            "port2_tac_id": self.port2_tac_id,
            "port3_tac_id": self.port3_tac_id,
            "port4_tac_id": self.port4_tac_id
        }

        for key, tac_port in tac_ports.items():
            p = r"([a-fA-F0-9]){8}"
            if (re.fullmatch(p, tac_port.text())):
                self.settings.setValue(key, tac_port.text())

            else:
                QMessageBox.warning(self.settings_widget,
                                    "Warning!",
                                    f"Bad TAC ID on Port {key[4]}!\n"
                                    "IDs are 8 digit hex values.\n"
                                    "E.g.: 000a5296")
                return

        self.settings.setValue("iridium_imei", self.iridium_imei.text())
        self.settings.setValue("lat_start", self.lat_start.text())
        self.settings.setValue("lat_stop", self.lat_stop.text())
        self.settings.setValue("lon_start", self.lon_start.text())
        self.settings.setValue("lon_stop", self.lon_stop.text())
        self.settings.setValue("hex_files_path", self.hex_path_lbl.text())
        self.settings.setValue("report_file_path", self.report_path_lbl.text())
        self.settings.setValue("atprogram_file_path",
                               self.atprogram_path_lbl.text())

        QMessageBox.information(self.settings_widget, "Information",
                                "Settings applied!")

        self.settings_widget.close()

    def closeEvent(self, event):
        """Override QWidget closeEvent to provide user with confirmation
        dialog and ensure threads are terminated appropriately."""

        event.accept()

        quit_msg = "Are you sure you want to exit the program?"
        confirmation = QMessageBox.question(self, 'Message',
                                            quit_msg, QMessageBox.Yes,
                                            QMessageBox.No)

        if confirmation == QMessageBox.Yes:
            self.serial_thread.quit()
            self.serial_thread.wait()
            event.accept()
        else:
            event.ignore()
