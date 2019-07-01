import time
import serial
import re
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class SerialManager(QObject):
    """Class that handles the serial connection."""
    data_ready = pyqtSignal(str)
    no_port_sel = pyqtSignal()
    no_port_sel_batch = pyqtSignal()
    no_port_sel_onewire = pyqtSignal()
    sleep_finished = pyqtSignal()
    line_written = pyqtSignal()
    flash_test_succeeded = pyqtSignal()
    flash_test_failed = pyqtSignal()
    serial_test_succeeded = pyqtSignal(str)
    serial_test_failed = pyqtSignal(str)
    port_unavailable_signal = pyqtSignal()
    version_signal = pyqtSignal(str)
    no_version = pyqtSignal()
    serial_error_signal = pyqtSignal()
    file_not_found_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ser = serial.Serial(None, 115200, timeout=15,
                                 parity=serial.PARITY_NONE, rtscts=False,
                                 xonxoff=False, dsrdtr=False)
        self.end = b"\r\n>"

    def scan_ports():
        """Scan and return list of connected comm ports."""
        return serial.tools.list_ports.comports()

    def rs485_write_command(self, command: str):
        """Write a command by sending individual chars and wait for echo back,
           because its a RS485 interface: half-duplex with no control flow.
        """
        for c in command:
            self.ser.write(c.encode())
            self.ser.flush()
            time.sleep(0.05)
            self.ser.read(self.ser.in_waiting)

        self.ser.write(b"\r\n")
        self.ser.flush()
        time.sleep(0.1)

    @pyqtSlot(str)
    def send_command(self, command):
        """Checks connection to the serial port and sends a command."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                self.rs485_write_command(command)

                try:
                    response = self.ser.read_until(self.end).decode()
                    self.data_ready.emit(response)
                except UnicodeDecodeError:
                    self.serial_error_signal.emit()
                    return

            except serial.serialutil.SerialException:
                self.no_port_sel.emit()
        else:
            self.no_port_sel.emit()

    @pyqtSlot()
    def version_check(self):
        command = "version"
        p = r"[0-9]+\.[0-9]+[a-z]"
        if self.ser.is_open:
            try:
                self.flush_buffers()

                self.rs485_write_command(command)

                try:
                    response = self.ser.read_until(self.end).decode()
                except UnicodeDecodeError:
                    self.serial_error_signal.emit()
                    return

                # Ensure version matches format, otherwise emit error signal.
                if re.search(p, response):
                    self.version_signal.emit(re.search(p, response).group())
                    return
                else:
                    self.no_version.emit()
                    return

            except serial.serialutil.SerialException:
                self.port_unavailable_signal.emit()
        else:
            self.no_port_sel_batch.emit()

    @pyqtSlot()
    def one_wire_test(self):
        """Sends command for one wire test and evaluates the result."""
        if self.ser.is_open:
            try:
                self.flush_buffers()

                self.rs485_write_command("1-wire-test")
                time.sleep(0.5)
                self.ser.write(" ".encode())
                time.sleep(0.3)
                self.ser.write(".".encode())
                data = self.ser.read_until(self.end).decode()
                self.data_ready.emit(data)
            except serial.serialutil.SerialException:
                self.no_port_sel_onewire.emit()
        else:
            self.no_port_sel_onewire.emit()

    @pyqtSlot()
    def reprogram_one_wire(self):
        """Sends command to reprogram one wire master."""
        if self.ser.is_open:
            try:
                self.rs485_write_command("reprogram-1-wire-master")
                # Wait for serial buffer to fill
                time.sleep(5)
                num_bytes = self.ser.in_waiting
                data = self.ser.read(num_bytes).decode()
                self.data_ready.emit(data)
            except serial.serialutil.SerialException:
                self.no_port_sel_onewire.emit()
        else:
            self.no_port_sel_onewire.emit()

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
                self.no_port_sel_onewire.emit()
            except FileNotFoundError:
                self.file_not_found_signal.emit("1-wire-master")


            time.sleep(3)
            data = self.ser.read_until(self.end).decode()
            self.data_ready.emit(data)
        else:
            self.no_port_sel_onewire.emit()

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
