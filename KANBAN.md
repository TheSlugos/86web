# 86Web Project Kanban & Roadmap

## 📋 Backlog (Ideas & Planned Features)

### Storage & Media
- [ ] **Download Hard Disk Images** *(Deprioritized - file injector fulfilled file transfer need)*
  - Add UI button to download existing `hdd{N}.img` files from the VM configuration modal.
- [ ] **Upload Pre-built Hard Disk Images**
  - Add UI option to upload an existing `.img` file to create or replace a virtual hard drive.
- [ ] **Host Folder to CD-ROM Share** *(Deprioritized - file injector fulfilled file transfer need)*
  - Configure a secondary CD-ROM mapped to a host folder or dynamic ISO generator so files uploaded via the web UI can be read as a CD drive inside DOS/Windows without rebooting.

### Removable Media & IPC Controls
- [ ] **Audit & Refine Existing Image Functionality**
  - Audit existing image workflows (`ImagePickerModal.tsx`, `WritableImageBrowser.tsx`, `mediaApi`, `/library` vs per-VM media).
  - Clarify and fix issues where images can or cannot be mounted, deleted, or shared across VMs.

### Security & Production Hardening (Pre-Deployment)
- [ ] **Enforce Random `APP_SECRET_KEY` Generation**
  - Prevent startup or warn loudly if `APP_SECRET_KEY` remains the default placeholder (`changeme_secret`) to prevent JWT token forgery.
- [ ] **VNC WebSocket & Audio Stream Authentication**
  - Require token validation on `/vnc/{vm_id}/websockify` and `/vms/{vm_id}/audio` so unauthenticated users cannot view screens or listen to audio without logging in.
- [ ] **Login Rate Limiting**
  - Add brute-force protection / throttling to `POST /api/auth/token`.
- [ ] **Production Deployment Documentation**
  - Document best practices for public deployment (e.g. Cloudflare Zero Trust / Access, VNC passwords, SSL termination).

### UI & Input Controls
- [ ] **Windows 3.1 & DOS Mouse Movement Investigation**
  - Investigate cursor freezing/clipping when moving towards the top of the screen in Windows 3.1.
  - Check browser pointer lock (`requestPointerLock`) integration in noVNC canvas.
  - Check 86Box Qt menu bar / window border offset along the top edge inside Xvfb.
  - Verify guest mouse driver selection (Logitech Bus Mouse vs Microsoft PS/2 / Serial).

### Virtual Networking & Multiplayer Gaming Lab
- [ ] **Explore & Verify VM Group Networking**
  - Verify bridged TAP interfaces and PCap permissions (`cap_wrap`) across VMs assigned to the same network group.
  - Test packet drivers (NE2000 / Novell IPX) inside DOS/Win9x guests.
  - Setup a two-VM DOOM deathmatch over IPX network.

### Testing & Quality Assurance
- [ ] **Comprehensive Test Suite & Verification Plan**
  - Create integration test suite and checklist covering:
    - FAT hard disk file & recursive ZIP injector (`mtools`).
    - Live floppy/CD-ROM mounting, ejecting, write-protection toggling over IPC.
    - VM lifecycle controls (`hard_reset`, `pause`/`resume`, `cad`, clean `power_off`).
    - VM config JSON export & import with sanitization and name collision handling.

### Production Deployment & Migration
- [ ] **Deploy Custom 86Web Instance to Production Server**
  - Package and deploy custom 86Web build (`TheSlugos/86web` + `TheSlugos/86Box`) to replace the standard instance on the server.
  - Verify persistent data migration (`/data/vms`, `/data/roms`, database).

---

## ⚙️ In Progress / Next Up

1. **Windows 3.1 Mouse Quirk Debugging**
2. **Comprehensive Test Suite & Verification Plan**
3. **Deploy Custom 86Web to Production Server**
4. **Security Hardening (JWT Secret, Stream Auth, Rate Limiting)**
5. **VM Group Networking Lab (Multiplayer DOOM)**

---

## ✅ Completed

- [x] **VM Configuration Export & Import (`feat-import-export-vm-config`)**
  - **Native JSON Architecture**: Export and import complete VM configurations using 86Web's native JSON representation, ensuring 100% schema fidelity with zero loss of hardware options or bus filter conflicts.
  - **Media Path Sanitization**: Automatically strips private per-VM media paths (`/data/vms/.../media/`) on export and import while safely preserving shared library paths (`/library/...`).
  - **Smart Name Deduplication**: Handles import name collisions automatically using an incrementing counter (`(Imported)`, `(Imported 2)`).
  - **Format Validation**: Validates file structure, format tag (`86web-vm-config`), and required configuration parameters.
  - **Accessible Everywhere**: Export available in Grid View (`VMCard`), Table View (`VMTableRow`), and inside the VM Configuration Modal (`VMConfigModal`). Import available in the main toolbar and empty state screen.

