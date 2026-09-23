import os
import subprocess
import json
import tempfile
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
        
    except subprocess.CalledProcessError as e:
        # If sfdisk fails (e.g., no partition table at all), assume raw 0
        return 0
    except (json.JSONDecodeError, KeyError, IndexError):
        return 0

def inject_file(img_path: str, upload_file: UploadFile) -> None:
    """Injects a file into the root of the FAT filesystem inside the image."""
    offset = get_fat_offset(img_path)
    
    # Save the upload to a temp file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        # We need to read in chunks to avoid blowing up memory for large files
        upload_file.file.seek(0)
        while chunk := upload_file.file.read(8192 * 1024):
            tmp.write(chunk)
        tmp_path = tmp.name
        
    try:
        # Sanitize filename (DOS 8.3 format typically, but mcopy handles LFNs if configured)
        target_filename = os.path.basename(upload_file.filename or "upload.bin")
        
        # mcopy -i hdd.img@@offset -o temp_path ::/filename
        cmd = [
            "mcopy",
            "-i", f"{img_path}@@{offset}",
            "-o", # Overwrite without prompt
            tmp_path,
            f"::/{target_filename}"
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise MToolsError(f"File injection failed: {res.stderr}\n{res.stdout}")
            
    finally:
        os.unlink(tmp_path)
