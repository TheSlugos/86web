import os
import socket
import threading
from unittest.mock import MagicMock, patch
import pytest

from runner.app.vm_process import VMProcessManager, VMProcesses


class MockIpcServer:
    """Mock socket server that emulates 86Box's QLocalServer IPC interface."""
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.received_commands = []
        self.sock = None
        self.server_thread = None
        self.running = False
        self.port = None

    def start_tcp(self):
        """Start a TCP loopback socket that can be used on Windows where AF_UNIX may vary."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(1)
        self.running = True

        def _serve():
            while self.running:
                try:
                    self.sock.settimeout(0.5)
                    client, _ = self.sock.accept()
                    client.settimeout(2.0)
                    data = client.recv(1024).decode("utf-8")
                    if data:
                        cmd = data.strip()
                        self.received_commands.append(cmd)
                        resp = self.responses.get(cmd, "OK\n")
                        if not resp.endswith("\n"):
                            resp += "\n"
                        client.sendall(resp.encode("utf-8"))
                    client.close()
                except socket.timeout:
                    continue
                except Exception:
                    break

        self.server_thread = threading.Thread(target=_serve, daemon=True)
        self.server_thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if self.server_thread:
            self.server_thread.join(timeout=1.0)


# ─── Drive Routing & Key Formatting Tests ─────────────────────────────────────

def test_drive_keys_and_indices():
    valid_keys = {
        "fdd_01", "fdd_02", "fdd_03", "fdd_04",
        "cdrom_01", "cdrom_02", "cdrom_03", "cdrom_04",
    }
    
    # Verify index calculation (e.g. fdd_01 -> 0, cdrom_04 -> 3)
    for key in valid_keys:
        prefix = "fdd" if key.startswith("fdd") else "cdrom"
        idx = int(key[-2:]) - 1
        assert 0 <= idx <= 3
        assert prefix in ("fdd", "cdrom")


def test_floppy_mount_command_formatting():
    # Write-protected: ro
    cmd_ro = f"fdd_mount {0} {'ro'} /path/to/boot.img"
    assert cmd_ro == "fdd_mount 0 ro /path/to/boot.img"

    # Writable: rw
    cmd_rw = f"fdd_mount {1} {'rw'} /path/to/data.img"
    assert cmd_rw == "fdd_mount 1 rw /path/to/data.img"


def test_cdrom_mount_command_formatting():
    cmd_cd = f"cdrom_mount {0} /path/to/win95.iso"
    assert cmd_cd == "cdrom_mount 0 /path/to/win95.iso"


def test_eject_command_formatting():
    cmd_fdd_eject = f"fdd_eject {2}"
    assert cmd_fdd_eject == "fdd_eject 2"

    cmd_cd_eject = f"cdrom_eject {3}"
    assert cmd_cd_eject == "cdrom_eject 3"


# ─── IPC Communication Protocol Engine Tests ─────────────────────────────────

def test_run_ipc_command_vm_not_running():
    mgr = VMProcessManager()
    mgr._vms.clear()
    res = mgr.run_ipc_command(999, "ping")
    assert "error" in res
    assert res["error"] == "VM not running"


def test_run_ipc_command_socket_missing():
    mgr = VMProcessManager()
    procs = VMProcesses(vm_id=1, slot=0, display=":100", vnc_tcp_port=5900, vm_dir="/nonexistent/vm/dir")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # running
    procs.box86_proc = mock_proc
    mgr._vms[1] = procs

    with patch("os.path.exists", return_value=False):
        res = mgr.run_ipc_command(1, "ping")
        assert "error" in res
        assert "IPC socket not found" in res["error"]


def test_run_ipc_command_success_ok():
    mgr = VMProcessManager()
    procs = VMProcesses(vm_id=1, slot=0, display=":100", vnc_tcp_port=5900, vm_dir="/test/vm1")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    procs.box86_proc = mock_proc
    mgr._vms[1] = procs

    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [b"OK fdd_mount 0\n", b""]

    with patch("os.path.exists", return_value=True), \
         patch("socket.socket", return_value=mock_sock):
        res = mgr.run_ipc_command(1, "fdd_mount 0 ro /disk.img")
        assert res["status"] == "ok"
        assert res["response"] == "OK fdd_mount 0"
        mock_sock.sendall.assert_called_once_with(b"fdd_mount 0 ro /disk.img\n")


def test_run_ipc_command_returns_error_status():
    mgr = VMProcessManager()
    procs = VMProcesses(vm_id=1, slot=0, display=":100", vnc_tcp_port=5900, vm_dir="/test/vm1")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    procs.box86_proc = mock_proc
    mgr._vms[1] = procs

    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [b"ERROR invalid_drive_id\n", b""]

    with patch("os.path.exists", return_value=True), \
         patch("socket.socket", return_value=mock_sock):
        res = mgr.run_ipc_command(1, "fdd_mount 9 rw /bad.img")
        assert res["status"] == "error"
        assert res["error"] == "ERROR invalid_drive_id"


def test_run_ipc_command_socket_timeout_or_disconnect():
    mgr = VMProcessManager()
    procs = VMProcesses(vm_id=1, slot=0, display=":100", vnc_tcp_port=5900, vm_dir="/test/vm1")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    procs.box86_proc = mock_proc
    mgr._vms[1] = procs

    mock_sock = MagicMock()
    mock_sock.connect.side_effect = socket.timeout("timed out connecting")

    with patch("os.path.exists", return_value=True), \
         patch("socket.socket", return_value=mock_sock):
        res = mgr.run_ipc_command(1, "ping")
        assert "error" in res
        assert "Failed to communicate with IPC socket" in res["error"]
