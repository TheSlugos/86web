import os
import subprocess
import json
import tempfile
import zipfile
from typing import Optional
from fastapi import UploadFile

class MToolsError(Exception):
    pass

def get_fat_offset(img_path: str) -> int:
    """Uses sfdisk to find the start sector of the first partition and returns the byte offset."""
    try:
        result = subprocess.run(["sfdisk", "-J", img_path], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        ptable = data.get("partitiontable", {})
        sectorsize = ptable.get("sectorsize", 512)
        partitions = ptable.get("partitions", [])
        
        if not partitions:
            return 0  # Raw image (unpartitioned, like a floppy)
            
        start_sector = partitions[0].get("start", 0)
        return start_sector * sectorsize
        
    except subprocess.CalledProcessError:
        return 0
    except (json.JSONDecodeError, KeyError, IndexError):
        return 0

def ensure_fat_dir(img_path: str, offset: int, target_dir: str) -> None:
    """
    Recursively ensures that target_dir exists on the FAT filesystem.
    target_dir: e.g. "GAMES/DOOM" or "/GAMES/DOOM"
    """
    clean = target_dir.strip().replace("\\", "/").strip("/")
    if not clean:
        return
        
    parts = clean.split("/")
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        current = f"{current}/{part}" if current else part
        dos_path = f"::/{current}"
        
        chk = subprocess.run(
            ["mdir", "-i", f"{img_path}@@{offset}", dos_path],
            capture_output=True,
            text=True
        )
        if chk.returncode != 0:
            res = subprocess.run(
                ["mmd", "-i", f"{img_path}@@{offset}", dos_path],
                capture_output=True,
                text=True
            )
            if res.returncode != 0:
                err_msg = (res.stderr or res.stdout or "").strip()
                if "already exists" not in err_msg.lower() and "file exists" not in err_msg.lower():
                    raise MToolsError(f"Failed to create directory {dos_path}: {err_msg}")

def inject_file_or_zip(
    img_path: str,
    upload_file: UploadFile,
    target_folder: str = "",
    extract_zip: bool = True
) -> dict:
    """
    Injects a single file or extracts a ZIP archive into target_folder on the FAT filesystem.
    """
    offset = get_fat_offset(img_path)
    
    # Verify disk is formatted / accessible with mdir ::/
    chk = subprocess.run(
        ["mdir", "-i", f"{img_path}@@{offset}", "::/"],
        capture_output=True,
        text=True
    )
    if chk.returncode != 0:
        err_msg = (chk.stderr or chk.stdout or "").strip()
        if "non DOS media" in err_msg or "Cannot initialize" in err_msg:
            raise MToolsError(
                "The hard disk is not formatted with a DOS/FAT filesystem. "
                "Please partition (FDISK) and format (FORMAT C:) the disk inside the VM before injecting files."
            )
        raise MToolsError(f"Cannot read hard disk filesystem: {err_msg}")

    # Ensure target directory exists
    clean_folder = target_folder.strip().replace("\\", "/").strip("/")
    if clean_folder:
        ensure_fat_dir(img_path, offset, clean_folder)
        dos_dest = f"::/{clean_folder}/"
    else:
        dos_dest = "::/"

    is_zip = (upload_file.filename or "").lower().endswith(".zip") and extract_zip

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_upload = os.path.join(tmpdir, "upload.tmp")
        with open(tmp_upload, "wb") as f:
            upload_file.file.seek(0)
            while chunk := upload_file.file.read(8192 * 1024):
                f.write(chunk)

        if is_zip:
            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(tmp_upload, "r") as z:
                    # Sanitize against path traversal (Zip Slip)
                    for member in z.infolist():
                        norm = os.path.normpath(member.filename)
                        if norm.startswith("..") or os.path.isabs(norm):
                            raise MToolsError(f"Security error: ZIP archive contains illegal path '{member.filename}'")
                    z.extractall(extract_dir)
            except zipfile.BadZipFile:
                raise MToolsError("Invalid or corrupted ZIP archive.")

            items = os.listdir(extract_dir)
            if not items:
                return {
                    "status": "success",
                    "message": "ZIP archive was empty, nothing injected.",
                    "extracted": True
                }

            src_paths = [os.path.join(extract_dir, item) for item in items]
            
            # Copy in batches to prevent exceeding command line argument limits
            BATCH_SIZE = 100
            for i in range(0, len(src_paths), BATCH_SIZE):
                batch = src_paths[i:i + BATCH_SIZE]
                cmd = [
                    "mcopy",
                    "-s",  # Recursive
                    "-p",  # Preserve timestamps
                    "-o",  # Overwrite
                    "-i", f"{img_path}@@{offset}",
                    *batch,
                    dos_dest
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    err_msg = (res.stderr or res.stdout or "").strip()
                    if "No space left" in err_msg or "Disk full" in err_msg or "Directory full" in err_msg:
                        raise MToolsError("Failed to inject files: Hard disk or directory is full.")
                    raise MToolsError(f"Failed to inject extracted ZIP contents: {err_msg}")

            dest_display = clean_folder if clean_folder else "root (\\)"
            return {
                "status": "success",
                "message": f"Successfully extracted and injected {upload_file.filename} into {dest_display}",
                "extracted": True,
                "target_folder": clean_folder
            }
        else:
            # Single file upload
            target_filename = os.path.basename(upload_file.filename or "upload.bin")
            dest_file = f"{dos_dest}{target_filename}"
            cmd = [
                "mcopy",
                "-p",
                "-o",
                "-i", f"{img_path}@@{offset}",
                tmp_upload,
                dest_file
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                err_msg = (res.stderr or res.stdout or "").strip()
                if "No space left" in err_msg or "Disk full" in err_msg or "Directory full" in err_msg:
                    raise MToolsError("Failed to inject file: Hard disk or directory is full.")
                raise MToolsError(f"File injection failed: {err_msg}")

            dest_display = clean_folder if clean_folder else "root (\\)"
            return {
                "status": "success",
                "message": f"Successfully injected {target_filename} into {dest_display}",
                "extracted": False,
                "target_folder": clean_folder
            }

def inject_file(img_path: str, upload_file: UploadFile) -> None:
    """Backwards-compatible wrapper."""
    inject_file_or_zip(img_path, upload_file, target_folder="", extract_zip=False)
