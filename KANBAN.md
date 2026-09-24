# 86Web Project Kanban & Roadmap

## 📋 Backlog (Ideas & Planned Features)

### Storage & Media
- [ ] **MTools Injector: Target Folder Selection & ZIP Archive Extraction**
  - Allow specifying a target subfolder (e.g. `::/TEMP`, `::/GAMES`) on the FAT partition instead of always injecting into root (`::/`).
  - Add automatic extraction for `.zip` archive uploads, allowing entire game/tool directory structures to be unzipped directly onto the FAT hard drive.
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

### 86Box Custom IPC & Architecture (Future Refinements)
- [ ] **Per-VM Dynamic Socket Path (`--socketpath` or `${vmpath}/ipc.sock`)**
  - Currently `/tmp/86box-ipc.sock` is hardcoded. If multiple VMs run concurrently, they collide on this socket.
  - Add CLI argument `--socketpath <path>` or automatically default to `<vmpath>/86box-ipc.sock` so concurrent VMs each have an isolated control channel.
- [ ] **Floppy Write-Protection Flag via IPC**
  - Currently `fdd_mount` defaults write-protection to `false` (`floppyMount(id, path, false)`).
  - Add support for an optional flag (e.g. `fdd_mount <id> [ro|rw] <path>`) so users can mount floppies write-protected when desired.
- [ ] **VM Lifecycle & State Control via IPC**
  - Add IPC commands for soft reset (`reset`), hard reset (`hard_reset`), pause/resume (`pause`, `resume`), and ACPI shutdown (`acpi_power_button`) instead of relying solely on process signals.
- [ ] **Drive Status Query via IPC**
  - Add bidirectional response capability (e.g. `drive_query`) so 86Web can query 86Box directly for the active image path and status of each drive.

### Security & Production Hardening (Pre-Deployment)
- [ ] **Enforce Random `APP_SECRET_KEY` Generation**
  - Prevent startup or warn loudly if `APP_SECRET_KEY` remains the default placeholder (`changeme_secret`) to prevent JWT token forgery.
- [ ] **VNC WebSocket & Audio Stream Authentication**
  - Require token validation on `/vnc/{vm_id}/websockify` and `/vms/{vm_id}/audio` so unauthenticated users cannot view screens or listen to audio without logging in.
- [ ] **Login Rate Limiting**
  - Add brute-force protection / throttling to `POST /api/auth/token`.
- [ ] **Production Deployment Documentation**
  - Document best practices for public deployment (e.g. Cloudflare Zero Trust / Access, VNC passwords, SSL termination).

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
