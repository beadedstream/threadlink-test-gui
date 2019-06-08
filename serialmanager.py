import time
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class SerialManager(QObject):
    """Class that handles the serial connection."""
    data_ready = pyqtSignal(str)
    no_port_sel = pyqtSignal()
    sleep_finished = pyqtSignal()
    line_written = pyqtSignal()
    flash_test_succeeded = pyqtSignal()
    flash_test_failed = pyqtSignal()
    gps_test_succeeded = pyqtSignal()
    gps_test_failed = pyqtSignal()
    serial_test_succeeded = pyqtSignal(str)
    serial_test_failed = pyqtSignal(str)
    rtc_test_succeeded = pyqtSignal()
    rtc_test_failed = pyqtSignal()
    port_unavailable_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ser = serial.Serial(None, 115200, timeout=45,
                                 parity=serial.PARITY_NONE, rtscts=False,
                                 xonxoff=False, dsrdtr=False)
        self.end = b"\r\n>"

    def scan_ports():
        """Scan and return list of connected comm ports."""
        return serial.tools.list_ports.comports()

    @pyqtSlot(str)
    def send_command(self, command):
        """Checks connection to the serial port and sends a command."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                command = (command + "\r\n").encode()
                self.ser.write(command)
                data = self.ser.read_until(self.end).decode()
                self.data_ready.emit(data)
            except serial.serialutil.SerialException:
                self.no_port_sel.emit()
        else:
            self.no_port_sel.emit()

    @pyqtSlot()
    def one_wire_test(self):
        """Sends command for one wire test and evaluates the result."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                self.ser.write("1-wire-test\r".encode())
                time.sleep(1)
                self.ser.write(" ".encode())
                time.sleep(0.3)
                self.ser.write(".".encode())
                data = self.ser.read_until(self.end).decode()
                self.data_ready.emit(data)
            except serial.serialutil.SerialException:
                self.no_port_sel.emit()
        else:
            self.no_port_sel.emit()

    @pyqtSlot()
    def reprogram_one_wire(self):
        """Sends command to reprogram one wire master."""
        if self.ser.is_open:
            try:
                self.ser.write("reprogram-1-wire-master\r\n".encode())
                # Wait for serial buffer to fill
                time.sleep(5)
                num_bytes = self.ser.in_waiting
                data = self.ser.read(num_bytes).decode()
                self.data_ready.emit(data)
            except serial.serialutil.SerialException:
                self.no_port_sel.emit()
        else:
            self.no_port_sel.emit()

    @pyqtSlot(str)
    def write_hex_file(self, file_path):
        """Writes hex file line-by-line with appropriate delay between
        each name."""
        if self.ser.is_open:
            try:
                with open(file_path, "rb") as f:
                    for line in f:
                        self.ser.write(line)
                        self.line_written.emit()
                        # minimum of 50 ms delay required after each line
                        time.sleep(0.060)
            except serial.serialutil.SerialException:
                self.no_port_sel.emit()

            time.sleep(3)
            data = self.ser.read_until(self.end).decode()
            self.data_ready.emit(data)
        else:
            self.no_port_sel.emit()

    @pyqtSlot()
    def iridium_command(self):
        """Sends commands for reading from the iridium."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                self.ser.write(b"iridium\r\n")
                time.sleep(2)
                num_bytes = self.ser.in_waiting
                self.ser.read(num_bytes)
                self.ser.write(b"at+gsn\r\n")
                time.sleep(2)
                num_bytes = self.ser.in_waiting
                data = self.ser.read(num_bytes).decode()
                self.ser.write(b".\r\n")
                time.sleep(2)
                self.ser.read_until(self.end)
                self.data_ready.emit(data)
            except serial.serialutil.SerialException:
                self.no_port_sel.emit()
        else:
            self.no_port_sel.emit()

    @pyqtSlot()
    def flash_test(self):
        """Writes dummy data to flash, checks that it was written and then 
        clears it."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                # Make sure there are no logs to start with
                self.ser.write(b"clear\r\n")
                self.ser.read_until(b"[Y/N]")
                self.ser.write(b"Y")
                self.ser.read_until(self.end)

                self.ser.write(b"flash-fill 1 3 1 1 1 1\r\n")
                self.ser.read_until(self.end)

                self.ser.write(b"data\r\n")
                data = self.ser.read_until(self.end)
                if b"... 3 records" not in data:
                    self.flash_test_failed.emit()
                    return

                self.ser.write(b"psoc-log-usage\r\n")
                data = self.ser.read_until(self.end)
                if b"used: 3" not in data:
                    self.flash_test_failed.emit()
                    return

                self.ser.write(b"clear\r\n")
                self.ser.read_until(b"[Y/N]")
                self.ser.write(b"Y")
                self.ser.read_until(self.end)

                self.ser.write(b"data\r\n")
                data = self.ser.read_until(self.end)
                if b"No data!" not in data:
                    self.flash_test_failed.emit()
                    return

                self.ser.write(b"psoc-log-usage\r\n")
                data = self.ser.read_until(self.end)
                if b"used: 0" not in data:
                    self.flash_test_failed.emit()
                    return
                self.flash_test_succeeded.emit()

            except serial.serialutil.SerialException:
                self.no_port_sel.emit()
        else:
            self.no_port_sel.emit()

    @pyqtSlot()
    def gps_test(self):
        """Checks that the board has communication with the GPS module."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                self.ser.write(b"gps-rx\r\n")
                time.sleep(0.3)
                # Throw away 'gps-rx' command echo
                self.ser.read_until(b"\r\n")
                # Read first line of GPS data
                data = self.ser.read_until(b"\r\n")
                # Stop gps data
                self.ser.write(b".\r\n")

                if b"$GNTXT" not in data:
                    self.gps_test_failed.emit()
                    return

                self.gps_test_succeeded.emit()

            except serial.serialutil.SerialException:
                self.no_port_sel.emit()

    @pyqtSlot(str)
    def set_serial(self, serial_num):
        """Sets the serial port."""
        if self.ser.is_open:
            try:
                self.flush_buffers
                s = serial_num + "\r\n"
                self.ser.write(s.encode())
                time.sleep(0.3)
                data = self.ser.read_until(self.end).decode()
                # Try to get serial number twice
                if serial_num not in data:
                    self.flush_buffers
                    self.ser.write(s.encode())
                    time.sleep(0.3)
                    data = self.ser.read_until(self.end).decode()
                    if serial_num not in data:
                        self.serial_test_failed.emit(data)
                        return
                self.serial_test_succeeded.emit(serial_num)

            except serial.serialutil.SerialException:
                self.no_port_sel.emit()

    @pyqtSlot()
    def rtc_test(self):
        """Sets the time, sets an alarm and then checks that the alert
        is set."""
        if self.ser.is_open:
            try:
                self.flush_buffers
                # Make sure D505 app is off.
                self.ser.write(b"app 0\r\n")
                time.sleep(0.5)
                self.ser.read_until(self.end)
                self.ser.write(b"rtc-set 030719 115955\r\n")
                time.sleep(0.5)
                self.ser.read_until(self.end)
                self.ser.write(b"rtc-alarm 12:00\r\n")
                time.sleep(0.5)
                self.ser.read_until(self.end)
                time.sleep(0.5)
                self.ser.write(b"rtc-alarmed\r\n")
                data = self.ser.read_until(self.end).decode()
                if "0" not in data:
                    self.rtc_test_failed.emit()
                    return

                time.sleep(5)
                self.ser.write(b"rtc-alarmed\r\n")
                time.sleep(0.5)
                data = self.ser.read_until(self.end).decode()
                if "1" not in data:
                    self.rtc_test_failed.emit()
                    return

                self.rtc_test_succeeded.emit()

            except serial.serialutil.SerialException:
                self.no_port_sel.emit()

    @pyqtSlot(int)
    def sleep(self, interval):
        """Wait for a specified time period."""
        time.sleep(interval)
        self.sleep_finished.emit()

    def is_connected(self, port):
        """Checks for serial connection."""
        try:
            self.ser.write(b"\r\n")
            time.sleep(0.1)
            self.ser.read(self.ser.in_waiting)
        except serial.serialutil.SerialException:
            return False
        return self.ser.port == port and self.ser.is_open

    def open_port(self, port):
        """Opens serial port."""
        try:
            self.ser.close()
            self.ser.port = port
            self.ser.open()
        except serial.serialutil.SerialException:
            self.port_unavailable_signal.emit()

    def flush_buffers(self):
        """Flushes the serial buffer by writing to the buffer and then reading
        all the available bytes."""
        self.ser.write("\r\n".encode())
        time.sleep(0.5)
        self.ser.read(self.ser.in_waiting)

    def close_port(self):
        """Closes serial port."""
        self.ser.close()
