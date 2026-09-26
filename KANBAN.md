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

### Frontend UI & Removable Media Controls
- [ ] **Removable Media ("Drives") Menu in VNC Console Toolbar (`VNCViewer.tsx`)**
  - Add an interactive "Drives" / "Removable Media" dropdown menu to the active VM viewer toolbar.
  - List configured Floppy (A:, B:) and CD-ROM drives with current status (mounted image filename or `[Empty]`).
  - Provide live actions: "Insert Image..." (opens image picker), "Eject", and a write-protection toggle for floppies.
  - Wire to `vmApi.mountDrive(vmId, driveKey, path, writeProtected)` and `vmApi.ejectDrive(vmId, driveKey)`.
- [ ] **Audit & Refine Existing Image Functionality**
  - Audit existing image workflows (`ImagePickerModal.tsx`, `WritableImageBrowser.tsx`, `mediaApi`, `/library` vs per-VM media).
  - Clarify and fix issues where images can or cannot be mounted, deleted, or shared across VMs.
- [ ] **Rewire Console Toolbar Actions to Native IPC**
  - Switch "Reset" button in `VNCViewer.tsx` to send `hard_reset` over the IPC socket instead of terminating/re-launching the runner process.
  - Switch "Pause" button in `VNCViewer.tsx` to send `plat_pause()` over the IPC socket instead of Linux `SIGSTOP`/`SIGCONT` signals.

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

- [ ] **Frontend Removable Media UI & Existing Image Functionality Audit**
  - Designing and implementing the live drive mount/eject UI and testing current media browser behavior.

---

## ✅ Completed

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
