# 86Web Project Kanban & Roadmap

## 📋 Backlog (Ideas & Planned Features)

### Storage & Media
- [ ] **MTools Injector: Target Folder Selection**
  - Allow specifying or choosing a target subfolder (e.g. `::/TEMP`, `::/GAMES`) on the FAT partition instead of always injecting into root (`::/`).
  - Prevents root directory clutter and avoids FAT12/FAT16 512-entry root limit.
- [ ] **Download Hard Disk Images**
  - Add UI button to download existing `hdd{N}.img` files from the VM configuration modal.
- [ ] **Upload Pre-built Hard Disk Images**
  - Add UI option to upload an existing `.img` file to create or replace a virtual hard drive.
- [ ] **Host Folder to CD-ROM Share**
  - Configure a secondary CD-ROM mapped to a host folder or dynamic ISO generator so files uploaded via the web UI can be read as a CD drive inside DOS/Windows without rebooting.

### VM Management & Import/Export
- [ ] **Export VM Configuration**
  - Download/export a VM's `86box.cfg` file.
- [ ] **Import VM Configuration**
  - Upload an `86box.cfg` file to automatically parse and provision a new VM in 86Web.

### 86Box Core & Architecture
- [ ] **86Box Unix Domain Control Socket (Fork / Custom Build)**
  - Fork 86Box (`TheSlugos/86Box`) and implement a lightweight Unix domain socket server (`/tmp/86box-control-{uuid}.sock`) in `src/unix/`.
  - Expose direct RPC/text commands to call core emulator functions (`floppy_mount`, `floppy_eject`, `cdrom_mount`, `cdrom_eject`, `hard_reset`, etc.).
  - Completely eliminates UI-level keystroke/mouse automation fragility for live hypervisor management.

---

## ⚙️ In Progress / In Review

- [ ] **Media Hot-Swapping (`feat-hot-swap-hack`)**
  - Refine `xdotool` automation to reliably hot-swap media without reboots:
    1. Toggle menubar visible in fullscreen using `Ctrl+Alt+Page_Down` (`toggle_ui_fullscreen`).
    2. Click Media menu directly (`xdotool mousemove 115 10 click 1`) to avoid DOS input interception.
    3. Trigger `j` for live Floppy/CD eject.
    4. Trigger `e` and automate file dialog for mounting without string/quoting errors.
    5. Toggle menubar hidden to restore clean fullscreen view.
  - Plan: Resume testing on live containers tomorrow night.
- [x] **File Injection via MTools (`feat-file-injector`)**
  - [x] Integrate `mtools` (`mcopy`, `sfdisk`) in backend container.
  - [x] Implement `POST /api/vms/{id}/hdd/{index}/inject` endpoint.
  - [x] Add file upload UI in VM Configuration Modal (Hard Disks tab).
  - [x] Fix TypeScript compilation errors (`vmApi` import and `vmId` guard).
  - [x] Add friendly HTTP 400 error handling when disk is unpartitioned or unformatted.
  - [x] Add protection preventing injection while VM is running.

---

## ✅ Completed

- [x] **Fix Startup Floppy & CD-ROM Mounting (`main`)**
  - Fixed 86Box INI keys (`cdrom_{n}_fn`), removed numeric drive type mapping, and added proper `media/library/` path resolution.
- [x] **Fix Hardware Database Refresh 500 Error (`main`)**
  - Added missing `cache_dir` argument in `backend/app/routers/system.py`.
- [x] **Expand CPU Compatibility (`main`)**
  - Added Socket 3 / Slot 1 implicit socket mapping and compound socket parser for 486 / Pentium II processors.