- [x] **Rewire Console Toolbar Actions to Native IPC (`feat-ipc-lifecycle`)**
  - **Instant Hardware Reset**: Rewired "Reset" to dispatch `hard_reset` over native UNIX IPC (`pc_reset_hard()`), resetting guest CPU/BIOS instantly without killing the runner process, restarting PulseAudio, or dropping/reconnecting the VNC viewer session.
  - **Native Pause & Resume**: Rewired "Pause" to dispatch `pause` (`plat_pause(1)`) and `resume` (`plat_pause(0)`) over native IPC, immediately syncing VM database status (`"paused"` / `"running"`) without reliance on `SIGSTOP`/`SIGCONT`.
  - **Native Ctrl+Alt+Del**: Fast-pathed CAD (`ctrl+F12` / `cad`) to dispatch `cad` over native IPC (`pc_send_cad()`) directly into 86Box's keyboard buffer.
  - **Clean Virtual Disk Cache Flush on Stop**: Updated `stop_vm` to send `power_off` over native IPC first, waiting for 86Box to cleanly flush virtual disk caches to disk before process cleanup.
  - **Resilient Fallbacks**: Preserved existing process restart, OS signal (`SIGSTOP`/`SIGCONT`), and `xdotool` pathways as fallbacks if the IPC socket is unavailable.

- [x] **MTools Injector: Target Folder Selection & ZIP Archive Extraction (`feat-file-injector`)**
  - Added recursive FAT directory creation (`ensure_fat_dir` via `mmd`) supporting any target directory path (e.g. `GAMES/DOOM`).
  - Added automated `.zip` archive extraction and recursive tree copy (`mcopy -s -p -o`), preserving directory structures for game and tool installs.
  - Added path traversal / Zip Slip security checks and batch copy handling to avoid argument length limits.
  - Enhanced Hard Disks UI in `VMConfigModal.tsx` with dedicated target folder inputs and ZIP extraction toggle.
- [x] **Removable Media ("Drives") Menu in VNC Console Toolbar (`VNCViewer.tsx`) (`main`)**
  - Added interactive "Drives ▾" dropdown menu to console toolbar displaying all configured floppies and CD-ROMs.
  - Supports live disk insertion (`ImagePickerModal`), disk swapping, disk ejection, and floppy write-protection toggling.
  - Automatically updates VM database configuration and dispatches live commands over per-VM UNIX socket IPC.

- [x] **Custom 86Box Automated Release Pipeline & 86Web Distribution (`TheSlugos/86Box` + `TheSlugos/86web`)**
  - Created GitHub Actions workflow `.github/workflows/release.yml` in `TheSlugos/86Box` building on Ubuntu 22.04 LTS (x86_64, Qt6, SDL2).
  - Successfully tagged and published GitHub Release [`v7.0.0-86web.1`](https://github.com/TheSlugos/86Box/releases/tag/v7.0.0-86web.1) containing `86Box-Linux-x86_64-v7.0.0-86web.1.tar.gz`.
  - Updated 86Web's runner configuration (`RunnerSettings.box86_repo`), `updater.py`, `docker-compose.yml`, and `.env.example` to default to `TheSlugos/86Box`.
  - Enables clean, automated deployment for any user without requiring local 86Box source compilation.
- [x] **86Box Dynamic Per-VM UNIX Socket IPC & Headless Control (`TheSlugos/86Box:master` + `86web:feat-hot-swap-hack`)**
  - Implemented dynamic per-VM socket isolation defaulting to `<vmpath>/86box-ipc.sock` (with CLI override `--socketpath <path>`), eliminating multi-VM collisions.
  - Added bidirectional protocol with synchronous responses (`OK`, `ERROR`, `PONG`).
  - Implemented floppy write-protection flag (`fdd_mount <id> [ro|rw] <path>`).
  - Added live drive status queries (`fdd_status <id>`, `cdrom_status <id>`).
  - Added native lifecycle commands (`reset`, `hard_reset`, `pause`, `resume`, `power_off`, `acpi_shutdown`).
  - Implemented clean socket unlinking on exit in both 86Box (`closeEvent` / destructor) and 86Web runner (`stop_vm`).
  - Updated 86Web backend schemas and runner IPC client to route commands to per-VM sockets.
  - Created automated Docker compilation workflow (`docker compose -f docker-compose.build-86box.yml up --build`).
  - Fully verified and merged into `TheSlugos/86Box:master`.
- [x] **File Injection via MTools (`feat-file-injector`)**
  - [x] Integrate `mtools` (`mcopy`, `sfdisk`) in backend container.
  - [x] Implement `POST /api/vms/{id}/hdd/{index}/inject` endpoint.
  - [x] Add file upload UI in VM Configuration Modal (Hard Disks tab).
  - [x] Fix TypeScript compilation errors (`vmApi` import and `vmId` guard).
  - [x] Add friendly HTTP 400 error handling when disk is unpartitioned or unformatted.
  - [x] Add protection preventing injection while VM is running.
- [x] **Fix Startup Floppy & CD-ROM Mounting (`main`)**
  - Fixed 86Box INI keys (`cdrom_{n}_fn`), removed numeric drive type mapping, and added proper `media/library/` path resolution.
- [x] **Fix Hardware Database Refresh 500 Error (`main`)**
  - Added missing `cache_dir` argument in `backend/app/routers/system.py`.
- [x] **Expand CPU Compatibility (`main`)**
  - Added Socket 3 / Slot 1 implicit socket mapping and compound socket parser for 486 / Pentium II processors.
