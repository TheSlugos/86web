import io
import json
import os
import subprocess
import zipfile
from unittest.mock import MagicMock, patch
import pytest

from app.services.mtools import (
    MToolsError,
    get_fat_offset,
    ensure_fat_dir,
    inject_file_or_zip,
)


class DummyUploadFile:
    """Mock FastAPI UploadFile for testing without full HTTP request lifecycle."""
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = io.BytesIO(content)


# ─── 1. Partition Offset Detection ───────────────────────────────────────────

def test_get_fat_offset_valid_partition():
    sfdisk_json = json.dumps({
        "partitiontable": {
            "sectorsize": 512,
            "partitions": [
                {"node": "/dev/loop0p1", "start": 2048, "size": 102400}
            ]
        }
    })
    mock_res = subprocess.CompletedProcess(args=["sfdisk"], returncode=0, stdout=sfdisk_json, stderr="")
    with patch("subprocess.run", return_value=mock_res):
        offset = get_fat_offset("/path/to/disk.img")
        assert offset == 2048 * 512  # 1,048,576 bytes


def test_get_fat_offset_unpartitioned_raw():
    sfdisk_json = json.dumps({
        "partitiontable": {
            "sectorsize": 512,
            "partitions": []
        }
    })
    mock_res = subprocess.CompletedProcess(args=["sfdisk"], returncode=0, stdout=sfdisk_json, stderr="")
    with patch("subprocess.run", return_value=mock_res):
        offset = get_fat_offset("/path/to/floppy.img")
        assert offset == 0


def test_get_fat_offset_sfdisk_error():
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["sfdisk"])):
        offset = get_fat_offset("/path/to/corrupt.img")
        assert offset == 0


def test_get_fat_offset_invalid_json():
    mock_res = subprocess.CompletedProcess(args=["sfdisk"], returncode=0, stdout="not valid json", stderr="")
    with patch("subprocess.run", return_value=mock_res):
        offset = get_fat_offset("/path/to/bad.img")
        assert offset == 0


# ─── 2. Directory Creation (ensure_fat_dir) ───────────────────────────────────

def test_ensure_fat_dir_empty_or_root():
    with patch("subprocess.run") as mock_run:
        ensure_fat_dir("/path/to/disk.img", 0, "")
        ensure_fat_dir("/path/to/disk.img", 0, "/")
        ensure_fat_dir("/path/to/disk.img", 0, "   ")
        assert mock_run.call_count == 0


def test_ensure_fat_dir_creates_nested_directories():
    calls = []

    def mock_run(cmd, *args, **kwargs):
        calls.append(cmd)
        # mdir fails (directory does not exist), mmd succeeds
        if cmd[0] == "mdir":
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="File not found")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=mock_run):
        ensure_fat_dir("/path/to/disk.img", 1024, r"GAMES\DOOM")

        assert len(calls) == 4
        # 1. Check GAMES
        assert calls[0][0] == "mdir"
        assert calls[0][3] == "::/GAMES"
        # 2. Create GAMES
        assert calls[1][0] == "mmd"
        assert calls[1][3] == "::/GAMES"
        # 3. Check GAMES/DOOM
        assert calls[2][0] == "mdir"
        assert calls[2][3] == "::/GAMES/DOOM"
        # 4. Create GAMES/DOOM
        assert calls[3][0] == "mmd"
        assert calls[3][3] == "::/GAMES/DOOM"


def test_ensure_fat_dir_mmd_failure_raises_mtools_error():
    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "mdir":
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="Disk full")

    with patch("subprocess.run", side_effect=mock_run):
        with pytest.raises(MToolsError, match="Failed to create directory.*Disk full"):
            ensure_fat_dir("/path/to/disk.img", 0, "TESTDIR")


def test_ensure_fat_dir_already_exists_ignored():
    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "mdir":
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
        # mmd reports directory already exists
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="Directory already exists")

    with patch("subprocess.run", side_effect=mock_run):
        # Should not raise exception
        ensure_fat_dir("/path/to/disk.img", 0, "EXISTING")


# ─── 3. File & ZIP Injection ──────────────────────────────────────────────────

