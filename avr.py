import re
import subprocess
from pathlib import Path
from packaging.version import LegacyVersion
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class FlashThreadlink(QObject):
    """Class that flashes the D505 board with hex files."""
    command_succeeded = pyqtSignal(str)
    command_failed = pyqtSignal(str)
    flash_finished = pyqtSignal()
    process_error_signal = pyqtSignal()
    file_not_found_signal = pyqtSignal(str)
    version_signal = pyqtSignal(str, str, str)

    def __init__(self, atprogram_path, hex_files_path):
        super().__init__()

        # Hide console window
        self.si = subprocess.STARTUPINFO()
        self.si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.atprogram_path = atprogram_path
        self.hex_files_path = hex_files_path
        self.boot_file = Path.joinpath(hex_files_path, "boot-section.hex")
        self.app_file = Path.joinpath(hex_files_path, "app-section.hex")
        self.main_file = None
        self.commands = None

    def check_files(self):

        if not self.boot_file.is_file():
            self.file_not_found_signal.emit(str(self.boot_file))
            return

        if not self.app_file.is_file():
            self.file_not_found_signal.emit(str(self.app_file))
            return

        main_files = list(self.hex_files_path.glob("main-app*.hex"))
        main_file, main_app_ver = FlashThreadlink.get_latest_version(main_files)

        if not main_file:
            self.file_not_found_signal.emit(str(self.main_file))
            return

        one_wire_files = list(self.hex_files_path.glob("1-wire-master*.hex"))
        one_wire_file, one_wire_ver = FlashThreadlink.get_latest_version(one_wire_files)

        chip_erase = [self.atprogram_path,
                      "-t", "avrispmk2",
                      "-i", "pdi",
                      "-d", "atxmega128a4u",
                      "chiperase"]
        prog_boot = [self.atprogram_path,
                     "-t", "avrispmk2",
                     "-i", "pdi",
                     "-d", "atxmega256a3",
                     "program",
                     "--flash", "-f", str(self.boot_file),
                     "--format", "hex",
                     "--verify"]
        prog_app = [self.atprogram_path,
                    "-t", "avrispmk2",
                    "-i", "pdi",
                    "-d", "atxmega128a4u",
                    "program",
                    "--flash", "-f", str(self.app_file),
                    "--format", "hex",
                    "--verify"]
        prog_main = [self.atprogram_path,
                     "-t", "avrispmk2",
                     "-i", "pdi",
                     "-d", "atxmega128a4u",
                     "program",
                     "--flash", "-f", str(main_file),
                     "--format", "hex",
                     "--verify"]
        write_fuses = [self.atprogram_path,
                       "-t", "avrispmk2",
                       "-i", "pdi",
                       "-d", "atxmega128a4u",
                       "write",
                       "--fuses", "--values", "FF00BFFFFEFF"]
        write_lockbits = [self.atprogram_path,
                          "-t", "avrispmk2",
                          "-i", "pdi",
                          "-d", "atxmega128a4u",
                          "write",
                          "--lockbits", "--values", "FC"]

        # Command status is for the subsequent step
        self.commands = {"chip_erase": chip_erase,
                         "prog_boot": prog_boot,
                         "prog_app": prog_app,
                         "prog_main": prog_main,
                         "write_fuses": write_fuses,
                         "write_lockbits": write_lockbits}
        self.version_signal.emit(main_app_ver, str(one_wire_file), one_wire_ver)

    @pyqtSlot()
    def flash(self):
        """Loops through all the commands to flash the D505 board."""

        for cmd_text, cmd in self.commands.items():
            try:
                status = subprocess.check_output(cmd,
                                                 startupinfo=self.si).decode()

                if "Firmware check OK" in status:
                    self.command_succeeded.emit(cmd_text)
                else:
                    self.command_failed.emit(cmd_text)
                    break

            except ValueError:
                self.command_failed.emit(cmd_text)
                break
            except subprocess.CalledProcessError:
                self.process_error_signal.emit()
                break
            except FileNotFoundError:
                self.file_not_found_signal.emit()
                break


        self.flash_finished.emit()

    @staticmethod
    def get_latest_version(filenames: list) -> (str, str):
        current_version = None
        current_filename = None

        for name in filenames:
            p = "([0-9]+\.[0-9]+[a-z])"
            try:
                version = re.search(p, str(name)).group()
            except AttributeError:
                continue

            if not current_version:
                current_version = version
                current_filename = name

            if LegacyVersion(version) > LegacyVersion(current_version):
                current_version = version
                current_filename = name

        return (current_filename, current_version)