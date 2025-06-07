from krita import *
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QDockWidget
from PyQt5.QtCore import QTimer
from .pypresence import Presence
from os.path import basename
from io import BytesIO
from time import time
import requests

RPC = Presence(client_id=1380857819254755328)

class BasedKrita(Extension):
    def __init__(self, parent):
        super().__init__(parent)

        # undo and redo stats
        self.label = None
        self.windows = []
        self.undo = 0
        self.redo = 0

        # discord rich presence
        self.time = time()
        self.connected = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_rpc_safe)

    def setup(self):
        notifier = Krita.instance().notifier()
        notifier.setActive(True)
        notifier.windowCreated.connect(self.window_created)
        self.timer.start(1000)

    def update_rpc_safe(self):
        try:
            self.update_rpc()
            self.timer.setInterval(15000)
        except:
            self.connected = False
            self.timer.stop()
            self.timer.start(1000)

    def update_rpc(self):
        if not self.connected:
            RPC.connect()
            self.connected = True

        doc = Krita.instance().activeDocument()
        if not doc:
            RPC.update(
                details="No active document",
                state="¯\\_(ツ)_/¯",
                large_text=f"Krita v{Krita.instance().version()}",
                large_image="krita",
                start=int(self.time))
            return

        image = doc.thumbnail(256, 256)
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()

        try:
            response = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                files={
                    'fileToUpload': ('thumbnail.png', BytesIO(byte_array.data()))
                },
                data={
                    'reqtype': 'fileupload',
                    'time': '1h'
                })
            response.raise_for_status()
            url = response.text.strip()
        except:
            url = 'https://files.catbox.moe/4e94ax.png'

        RPC.update(
            details=str(doc.name()) or str(basename(doc.fileName())) or "Unnamed",
            state=f"{self.undo} undo, {self.redo} redo",
            small_text=f"Krita v{Krita.instance().version()}",
            small_image="krita",
            large_text="Image preview",
            large_image=url,
            start=int(self.time))

    def increment_undo(self):
        self.undo += 1
        self.save_counts()
        self.update_label()

    def increment_redo(self):
        self.redo += 1
        self.save_counts()
        self.update_label()

    def save_counts(self):
        doc = Krita.instance().activeDocument()
        if doc:
            doc.setAnnotation("undo_count", "How many times you used undo", str(self.undo).encode())
            doc.setAnnotation("redo_count", "How many times you used redo", str(self.redo).encode())

    def load_counts(self):
        doc = Krita.instance().activeDocument()
        if doc:
            self.undo = int(bytes(doc.annotation("undo_count")).decode() or 0)
            self.redo = int(bytes(doc.annotation("redo_count")).decode() or 0)

    def update_label(self):
        self.label.setText(f"You used undo {self.undo} times and used redo {self.redo} times")

    def modify_history(self):
        self.label = QLabel("")
        history = Krita.instance().activeWindow().qwindow().findChild(QDockWidget, "History")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(history.widget())
        container = QWidget()
        container.setLayout(layout)
        history.setWidget(container)

    def on_view_changed(self):
        self.load_counts()
        self.update_label()

    def window_created(self):
        Krita.instance().action("edit_undo").triggered.connect(self.increment_undo)
        Krita.instance().action("edit_redo").triggered.connect(self.increment_redo)
        self.modify_history()
        for win in Application.windows():
            if win not in self.windows:
                win.activeViewChanged.connect(self.on_view_changed)

    def createActions(self, window):
        window.activeViewChanged.connect(self.on_view_changed)

Krita.instance().addExtension(BasedKrita(Krita.instance()))
