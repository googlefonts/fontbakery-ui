from fontbakery.commands.check_profile import get_module
from fontbakery.reporters import FontbakeryReporter
from fontbakery.reporters.html import HTMLReporter
from fontbakery.reporters.ghmarkdown import GHMarkdownReporter
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from fontbakery.checkrunner import (
    get_module_profile,
    CheckRunner,
    START,
    ENDCHECK,
    distribute_generator,
)


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


class FontbakeryRunner(QObject):
    signalStatus = pyqtSignal(str, str)
    progressStatus = pyqtSignal(float)

    def __init__(self, profilename, loglevels, paths, checks=None, parent=None):
        super(self.__class__, self).__init__(parent)
        self.paths = paths
        self.profilename = profilename
        self.loglevels = loglevels
        self.checks = checks

    @pyqtSlot()
    def start(self):
        profile = get_module_profile(
            get_module("fontbakery.profiles." + self.profilename)
        )
        print(self.checks)
        runner = CheckRunner(profile, values={"fonts": self.paths},
            config={
                "custom_order": None,
                "explicit_checks": self.checks,
                "exclude_checks": None
            }
        )
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
