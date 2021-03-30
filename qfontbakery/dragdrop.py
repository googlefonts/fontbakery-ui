from PyQt5.QtWidgets import QLabel, QFileDialog


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

