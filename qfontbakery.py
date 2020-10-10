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
)
from PyQt5.QtWebEngineWidgets import *
import re
from fontbakery.checkrunner import (
    get_module_profile,
    CheckRunner,
    INFO,
    distribute_generator,
)
from fontbakery.commands.check_profile import get_module

from fontbakery.reporters.html import HTMLReporter
from qprogress import QProgressIndicator

profiles = ["googlefonts", "adobefonts", "notofonts", "opentype"]


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


class ResultsDialog(QDialog):
    def __init__(self, html):
        super(ResultsDialog, self).__init__()
        self.setWindowTitle("FontBakery Results")
        QBtn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        self.webrenderer = QWebEngineView()
        self.webrenderer.setHtml(html)
        self.layout.addWidget(self.webrenderer)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


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
        self.layout.addWidget(DragDropArea(self))
        self.progress = QProgressIndicator(self)
        self.layout.addWidget(self.progress)

    def run_fontbakery(self, paths):
        try:
            self.progress.startAnimation()

            # This job should ideally be run on a background thread...

            profilename = self.checkwidget.currentText()
            profile = get_module_profile(
                get_module("fontbakery.profiles." + profilename)
            )
            runner = CheckRunner(
                profile, values={"fonts": ["Mehr-Nastaliq-Web-version-1.0-beta.ttf"]}
            )
            hr = HTMLReporter(runner=runner, loglevels=[INFO])
            reporters = [hr.receive]
            status_generator = runner.run()
            distribute_generator(status_generator, reporters)

            self.show_html(hr.get_html())

        except Exception as e:
            raise
        finally:
            self.progress.stopAnimation()

    def show_html(self, html):
        ResultsDialog(html).exec_()


# # start my_app
my_app = QApplication(sys.argv)
mainwindow = MainWindow()
mainwindow.raise_()
mainwindow.show()
sys.exit(my_app.exec_())
