import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from app.routers.vms import _VALID_DRIVE_KEYS, mount_drive, eject_drive
from app.schemas import DriveMount


# ─── Drive Key Validation ─────────────────────────────────────────────────────

def test_valid_drive_keys():
    expected = {
        "fdd_01", "fdd_02", "fdd_03", "fdd_04",
        "cdrom_01", "cdrom_02", "cdrom_03", "cdrom_04",
    }
    assert _VALID_DRIVE_KEYS == expected


@pytest.mark.anyio
async def test_mount_invalid_drive_key_raises_400():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    body = DriveMount(path="/data/disk.img", write_protected=False)

    for invalid_key in ["fdd_00", "fdd_05", "hdd_01", "cdrom_00", "floppy_a"]:
        with pytest.raises(HTTPException) as exc_info:
            await mount_drive(
                vm_id=1,
                drive_key=invalid_key,
                body=body,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 400
        assert "Invalid drive key" in exc_info.value.detail


@pytest.mark.anyio
async def test_eject_invalid_drive_key_raises_400():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)

    with pytest.raises(HTTPException) as exc_info:
        await eject_drive(
            vm_id=1,
            drive_key="invalid_drive",
            db=mock_db,
            current_user=mock_user,
        )
    assert exc_info.value.status_code == 400
    assert "Invalid drive key" in exc_info.value.detail


# ─── Path Containment & Security Tests ────────────────────────────────────────

