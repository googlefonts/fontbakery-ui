import sys
from PyQt5.QtCore import *
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
from PyQt5.QtWebEngineWidgets import *
import re
from fontbakery.checkrunner import (
    get_module_profile,
    CheckRunner,
    INFO,
    START,
    ENDCHECK,
    distribute_generator,
)
from fontbakery.commands.check_profile import get_module, log_levels
from fontbakery.reporters import FontbakeryReporter
from fontbakery.reporters.html import HTMLReporter
from fontbakery.reporters.ghmarkdown import GHMarkdownReporter
import fontbakery
import subprocess
import sys
import platform
import os

if platform.system() == "Windows":
    import win32clipboard

os.environ["QT_MAC_WANTS_LAYER"] = "1"

print(sys.path)

import site # Needed for py2app
from pip._internal import main as pipmain
import requests
import json
import os

# Make hidden imports visible, for pyinstaller
import fontbakery.profiles.googlefonts
import fontbakery.profiles.adobefonts
import fontbakery.profiles.notofonts
import fontbakery.profiles.opentype
import fontbakery.profiles.universal


profiles = ["googlefonts", "adobefonts", "notofonts", "opentype", "universal"]
url = 'https://api.github.com/repos/googlefonts/fontbakery/tags'
tag_url = 'git+git://github.com/googlefonts/fontbakery.git@v'
current = fontbakery.__version__
is_py2app = hasattr(sys, "frozen")
print(is_py2app)


def needs_update():
    try:
        r = requests.get(url).content
        info = json.loads(r)
        latest = info[0]["name"][1:]
        print(f"Version {latest} of fontbakery is available. You have {current}")
        if current != latest:
            return latest
        return None
    except Exception as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Error getting latest fontbakery version: " + str(e))
        msg.setWindowTitle("Fontbakery")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        return (None, None)

def update_dialog(ver):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(f'Version {ver} of fontbakery is available. You have {current}. Upgrade now?')
    msg.setWindowTitle("Upgrade fontbakery?")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)
    msg.buttonClicked.connect(lambda item: update_dialog_response(item, ver))
    msg.exec_()

def update_dialog_response(item, ver):
    item.parent().parent().done(0)
    if item.text() == "&No":
        return
    pipmain(["install", "--user", tag_url+ver]) # XXX
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText("Fontbakery has been upgraded. Please restart.")
    msg.setWindowTitle("Fontbakery")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
    sys.exit(1)


class ProgressReporter(FontbakeryReporter):
    def __init__(self, signal, is_async=False, runner=None):
        self.signal = signal
        super().__init__(is_async, runner)

    def receive(self, event):
        status, message, identity = event
        if status == START:
            self.count = len(message)
        elif status == ENDCHECK:
            self._tick += 1
        self.signal.emit(100 * self._tick / float(self.count))


class DragDropArea(QLabel):
    def __init__(self, parent):
        super(DragDropArea, self).__init__()
        self.parent = parent
        self.setText("Drop a font here to test")
        self.setStyleSheet("background-color: green ")
        self.setMargin(10)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and self.isAllFonts(event.mimeData()):
            self.setStyleSheet("background-color: yellow ")
            event.accept()
        else:
            self.setStyleSheet("background-color: red ")
            event.ignore()

    def isAllFonts(self, mime):
        for url in mime.urls():
            path = url.toLocalFile()
            if not re.match(r".*\.(otf|ttf|ttc|otc)$", path):
                return False
        return True

    def dragLeaveEvent(self, event):
        self.setStyleSheet("background-color: green ")

    def dropEvent(self, event):
        self.setStyleSheet("background-color: green ")
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self.parent.run_fontbakery(paths)

    def mousePressEvent(self, event):
        file = QFileDialog.getOpenFileNames(
            self, "Open font file(s)", filter="Font file (*.otf *.ttf *.ttc *.otc)"
        )
        if not file:
            return
        self.parent.run_fontbakery(file[0])
        event.accept()



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


class FontbakeryRunner(QObject):
    signalStatus = pyqtSignal(str, str)
    progressStatus = pyqtSignal(float)

    def __init__(self, profilename, loglevels, paths, parent=None):
        super(self.__class__, self).__init__(parent)
        self.paths = paths
        self.profilename = profilename
        self.loglevels = loglevels

    @pyqtSlot()
    def start(self):
        profile = get_module_profile(
            get_module("fontbakery.profiles." + self.profilename)
        )
        runner = CheckRunner(profile, values={"fonts": self.paths})
        print("Log levels: ", self.loglevels)
        hr = HTMLReporter(runner=runner, loglevels=self.loglevels)
        ghmd = GHMarkdownReporter(runner=runner, loglevels=self.loglevels)
        prog = ProgressReporter(self.progressStatus, runner=runner)
        reporters = [hr.receive, prog.receive, ghmd.receive]
        status_generator = runner.run()
        print("Starting distribute_generator")
        distribute_generator(status_generator, reporters)
        print("Done with distribute_generator")
        self.signalStatus.emit(hr.get_html(), ghmd.get_markdown())


class MainWindow(QWidget):
    def __init__(self):
        super(QWidget, self).__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Choose profile to check:"))
        self.checkwidget = QComboBox()
        for p in profiles:
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