def test_inject_unformatted_disk_raises_helpful_error():
    mock_mdir = subprocess.CompletedProcess(
        args=["mdir"], returncode=1, stdout="", stderr="init :: Non DOS media or cannot read boot sector"
    )
    with patch("app.services.mtools.get_fat_offset", return_value=0), \
         patch("subprocess.run", return_value=mock_mdir):
        upload = DummyUploadFile("file.txt", b"hello world")
        with pytest.raises(MToolsError, match="not formatted with a DOS/FAT filesystem"):
            inject_file_or_zip("/path/to/disk.img", upload)


def test_inject_single_file_success():
    def mock_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("app.services.mtools.get_fat_offset", return_value=512), \
         patch("app.services.mtools.ensure_fat_dir") as mock_ensure, \
         patch("subprocess.run", side_effect=mock_run) as mock_cmd:
        upload = DummyUploadFile("readme.txt", b"Test documentation")
        res = inject_file_or_zip("/path/to/disk.img", upload, target_folder="DOCS", extract_zip=False)

        assert res["status"] == "success"
        assert res["extracted"] is False
        assert res["target_folder"] == "DOCS"
        mock_ensure.assert_called_once_with("/path/to/disk.img", 512, "DOCS")

        # Verify mcopy was invoked
        mcopy_calls = [c for c in mock_cmd.call_args_list if c[0][0][0] == "mcopy"]
        assert len(mcopy_calls) == 1
        assert mcopy_calls[0][0][0][-1] == "::/DOCS/readme.txt"


def test_inject_single_file_disk_full():
    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "mcopy":
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="Disk full")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("app.services.mtools.get_fat_offset", return_value=0), \
         patch("subprocess.run", side_effect=mock_run):
        upload = DummyUploadFile("huge.bin", b"x" * 100)
        with pytest.raises(MToolsError, match="Hard disk or directory is full"):
            inject_file_or_zip("/path/to/disk.img", upload)


def test_inject_zip_archive_success():
    # Build in-memory zip
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr("doom.exe", b"fake doom executable")
        z.writestr("doom1.wad", b"fake wad data")
    zip_bytes = zip_buf.getvalue()

    def mock_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("app.services.mtools.get_fat_offset", return_value=0), \
         patch("app.services.mtools.ensure_fat_dir"), \
         patch("subprocess.run", side_effect=mock_run) as mock_cmd:
        upload = DummyUploadFile("doom.zip", zip_bytes)
        res = inject_file_or_zip("/path/to/disk.img", upload, target_folder="GAMES/DOOM", extract_zip=True)

        assert res["status"] == "success"
        assert res["extracted"] is True
        assert res["target_folder"] == "GAMES/DOOM"

        # Verify mcopy batch recursive copy was executed
        mcopy_calls = [c for c in mock_cmd.call_args_list if c[0][0][0] == "mcopy"]
        assert len(mcopy_calls) >= 1
        assert "-s" in mcopy_calls[0][0][0]  # recursive
        assert mcopy_calls[0][0][0][-1] == "::/GAMES/DOOM/"


def test_inject_zip_archive_empty():
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as _:
        pass  # empty zip

    with patch("app.services.mtools.get_fat_offset", return_value=0), \
         patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")):
        upload = DummyUploadFile("empty.zip", zip_buf.getvalue())
        res = inject_file_or_zip("/path/to/disk.img", upload, extract_zip=True)
        assert res["status"] == "success"
        assert "empty" in res["message"].lower()


def test_inject_zip_slip_path_traversal_prevention():
    # Attempt Zip Slip attack with relative parent directory
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr("../../etc/passwd", b"root::0:0:root:/root:/bin/bash")
    
    with patch("app.services.mtools.get_fat_offset", return_value=0), \
         patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")):
        upload = DummyUploadFile("malicious.zip", zip_buf.getvalue())
        with pytest.raises(MToolsError, match="Security error: ZIP archive contains illegal path"):
            inject_file_or_zip("/path/to/disk.img", upload, extract_zip=True)


def test_inject_zip_corrupt_archive():
    with patch("app.services.mtools.get_fat_offset", return_value=0), \
         patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")):
        upload = DummyUploadFile("corrupt.zip", b"not a zip file content")
        with pytest.raises(MToolsError, match="Invalid or corrupted ZIP archive"):
            inject_file_or_zip("/path/to/disk.img", upload, extract_zip=True)
