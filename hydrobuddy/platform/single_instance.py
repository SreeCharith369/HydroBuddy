"""Only one HydroBuddy runs at a time. Launching it again opens the running one.

A lock file decides who is first. The first instance also listens on two local
sockets, one per command ("show" and "quit"). Connecting to a socket *is* the
message, so nothing has to be read from a pipe the sender may already have closed.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)

COMMANDS = ("show", "quit")


class SingleInstance(QObject):
    activated = Signal()  # another launch asked us to show ourselves
    quit_requested = Signal()  # another launch asked us to close

    def __init__(self, data_folder: Path) -> None:
        super().__init__()
        # One name per data folder, so a test copy never talks to the real app.
        digest = hashlib.sha1(str(data_folder.resolve()).lower().encode()).hexdigest()[:12]
        self.name = f"HydroBuddy-{digest}"
        self._lock = QLockFile(str(data_folder / "hydrobuddy.lock"))
        self._lock.setStaleLockTime(0)  # a crashed instance's lock is detected by its PID
        self._servers: list[QLocalServer] = []

    def acquire(self) -> bool:
        """Become the running instance. Returns False if another one already is."""

        if not self._lock.tryLock(200):
            self.send("show")
            return False
        for command in COMMANDS:
            name = f"{self.name}-{command}"
            QLocalServer.removeServer(name)  # clean up after a crash
            server = QLocalServer(self)
            server.newConnection.connect(lambda s=server, c=command: self._on_connection(s, c))
            if not server.listen(name):
                log.warning("Could not listen for other launches: %s", server.errorString())
            self._servers.append(server)
        return True

    def send(self, command: str) -> bool:
        """Send "show" or "quit" to the running instance. Returns False if none answered."""

        socket = QLocalSocket()
        socket.connectToServer(f"{self.name}-{command}")
        if not socket.waitForConnected(500):
            return False
        socket.disconnectFromServer()
        return True

    def _on_connection(self, server: QLocalServer, command: str) -> None:
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            log.info("Another launch asked HydroBuddy to %s", command)
            if command == "quit":
                self.quit_requested.emit()
            else:
                self.activated.emit()