@pytest.mark.anyio
async def test_mount_path_traversal_rejected():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    mock_vm = MagicMock(id=1, user_id=1, uuid="test-uuid", config={}, status="stopped")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_vm

    body = DriveMount(path="/etc/passwd", write_protected=False)

    with patch("app.routers.vms.settings") as mock_settings:
        mock_settings.vms_path = "/data/vms"
        mock_settings.library_path = "/data/library"
        mock_settings.user_images_path.return_value = "/data/user_images/1"
        mock_settings.shared_media_path.return_value = "/data/shared/1"

        with pytest.raises(HTTPException) as exc_info:
            await mount_drive(
                vm_id=1,
                drive_key="fdd_01",
                body=body,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 400
        assert "Image path must be within" in exc_info.value.detail


@pytest.mark.anyio
async def test_mount_nonexistent_file_rejected():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    mock_vm = MagicMock(id=1, user_id=1, uuid="test-uuid", config={}, status="stopped")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_vm

    body = DriveMount(path="/data/library/nonexistent.img", write_protected=False)

    with patch("app.routers.vms.settings") as mock_settings, \
         patch("os.path.exists", return_value=False):
        mock_settings.vms_path = "/data/vms"
        mock_settings.library_path = "/data/library"
        mock_settings.user_images_path.return_value = "/data/user_images/1"
        mock_settings.shared_media_path.return_value = "/data/shared/1"

        with pytest.raises(HTTPException) as exc_info:
            await mount_drive(
                vm_id=1,
                drive_key="fdd_01",
                body=body,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 404
        assert "Image file not found" in exc_info.value.detail


# ─── Live IPC Mount & Eject Command Dispatch Tests ────────────────────────────

@pytest.mark.anyio
async def test_mount_running_floppy_ro_dispatches_ipc():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    mock_vm = MagicMock(id=1, user_id=1, uuid="test-uuid", config={}, status="running")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_vm

    body = DriveMount(path="/data/library/boot.img", write_protected=True)

    with patch("app.routers.vms.settings") as mock_settings, \
         patch("app.routers.vms._write_86box_config"), \
         patch("os.path.exists", return_value=True), \
         patch("app.routers.vms.VMService.run_ipc_command", new_callable=AsyncMock) as mock_ipc:
        mock_settings.vms_path = "/data/vms"
        mock_settings.library_path = "/data/library"
        mock_settings.user_images_path.return_value = "/data/user_images/1"
        mock_settings.shared_media_path.return_value = "/data/shared/1"

        res = await mount_drive(
            vm_id=1,
            drive_key="fdd_01",
            body=body,
            db=mock_db,
            current_user=mock_user,
        )

        assert res["status"] == "mounted"
        assert res["write_protected"] is True
        # Verify IPC command formatted with fdd 0 and ro flag
        mock_ipc.assert_called_once()
        cmd = mock_ipc.call_args[0][1]
        assert cmd.startswith("fdd_mount 0 ro ")


@pytest.mark.anyio
async def test_mount_running_cdrom_dispatches_ipc():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    mock_vm = MagicMock(id=1, user_id=1, uuid="test-uuid", config={}, status="running")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_vm

    body = DriveMount(path="/data/library/win95.iso", write_protected=False)

    with patch("app.routers.vms.settings") as mock_settings, \
         patch("app.routers.vms._write_86box_config"), \
         patch("os.path.exists", return_value=True), \
         patch("app.routers.vms.VMService.run_ipc_command", new_callable=AsyncMock) as mock_ipc:
        mock_settings.vms_path = "/data/vms"
        mock_settings.library_path = "/data/library"
        mock_settings.user_images_path.return_value = "/data/user_images/1"
        mock_settings.shared_media_path.return_value = "/data/shared/1"

        res = await mount_drive(
            vm_id=1,
            drive_key="cdrom_02",
            body=body,
            db=mock_db,
            current_user=mock_user,
        )

        assert res["status"] == "mounted"
        # Verify CD-ROM 2 maps to index 1
        mock_ipc.assert_called_once()
        cmd = mock_ipc.call_args[0][1]
        assert cmd.startswith("cdrom_mount 1 ")


@pytest.mark.anyio
async def test_eject_running_drive_dispatches_ipc():
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    mock_vm = MagicMock(id=1, user_id=1, uuid="test-uuid", config={"fdd_02_fn": "/data/disk.img"}, status="running")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_vm

    with patch("app.routers.vms.settings") as mock_settings, \
         patch("app.routers.vms._write_86box_config"), \
         patch("app.routers.vms.VMService.run_ipc_command", new_callable=AsyncMock) as mock_ipc:
        mock_settings.vms_path = "/data/vms"

        res = await eject_drive(
            vm_id=1,
            drive_key="fdd_02",
            db=mock_db,
            current_user=mock_user,
        )

        assert res == {"status": "ejected", "drive_key": "fdd_02"}
        assert mock_vm.config["fdd_02_fn"] == ""
        mock_ipc.assert_called_once_with(1, "fdd_eject 1")


def test_write_86box_config_resolves_bare_floppy_to_media(tmp_path):
    from app.routers.vms import _write_86box_config
    vm_dir = tmp_path / "test-vm"
    media_dir = vm_dir / "media"
    media_dir.mkdir(parents=True)
    floppy_file = media_dir / "msdos6_22disk1.img"
    floppy_file.write_bytes(b"dummy floppy")

    mock_vm = MagicMock(
        id=1,
        user_id=1,
        uuid="test-uuid",
        config={
            "machine": "ibmxt",
            "cpu_family": "8088",
            "fdd_01_type": "35_2hd",
            "fdd_01_fn": "msdos6_22disk1.img",
        },
    )

    with patch("app.hardware_lists.get_cpu_by_index", return_value=(4772727, 1)), \
         patch("app.hardware_lists.machine_has_builtin_video", return_value=False):
        _write_86box_config(mock_vm, str(vm_dir))

    cfg_path = vm_dir / "86box.cfg"
    assert cfg_path.exists()
    content = cfg_path.read_text(encoding="utf-8")
    assert "fdd_01_fn = media/msdos6_22disk1.img" in content


def test_write_86box_config_resolves_bare_cdrom_to_media(tmp_path):
    from app.routers.vms import _write_86box_config
    vm_dir = tmp_path / "test-vm-cd"
    media_dir = vm_dir / "media"
    media_dir.mkdir(parents=True)
    iso_file = media_dir / "setup.iso"
    iso_file.write_bytes(b"dummy iso")

    mock_vm = MagicMock(
        id=2,
        user_id=1,
        uuid="test-uuid-cd",
        config={
            "machine": "ibmxt",
            "cpu_family": "8088",
            "cdrom_01_enabled": True,
            "cdrom_01_bus": "ide",
            "cdrom_01_fn": "setup.iso",
        },
    )

    with patch("app.hardware_lists.get_cpu_by_index", return_value=(4772727, 1)), \
         patch("app.hardware_lists.machine_has_builtin_video", return_value=False):
        _write_86box_config(mock_vm, str(vm_dir))

    cfg_path = vm_dir / "86box.cfg"
    assert cfg_path.exists()
    content = cfg_path.read_text(encoding="utf-8")
    assert "cdrom_01_fn = media/setup.iso" in content

