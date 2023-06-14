import sys
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QFileDialog
)
from PyQt5.QtCore import QThread, QSettings, Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
import re
import subprocess
import sys
import platform
import os
from fontbakery.commands.check_profile import log_levels
from fontbakery.profile import get_module_profile
from importlib import import_module

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

class CheckCombo(QComboBox):
    def __init__(self, profile):
        super().__init__()
        imported = import_module("fontbakery.profiles."+profile)
        profile = get_module_profile(imported)
        self.setMaxVisibleItems(10)
        self.setStyleSheet("combobox-popup: 0;")
        self.profile = profile
        for _, section in profile._sections.items():
            self.addItem(section.name)
            item = self.model().item(self.count()-1,0)
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            item.setFlags(item.flags() &  ~Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)

            for check in section._checks:
                self.addItem(check.description,userData = check.id)
                item = self.model().item(self.count()-1,0)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
        self.adjustSize()

    def checked_checks(self):
        rv = []
        for i in range(0, self.count()):
            item = self.model().item(i)
            if item.checkState() != Qt.Checked or not self.itemData(i):
                continue
            rv.append(self.itemData(i))
        return rv

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return QSize(50, super().minimumSizeHint().height())


class ResultsWidget(QWidget):
    def __init__(self, html, markdown):
        super(ResultsWidget, self).__init__()
        self.markdown = markdown
        QBtn = QDialogButtonBox.Ok
        self.layout = QVBoxLayout()
        self.webrenderer = QWebEngineView()
        self.webrenderer.setHtml(html)
        self.layout.addWidget(self.webrenderer)
        self.setMinimumHeight(400)

        if platform.system() in ["Darwin", "Windows"]:
            self.mdbutton = QPushButton("Copy Markdown to clipboard")
            self.mdbutton.clicked.connect(self.md_to_clipboard)
            self.layout.addWidget(self.mdbutton)
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
        self.settings = QSettings()
        geometry = self.settings.value('mainwindowgeometry', '')
        if geometry:
            self.restoreGeometry(geometry)
        self.vlayout = QVBoxLayout()
        self.layout = QVBoxLayout()
        self.left = QWidget()
        self.left.setLayout(self.vlayout)
        self.right = QWidget()
        self.layout.addWidget(self.left)
        self.layout.addWidget(self.right)
        self.setLayout(self.layout)
        self.vlayout.addWidget(QLabel("Choose profile to check:"))
        self.profilewidget = QComboBox()
        for p in CLI_PROFILES:
            self.profilewidget.addItem(p)
        last_used_profile = self.settings.value("last_used_profile", "")
        if last_used_profile:
            self.profilewidget.setCurrentText(last_used_profile)
        self.vlayout.addWidget(self.profilewidget)

        self.profilewidget.currentIndexChanged.connect(self.profile_changed)

        self.vlayout.addWidget(QLabel("Choose checks to run:"))
        self.checkwidget = CheckCombo(self.profilewidget.currentText())
        self.vlayout.addWidget(self.checkwidget)

        self.vlayout.addWidget(QLabel("Choose level of output:"))
        self.loglevelwidget = QComboBox()
        for l in log_levels.keys():
            self.loglevelwidget.addItem(l)
        self.loglevelwidget.setCurrentText("INFO")
        self.vlayout.addWidget(self.loglevelwidget)

        self.vlayout.addWidget(DragDropArea(self))

        self.progress = QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.vlayout.addWidget(self.progress)
        self.vlayout.addStretch()

    def run_fontbakery(self, paths):
        self.progress.setValue(0)
        # Setup the worker object and the worker_thread.
        profilename = self.profilewidget.currentText()
        loglevel = log_levels[self.loglevelwidget.currentText()]
        self.settings.setValue('last_used_profile', profilename)
        print("checked_checks", self.checkwidget.checked_checks())
        self.worker = FontbakeryRunner(profilename, [loglevel], paths, checks=self.checkwidget.checked_checks())
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
        self.layout.removeWidget(self.right)
        self.right.deleteLater()
        self.right = ResultsWidget(html, md)
        self.layout.addWidget(self.right)

    def profile_changed(self):
        index = self.vlayout.indexOf(self.checkwidget)
        self.vlayout.removeWidget(self.checkwidget)
        self.checkwidget.deleteLater()
        self.checkwidget = CheckCombo(self.profilewidget.currentText())
        self.vlayout.insertWidget(index, self.checkwidget)

    def closeEvent(self, event):
        geometry = self.saveGeometry()
        self.settings.setValue('mainwindowgeometry', geometry)


# # start my_app
my_app = QApplication(sys.argv)
my_app.setApplicationName("FontBakery")
my_app.setOrganizationDomain("fonts.google.com")

mainwindow = MainWindow()
mainwindow.raise_()
mainwindow.adjustSize()
mainwindow.setMinimumWidth(400)
mainwindow.show()
ver = needs_update()
if ver:
    update_dialog(ver)
sys.exit(my_app.exec_())
