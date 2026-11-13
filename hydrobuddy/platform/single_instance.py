"""Only one HydroBuddy runs at a time. Launching it again opens the running one.

A lock file decides who is first. The first instance also listens on a local
socket; a second launch sends it "show" and exits.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)


class SingleInstance(QObject):
    activated = Signal()  # another launch asked us to show ourselves

    def __init__(self, data_folder: Path) -> None:
        super().__init__()
        # One name per data folder, so a test copy never talks to the real app.
        digest = hashlib.sha1(str(data_folder.resolve()).lower().encode()).hexdigest()[:12]
        self.name = f"HydroBuddy-{digest}"
        self._lock = QLockFile(str(data_folder / "hydrobuddy.lock"))
        self._lock.setStaleLockTime(0)  # a crashed instance's lock is detected by its PID
        self._server: QLocalServer | None = None

    def acquire(self) -> bool:
        """Become the running instance. Returns False if another one already is."""

        if not self._lock.tryLock(200):
            self._notify_running_instance()
            return False
        QLocalServer.removeServer(self.name)  # clean up after a crash
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(self.name):
            log.warning("Could not listen for other launches: %s", self._server.errorString())
        return True

    def _notify_running_instance(self) -> None:
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if socket.waitForConnected(500):
            socket.write(b"show")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()

    def _on_connection(self) -> None:
        while self._server and self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            log.info("Another launch asked to show HydroBuddy")
            self.activated.emit()
