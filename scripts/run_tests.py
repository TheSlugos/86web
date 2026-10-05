#!/usr/bin/env python3
"""
86Web Unified Test Suite Runner
Runs both Frontend (Node) and Backend (pytest) automated tests.
"""

import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run_frontend_tests() -> bool:
    print("\n" + "=" * 60)
    print(" >>> RUNNING FRONTEND TESTS (Node test runner)")
    print("=" * 60)
    frontend_dir = os.path.join(REPO_ROOT, "frontend")
    cmd = ["node", "--experimental-strip-types", "--test", "src/lib/__tests__/*.test.ts"]
    try:
        res = subprocess.run(cmd, cwd=frontend_dir)
        return res.returncode == 0
    except FileNotFoundError:
        print("[-] Error: 'node' executable not found in PATH.")
        return False


def run_backend_tests() -> bool:
    print("\n" + "=" * 60)
    print(" >>> RUNNING BACKEND TESTS (pytest)")
    print("=" * 60)

    # Use virtual environment python/pytest if present, else fallback to sys.executable
    venv_pytest_win = os.path.join(REPO_ROOT, "backend", ".venv", "Scripts", "pytest.exe")
    venv_pytest_posix = os.path.join(REPO_ROOT, "backend", ".venv", "bin", "pytest")

    if os.path.isfile(venv_pytest_win):
        pytest_cmd = [venv_pytest_win]
    elif os.path.isfile(venv_pytest_posix):
        pytest_cmd = [venv_pytest_posix]
    else:
        pytest_cmd = [sys.executable, "-m", "pytest"]

    cmd = pytest_cmd + ["backend/tests", "-v"]

    env = os.environ.copy()
    backend_path = os.path.join(REPO_ROOT, "backend")
    runner_path = os.path.join(REPO_ROOT, "runner")
    sep = os.pathsep
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_path}{sep}{runner_path}{sep}{REPO_ROOT}{sep}{existing_pp}"

    try:
        res = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
        return res.returncode == 0
    except Exception as e:
        print(f"[-] Error running backend tests: {e}")
        return False


def main():
    frontend_ok = run_frontend_tests()
    backend_ok = run_backend_tests()

    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    print(f" Frontend Tests: {'[PASS]' if frontend_ok else '[FAIL]'}")
    print(f" Backend Tests:  {'[PASS]' if backend_ok else '[FAIL]'}")
    print("=" * 60)

    if not (frontend_ok and backend_ok):
        sys.exit(1)
    print("All test suites passed successfully!\n")


if __name__ == "__main__":
    main()
