# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Utilities for IPC with existing instances."""

import json
import getpass

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from qutebrowser.utils import log, objreg


SOCKETNAME = 'qutebrowser-{}'.format(getpass.getuser())
CONNECT_TIMEOUT = 100
WRITE_TIMEOUT = 1000


class IPCError(Exception):

    """Exception raised when there was a problem with IPC."""


class IPCServer(QObject):

    """IPC server to which clients connect to."""

    def __init__(self, parent=None):
        """Start the IPC server and listen to commands."""
        super().__init__(parent)
        self._remove_server()
        self._server = QLocalServer(self)
        ok = self._server.listen(SOCKETNAME)
        if not ok:
            raise IPCError("Error while listening to IPC server: {} "
                           "(error {})".format(self._server.errorString(),
                                               self._server.serverError()))
        self._server.newConnection.connect(self.on_connection)
        self._socket = None

    def _remove_server(self):
        """Remove an existing server."""
        ok = QLocalServer.removeServer(SOCKETNAME)
        if not ok:
            raise IPCError("Error while removing server {}!".format(
                SOCKETNAME))

    @pyqtSlot(int)
    def on_error(self, error):
        """Convenience method which calls _socket_error on an error."""
        if error != QLocalSocket.PeerClosedError:
            _socket_error("handling IPC connection", self._socket)

    @pyqtSlot()
    def on_connection(self):
        """Slot for a new connection for the local socket."""
        socket = self._server.nextPendingConnection()
        if self._socket is not None:
            # We already have a connection running, so we refuse this one.
            socket.close()
            socket.deleteLater()
        else:
            socket.readyRead.connect(self.on_ready_read)
            socket.disconnected.connect(self.on_disconnected)
            socket.error.connect(self.on_error)
            self._socket = socket

    def on_disconnected(self):
        """Clean up socket when the client disconnected."""
        self._socket.deleteLater()
        self._socket = None

    def on_ready_read(self):
        """Read json data from the client."""
        while self._socket.canReadLine():
            data = bytes(self._socket.readLine())
            args = json.loads(data.decode('utf-8'))
            app = objreg.get('app')
            app.process_args(args)

    def shutdown(self):
        """Shut down the IPC server cleanly."""
        if self._socket is not None:
            self._socket.deleteLater()
            self._socket = None
        self._server.close()
        self._server.deleteLater()
        self._remove_server()

def init():
    """Initialize the global IPC server."""
    app = objreg.get('app')
    server = IPCServer(app)
    objreg.register('ipc-server', server)


def _socket_error(action, socket):
    """Raise an IPCError based on an action and a QLocalSocket.

    Args:
        action: A string like "writing to running instance".
        socket: A QLocalSocket.
    """
    raise IPCError("Error while {}: {} (error {})".format(
        action, socket.errorString(), socket.error()))


def send_to_running_instance(cmdlist):
    """Try to send a commandline to a running instance.

    Blocks for CONNECT_TIMEOUT ms.

    Args:
        cmdlist: A list to send (URLs/commands)

    Return:
        True if connecting was successful, False if no connection was made.
    """
    socket = QLocalSocket()
    socket.connectToServer(SOCKETNAME)
    connected = socket.waitForConnected(100)
    if connected:
        log.init.info("Opening in existing instance")
        line = json.dumps(cmdlist) + '\n'
        socket.writeData(line.encode('utf-8'))
        socket.waitForBytesWritten(WRITE_TIMEOUT)
        if socket.error() != QLocalSocket.UnknownSocketError:
            _socket_error("writing to running instance", socket)
        else:
            return True
    else:
        if socket.error() not in (QLocalSocket.ConnectionRefusedError,
                                  QLocalSocket.ServerNotFoundError):
            _socket_error("connecting to running instance", socket)
        else:
            return False
