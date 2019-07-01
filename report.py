import csv
from os import path
from datetime import datetime as dt
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class Report(QObject):
    """Test Report class. Tracks status of tests and creates test report.
    
    Instance Variables
    timestamp   -- Used to store the current timestamp for naming the report.
    date        -- Stores date in dd--mm--yy format.
    test_result -- Boolean storing success or failure of the sum of the tests.
    data        -- Dictionary of test variables and their results and values.

    Instance Methods
    write_data          -- Updates data model.
    set_file_location   -- Sets file path for report location.
    generate_report     -- Generates report and saves to path location.
    """
    write_error_signal = pyqtSignal()
    file_not_found_signal = pyqtSignal()
    generic_error_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        today = dt.now()
        self.timestamp = None
        self.date = f"{today.day:02d}-{today.month:02d}-{today.year}"
        self.test_result = None
        # Data format: key | [value, units, test-passed]
        self.data = {
            # key : ["Name", value, PASS/FAIL]
            "timestamp": ["Timestamp", None, "PASS"],
            "pcba_sn": ["PCBA PN", None, None],
            "pcba_pn": ["PCBA SN", None, None],
            "tester_id": ["Tester ID", None, None],
            "input_i": ["Input Current (mA)", None, None],
            "5v_supply": ["5V Supply (V)", None, None],
            "2p5v": ["2.5V Output (V)", None, None],
            "1p8v": ["1.8V Supply (V)", None, None],
            "internal_5v": ["Internal 5V (V)", None, None],
            # "xmega_bootloader": ["Xmega Bootloader Version", None, None],
            "xmega_app": ["Xmega App Version", None, None],
            "one_wire_ver": ["1WireMaster Version", None, None],
            # "serial_match": ["Serial Number Match", None, None],
            "tac_connected": ["TAC Port Connected", None, None],
            "led_test": ["LED Test", None, None],
            "eeprom_sn": ["EEPROM SN", None, None],
            "hall_effect": ["Hall-Effect Sensor Test", None, None],
        }
        self.file_path = ""

    def write_data(self, data_key, data_value, status):
        """Updates the data model with the received value and a bool
        indicating if the test passed or not. If the test failed and isn't
        already in the list of data, include it.
        """
        self.data[data_key][1] = data_value
        self.data[data_key][2] = status

    def set_file_location(self, file_path):
        """Sets the file path for the report's save location."""
        self.file_path = file_path

    def generate_report(self):
        """Writes all data in the data dictionary to an output file."""
        # Get the time again for a more accurate report timestamp.
        today = dt.now()
        self.timestamp = (
            f"{today.year}-{today.month:02d}-{today.day:02d}"
            f" {today.hour:02d}:{today.minute:02d}"
            f":{today.second}"
        )
        self.data["timestamp"][1] = self.timestamp
        # Filename-friendly timestamp
        ts = self.timestamp.replace(":", "-")
        sn = self.data["pcba_sn"][1]
        id = self.data["tester_id"][1]

        name = path.join(self.file_path, f"{sn}_{ts}-ID-{id}.csv")

        # Check for any tests that failed.
        for _, test in self.data.items():
            if test[2] == "FAIL":
                self.test_result = "FAIL"
                name = name[:-4] + "_FAIL.csv"
                break
            self.test_result = "PASS"

        try:
            with open(name, "w", newline='') as f:
                csvwriter = csv.writer(f)

                csvwriter.writerow(["Name", "Value", "Pass/Fail"])
                csvwriter.writerow(["Test Result", "", self.test_result])
                for _, test in self.data.items():
                    csvwriter.writerow([test[0], test[1], test[2]])

        except FileNotFoundError:
            self.file_not_found_signal.emit()
        except:
            self.generic_error_signal.emit()
