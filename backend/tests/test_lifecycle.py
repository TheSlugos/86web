import asyncio
import os
import signal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from runner.app.vm_process import VMProcessManager, VMProcesses


@pytest.fixture
def manager():
    mgr = VMProcessManager()
    mgr._vms.clear()
    mgr._slots.clear()
    return mgr


@pytest.fixture
def running_vm(manager):
    procs = VMProcesses(
        vm_id=1,
        slot=0,
        display=":100",
        vnc_tcp_port=5900,
        vm_dir="/test/vm1",
        box86_cmd=["/86box", "--config", "/test/vm1/86box.cfg"]
    )
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # Process is alive
    mock_proc.pid = 12345
    procs.box86_proc = mock_proc
    manager._vms[1] = procs
    manager._slots.add(0)
    return procs


# ─── Hard Reset Tests ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_reset_vm_not_running(manager):
    res = await manager.reset_vm(99)
    assert res == {"error": "VM not running"}


@pytest.mark.anyio
async def test_reset_vm_native_ipc_success(manager, running_vm):
    with patch.object(manager, "run_ipc_command", return_value={"status": "ok", "response": "OK hard_reset"}) as mock_ipc:
        running_vm.paused = True
        res = await manager.reset_vm(1)

        assert res == {"status": "reset"}
        assert running_vm.paused is False
        mock_ipc.assert_called_once_with(1, "hard_reset")
        # Ensure process was NOT restarted because IPC succeeded
        running_vm.box86_proc.terminate.assert_not_called()


@pytest.mark.anyio
async def test_reset_vm_ipc_fallback_to_restart(manager, running_vm):
    old_proc = running_vm.box86_proc
    with patch.object(manager, "run_ipc_command", return_value={"error": "socket missing"}), \
         patch("subprocess.Popen") as mock_popen, \
         patch("asyncio.sleep", return_value=None):
        new_proc = MagicMock()
        new_proc.poll.return_value = None
        mock_popen.return_value = new_proc

        res = await manager.reset_vm(1)
        assert res == {"status": "reset"}
        old_proc.terminate.assert_called_once()
        mock_popen.assert_called_once()


# ─── Pause & Resume Tests ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_pause_vm_not_running(manager):
    res = await manager.pause_vm(99)
    assert res == {"error": "VM not running"}


@pytest.mark.anyio
async def test_pause_vm_native_ipc(manager, running_vm):
    running_vm.paused = False
    with patch.object(manager, "run_ipc_command", return_value={"status": "ok", "response": "OK pause"}) as mock_ipc:
        res = await manager.pause_vm(1)
        assert res == {"status": "paused"}
        assert running_vm.paused is True
        mock_ipc.assert_called_once_with(1, "pause")


@pytest.mark.anyio
async def test_resume_vm_native_ipc(manager, running_vm):
    running_vm.paused = True
    with patch.object(manager, "run_ipc_command", return_value={"status": "ok", "response": "OK resume"}) as mock_ipc:
        res = await manager.pause_vm(1)
        assert res == {"status": "resumed"}
        assert running_vm.paused is False
        mock_ipc.assert_called_once_with(1, "resume")


@pytest.mark.anyio
async def test_pause_vm_fallback_to_signals(manager, running_vm):
    from runner.app.vm_process import SIGSTOP
    running_vm.paused = False
    with patch.object(manager, "run_ipc_command", return_value={"error": "socket missing"}), \
         patch("runner.app.vm_process._killpg") as mock_killpg:
        res = await manager.pause_vm(1)
        assert res == {"status": "paused"}
        assert running_vm.paused is True
        mock_killpg.assert_called_once_with(12345, SIGSTOP)


# ─── Ctrl+Alt+Del (CAD) Fast-Path Tests ──────────────────────────────────────

def test_send_key_cad_fast_path(manager, running_vm):
    with patch.object(manager, "run_ipc_command", return_value={"status": "ok"}) as mock_ipc, \
         patch("subprocess.run") as mock_xdotool:
        res = manager.send_key(1, "ctrl+F12")
        assert res == {"status": "ok"}
        mock_ipc.assert_called_once_with(1, "cad")
        mock_xdotool.assert_not_called()


def test_send_key_cad_alias(manager, running_vm):
    with patch.object(manager, "run_ipc_command", return_value={"status": "ok"}) as mock_ipc:
        res = manager.send_key(1, "cad")
        assert res == {"status": "ok"}
        mock_ipc.assert_called_once_with(1, "cad")


def test_send_key_non_cad_uses_xdotool(manager, running_vm):
    mock_res = MagicMock(returncode=0)
    with patch.object(manager, "run_ipc_command") as mock_ipc, \
         patch("subprocess.run", return_value=mock_res) as mock_xdotool:
        res = manager.send_key(1, "Return")
        assert res == {"status": "ok"}
        mock_ipc.assert_not_called()
        mock_xdotool.assert_called_once()
        assert "Return" in mock_xdotool.call_args[0][0]


# ─── Clean Power Off on Stop Tests ───────────────────────────────────────────

@pytest.mark.anyio
async def test_stop_vm_sends_ipc_power_off_for_clean_flush(manager, running_vm):
    with patch.object(manager, "run_ipc_command", return_value={"status": "ok"}) as mock_ipc, \
         patch.object(manager, "_kill_procs", new_callable=AsyncMock) as mock_kill, \
         patch("asyncio.sleep", return_value=None), \
         patch("os.path.exists", return_value=False):
        res = await manager.stop_vm(1)
        assert res == {"status": "stopped"}
        # Verify clean power_off was dispatched first
        mock_ipc.assert_called_once_with(1, "power_off", procs=running_vm)
        mock_kill.assert_called_once_with(running_vm)
        assert 1 not in manager._vms
        assert 0 not in manager._slots
