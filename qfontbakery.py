import sys
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QFileDialog
)
from PyQt5.QtCore import QThread
from PyQt5.QtWebEngineWidgets import QWebEngineView
import re
import subprocess
import sys
import platform
import os
from fontbakery.commands.check_profile import log_levels

if platform.system() == "Windows":
    import win32clipboard

os.environ["QT_MAC_WANTS_LAYER"] = "1"

print(sys.path)

import site # Needed for py2app

from qfontbakery.selfupdate import needs_update, update_dialog
from qfontbakery.dragdrop import DragDropArea
from qfontbakery.fbinterface import FontbakeryRunner

# Make hidden imports visible, for pyinstaller
import fontbakery.profiles.googlefonts
import fontbakery.profiles.adobefonts
import fontbakery.profiles.notofonts
import fontbakery.profiles.opentype
import fontbakery.profiles.universal

from fontbakery.cli import CLI_PROFILES

class ResultsDialog(QDialog):
    def __init__(self, html, markdown):
        super(ResultsDialog, self).__init__()
        self.setWindowTitle("FontBakery Results")
        self.markdown = markdown
        QBtn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        self.webrenderer = QWebEngineView()
        self.webrenderer.setHtml(html)
        self.layout.addWidget(self.webrenderer)

        if platform.system() in ["Darwin", "Windows"]:
            self.mdbutton = QPushButton("Copy Markdown to clipboard")
            self.mdbutton.clicked.connect(self.md_to_clipboard)
            self.layout.addWidget(self.mdbutton)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def md_to_clipboard(self):
        if platform.system() == "Darwin":
            self.setClipboardDataMac(self.markdown)
        else:
            self.setClipboardDataWin(self.markdown)
        self.mdbutton.setText("Copied!")

    def setClipboardDataWin(self, data):
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_TEXT, data)

    def setClipboardDataMac(self, data):
        p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        p.stdin.write(data.encode("utf-8"))
        p.stdin.close()
        retcode = p.wait()

class MainWindow(QWidget):
    def __init__(self):
        super(QWidget, self).__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Choose profile to check:"))
        self.checkwidget = QComboBox()
        for p in CLI_PROFILES:
            self.checkwidget.addItem(p)
        self.layout.addWidget(self.checkwidget)

        self.layout.addWidget(QLabel("Choose level of output:"))
        self.loglevelwidget = QComboBox()
        for l in log_levels.keys():
            self.loglevelwidget.addItem(l)
        self.loglevelwidget.setCurrentText("INFO")
        self.layout.addWidget(self.loglevelwidget)

        self.layout.addWidget(DragDropArea(self))

        self.progress = QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.layout.addWidget(self.progress)

    def run_fontbakery(self, paths):
        self.progress.setValue(0)
        # Setup the worker object and the worker_thread.
        profilename = self.checkwidget.currentText()
        loglevel = log_levels[self.loglevelwidget.currentText()]
        self.worker = FontbakeryRunner(profilename, [loglevel], paths)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.signalStatus.connect(self.show_results)
        self.worker.progressStatus.connect(self.update_progress)
        self.worker_thread.start()

    def update_progress(self, value):
        self.progress.setValue(int(value))

    def show_results(self, html, md):
        self.worker_thread.quit()
        ResultsDialog(html, md).exec_()


# # start my_app
my_app = QApplication(sys.argv)
mainwindow = MainWindow()
mainwindow.raise_()
mainwindow.show()
ver = needs_update()
if ver:
    update_dialog(ver)
sys.exit(my_app.exec_())
