# Fontbakery UI

[FontBakery](https://github.com/googlefonts/fontbakery) is a tool for quality assurance of font projects.
But it's not _terribly_ easy to install and use.

The aim of this project is to create an easy-to-install, drag-and-drop interface to testing your fonts with FontBakery.

## Running on macOS

We build a macOS application of FontBakery on each commit, so it's easiest to download the binary from [github.com/googlefonts/fontbakery-ui/releases](https://github.com/googlefonts/fontbakery-ui/releases)

If you do want to build and run it yourself, though, you should run:

```
git clone https://github.com/googlefonts/fontbakery-ui.git
cd fontbakery-ui
pip3 install -r requirements.txt
python3 setup.py py2app
open dist/FontBakery.app
```

## Running on Windows

We'll get continuous deployment working here too, somehow, sometime...

## Running on Linux

```
apt-get install python3-pyqt5
git clone https://github.com/googlefonts/fontbakery-ui.git
cd fontbakery-ui
pip3 install -r requirements.txt
python3 qfontbakery.py
```

The first line above installs PyQt5 from the Debian package manager, in order to get the correct windowing system abstraction plugin thingy to run Qt on your window system.
On non-Debian derived GNU+Linux distributions, you will need to install the equivalent package using that system's package manager.
