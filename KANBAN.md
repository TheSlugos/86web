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



---

## ⚙️ In Progress / In Review
 
(All current sprint items completed!)
- [x] **File Injection via MTools (`feat-file-injector`)**
  - [x] Integrate `mtools` (`mcopy`, `sfdisk`) in backend container.
  - [x] Implement `POST /api/vms/{id}/hdd/{index}/inject` endpoint.
  - [x] Add file upload UI in VM Configuration Modal (Hard Disks tab).
  - [x] Fix TypeScript compilation errors (`vmApi` import and `vmId` guard).
  - [x] Add friendly HTTP 400 error handling when disk is unpartitioned or unformatted.
  - [x] Add protection preventing injection while VM is running.

---

## ✅ Completed

- [x] **86Box Native UNIX Socket IPC & Headless Hot-Swapping (`feat-hot-swap-hack` + `feat-unix-socket-ipc`)**
  - Added `QLocalServer` UNIX domain control socket (`/tmp/86box-ipc.sock`) to 86Box Qt mainwindow.
  - Implemented direct C++ commands (`cdrom_mount`, `cdrom_eject`, `fdd_mount`, `fdd_eject`) dispatched directly onto the GUI thread.
  - Replaced fragile GUI `xdotool` keystroke simulation in 86Web with direct UNIX domain socket IPC.
  - Added automated Docker builder container (`docker compose -f docker-compose.build-86box.yml up --build`) for reproducible one-command custom 86Box compilation without host dependencies.
  - Verified live mounting and ejecting on running VMs without rebooting.
- [x] **Fix Startup Floppy & CD-ROM Mounting (`main`)**
  - Fixed 86Box INI keys (`cdrom_{n}_fn`), removed numeric drive type mapping, and added proper `media/library/` path resolution.
- [x] **Fix Hardware Database Refresh 500 Error (`main`)**
  - Added missing `cache_dir` argument in `backend/app/routers/system.py`.
- [x] **Expand CPU Compatibility (`main`)**
  - Added Socket 3 / Slot 1 implicit socket mapping and compound socket parser for 486 / Pentium II processors.
