import os.path
from PyQt5.QtWidgets import (
    QWizardPage, QWizard, QLabel, QVBoxLayout, QCheckBox, QGridLayout,
    QLineEdit, QProgressBar, QPushButton, QMessageBox, QHBoxLayout,
    QApplication, QSizePolicy, QFileDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QThread


class FinalPage(QWizardPage):
    """Final QWizard page, displays test result."""
    def __init__(self, test_utility, report):
        self.system_font = QApplication.font().family()
        self.label_font = QFont(self.system_font, 12)

        super().__init__()

        self.tu = test_utility
        self.report = report

    def initializePage(self):
        self.report.file_not_found_signal.connect(self.file_not_found)
        self.report.generic_error_signal.connect(self.generic_error)

        # Check test result
        report_file_path = self.tu.settings.value("report_file_path")

        # if not path.isdir(report_file_path):
        #     QMessageBox.warning(self, "Warning", "Report directory does not "
        #                         "exist!\n Please specify directory.")

        self.report.set_file_location(report_file_path)
        self.report.generate_report()

        test_result = self.report.test_result

        if test_result == "PASS":
            self.test_status = "Successful"
        else:
            self.test_status = "Failed"

        self.test_status_lbl = QLabel(f"Test {self.test_status}!")
        self.test_status_lbl.setFont(self.label_font)

        self.report_location_lbl = QLabel(
            f"Report available at: {report_file_path}.")
        self.report_location_lbl.setWordWrap(True)
        self.report_location_lbl.setFont(self.label_font)

        self.break_down_lbl = QLabel("Remove power and remove DUT test "
                                     "fixture.")
        self.break_down_lbl.setFont(self.label_font)
        
        self.layout = QVBoxLayout()
        self.layout.addSpacing(100)
        self.layout.addWidget(self.test_status_lbl)
        self.layout.addSpacing(25)
        self.layout.addWidget(self.break_down_lbl)
        self.layout.addSpacing(25)
        self.layout.addWidget(self.report_location_lbl)
        self.layout.addStretch()
        self.setLayout(self.layout)
        self.setTitle("Test Completed")

    def file_not_found(self):
        QMessageBox.warning(self, "Warning", "Report directory does not "
                            "exist!\n Please specify directory.")
        report_dir = QFileDialog.getExistingDirectory(self,
            "Select report save location.")
        self.tu.settings.setValue("report_file_path", report_dir)
        self.initializePage()

    def generic_error(self):
        QMessageBox.warning(self, "Warning", "Failed to write report!")
