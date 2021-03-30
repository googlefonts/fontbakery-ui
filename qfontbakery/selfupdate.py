from pip._internal import main as pipmain
import requests
import json
import os
import fontbakery
import sys
from PyQt5.QtWidgets import (
    QMessageBox,
)

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
