"""Production Single-Command Unified Launcher for The SilentZone Sentinel.
Starts both the FastAPI Backend and Streamlit Frontend concurrently in a single process.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def main():
    print("=======================================================")
    print("  🛡️  The SilentZone Sentinel — Production Server")
    print("  Prepared by: Malik Junaid Ahmad & Saira Khan")
    print("=======================================================")

    backend_port = os.getenv("PORT_BACKEND", "8000")
    frontend_port = os.getenv("PORT", "8501")

    # 1. Start FastAPI Backend in background
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(backend_port),
    ]

    print(f"[*] Starting Backend API on port {backend_port}...")
    backend_process = subprocess.Popen(backend_cmd, cwd=str(ROOT_DIR))

    # Wait 2 seconds for backend to initialize
    time.sleep(2)

    # 2. Start Streamlit Frontend
    frontend_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        "--server.port",
        str(frontend_port),
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
        "--server.runOnSave",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    print(f"[*] Starting Frontend UI on port {frontend_port}...")
    print(f"[*] Live Dashboard: http://0.0.0.0:{frontend_port}")
    print("=======================================================")

    try:
        frontend_process = subprocess.Popen(frontend_cmd, cwd=str(ROOT_DIR))
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n[!] Shutting down services...")
    finally:
        backend_process.terminate()
        try:
            frontend_process.terminate()
        except Exception:
            pass
        print("[+] All services stopped gracefully.")

if __name__ == "__main__":
    main()
