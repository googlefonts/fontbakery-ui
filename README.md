# Fontbakery UI

[FontBakery](https://github.com/googlefonts/fontbakery) is a tool for quality assurance of font projects. But it's not _terribly_ easy to use. The aim of this project is to create an easy-to-install, drag-and-drop interface to testing your fonts.

## Running on Mac OS X

We build a Mac OS X application of FontBakery on each commit, so it's
easiest to download the binary from [here](https://github.com/simoncozens/fontbakery-ui/releases).

If you do want to build and run it yourself, though, you should run:

```
pip3 install -r requirements.txt
python3 setup.py py2app
open dist/FontBakery.app
```

## Running on Windows

We'll get continuous deployment working here too, somehow, sometime...

## Running on Linux

```
pip3 install -r requirements.txt
python3 qfontbakery.py
```

You may find that you need to install PyQt5 from your package manager (e.g.
`apt-get install python3-pyqt5`) in order to get the correct windowing system abstraction plugin thingy to run Qt on your window system.
