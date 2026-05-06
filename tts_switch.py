import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox


BASE_DIR = Path(__file__).resolve().parent
TTS_SCRIPT = BASE_DIR / "tts_local_server.py"
BACKEND_SCRIPT = BASE_DIR / "run_backend.py"

TTS_PID_FILE = BASE_DIR / ".tts_server.pid"
BACKEND_PID_FILE = BASE_DIR / ".backend_server.pid"
CLOUDFLARED_PID_FILE = BASE_DIR / ".cloudflared.pid"
STACK_STATE_FILE = BASE_DIR / ".tts_stack_state.json"

TTS_OUT_LOG = BASE_DIR / "tts_server.out.log"
TTS_ERR_LOG = BASE_DIR / "tts_server.err.log"
BACKEND_OUT_LOG = BASE_DIR / "backend_server.out.log"
BACKEND_ERR_LOG = BASE_DIR / "backend_server.err.log"
CLOUDFLARED_LOG = BASE_DIR / "cloudflared_tts.log"
VERCEL_LOG = BASE_DIR / "vercel_tts_update.log"

TTS_HEALTH_URL = "http://127.0.0.1:8020/health"
BACKEND_URL = "http://127.0.0.1:8000/"
BACKEND_TTS_URL = "http://127.0.0.1:8000/api/tts"
TUNNEL_LOCAL_URL = "http://127.0.0.1:8000"

DEFAULT_TTS_PYTHON = r"C:\Users\math\anaconda3\envs\mathwi\python.exe"
DEFAULT_BACKEND_PYTHON = r"C:\Users\math\anaconda3\python.exe"


def creation_flags() -> int:
    return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "CREATE_NO_WINDOW", 0
    )


def get_tts_python() -> str:
    return os.getenv("MINDBUDDHI_TTS_PYTHON", DEFAULT_TTS_PYTHON)


def get_backend_python() -> str:
    return os.getenv("MINDBUDDHI_BACKEND_PYTHON", DEFAULT_BACKEND_PYTHON)


def append_log(path: Path, text: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n[{timestamp}] {text}\n")


def get_json(url: str, timeout: float = 1.5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                return None
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def get_tts_health() -> dict | None:
    return get_json(TTS_HEALTH_URL)


def is_tts_ready() -> bool:
    health = get_tts_health()
    return bool(
        health
        and health.get("ok")
        and health.get("model_loaded")
        and health.get("voice_latents_loaded")
    )


def is_backend_ready() -> bool:
    try:
        with urllib.request.urlopen(BACKEND_URL, timeout=1.5) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def write_pid(path: Path, pid: int) -> None:
    path.write_text(str(pid), encoding="utf-8")


def process_exists(pid: int) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return str(pid) in result.stdout


def find_port_pid(port: int) -> int | None:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    suffix = f":{port}"
    for line in result.stdout.splitlines():
        normalized = " ".join(line.split())
        if "LISTENING" not in normalized:
            continue
        parts = normalized.split()
        if len(parts) >= 5 and parts[1].endswith(suffix):
            try:
                return int(parts[-1])
            except ValueError:
                return None
    return None


def stop_pid_file(path: Path, port: int | None = None) -> None:
    pid = read_pid(path)
    if pid and not process_exists(pid):
        pid = None
    if pid is None and port is not None:
        pid = find_port_pid(port)
    if pid:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    path.unlink(missing_ok=True)


def start_tts_server(progress=None) -> tuple[bool, str]:
    if is_tts_ready():
        return True, "TTS model is already ready."

    tts_python = Path(get_tts_python())
    if not tts_python.exists():
        return False, f"TTS Python not found: {tts_python}"

    if progress:
        progress("Starting local TTS server on port 8020...")

    env = os.environ.copy()
    env["COQUI_TOS_AGREED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    with TTS_OUT_LOG.open("ab") as out_log, TTS_ERR_LOG.open("ab") as err_log:
        process = subprocess.Popen(
            [str(tts_python), str(TTS_SCRIPT)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=out_log,
            stderr=err_log,
            creationflags=creation_flags(),
        )
    write_pid(TTS_PID_FILE, process.pid)

    for _ in range(180):
        if is_tts_ready():
            return True, "TTS model is ready."
        if process.poll() is not None:
            return False, "TTS server exited while starting. Check tts_server.err.log."
        time.sleep(1)
    return False, "TTS server did not finish warmup in time."


def start_backend_server(progress=None) -> tuple[bool, str]:
    if is_backend_ready():
        return True, "Backend is already running."

    backend_python = Path(get_backend_python())
    if not backend_python.exists():
        return False, f"Backend Python not found: {backend_python}"

    if progress:
        progress("Starting local backend on port 8000...")

    env = os.environ.copy()
    env["MINDBUDDHI_TTS_URL"] = BACKEND_TTS_URL.replace(":8000", ":8020")
    env["MINDBUDDHI_TTS_FALLBACK"] = "0"

    with BACKEND_OUT_LOG.open("ab") as out_log, BACKEND_ERR_LOG.open("ab") as err_log:
        process = subprocess.Popen(
            [str(backend_python), str(BACKEND_SCRIPT)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=out_log,
            stderr=err_log,
            creationflags=creation_flags(),
        )
    write_pid(BACKEND_PID_FILE, process.pid)

    for _ in range(45):
        if is_backend_ready():
            return True, "Backend is ready."
        if process.poll() is not None:
            return False, "Backend exited while starting. Check backend_server.err.log."
        time.sleep(1)
    return False, "Backend did not start in time."


def start_cloudflared(progress=None) -> tuple[bool, str]:
    cloudflared = shutil.which("cloudflared")
    if not cloudflared:
        return False, "cloudflared was not found."

    if progress:
        progress("Starting Cloudflare quick tunnel...")

    stop_pid_file(CLOUDFLARED_PID_FILE)
    CLOUDFLARED_LOG.write_text("", encoding="utf-8")

    with CLOUDFLARED_LOG.open("ab") as log:
        process = subprocess.Popen(
            [
                cloudflared,
                "tunnel",
                "--url",
                TUNNEL_LOCAL_URL,
                "--protocol",
                "quic",
                "--ha-connections",
                "1",
            ],
            cwd=str(BASE_DIR),
            stdout=log,
            stderr=log,
            creationflags=creation_flags(),
        )
    write_pid(CLOUDFLARED_PID_FILE, process.pid)

    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    for _ in range(60):
        if process.poll() is not None:
            return False, "cloudflared exited while starting. Check cloudflared_tts.log."
        text = CLOUDFLARED_LOG.read_text(encoding="utf-8", errors="replace")
        match = pattern.search(text)
        if match:
            url = match.group(0)
            return True, f"{url}/api/tts"
        time.sleep(1)
    return False, "Could not find quick tunnel URL in cloudflared output."


def run_vercel_command(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
    vercel = shutil.which("vercel.cmd") or shutil.which("vercel")
    if not vercel:
        raise RuntimeError("Vercel CLI was not found.")
    return subprocess.run(
        [vercel, *args],
        cwd=str(BASE_DIR),
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=180,
    )


def update_vercel_tts_url(tts_url: str, progress=None) -> tuple[bool, str]:
    if progress:
        progress("Updating Vercel MINDBUDDHI_TTS_URL...")

    VERCEL_LOG.write_text("", encoding="utf-8")

    add = run_vercel_command(
        [
            "env",
            "add",
            "MINDBUDDHI_TTS_URL",
            "production",
            "--value",
            tts_url,
            "--yes",
            "--sensitive",
            "--force",
        ],
    )
    append_log(VERCEL_LOG, "vercel env add\n" + add.stdout + add.stderr)
    if add.returncode != 0:
        return False, "Failed to update Vercel env. Check vercel_tts_update.log."

    if progress:
        progress("Redeploying Vercel production...")
    deploy = run_vercel_command(["--prod", "--yes"])
    append_log(VERCEL_LOG, "vercel --prod --yes\n" + deploy.stdout + deploy.stderr)
    if deploy.returncode != 0:
        return False, "Vercel deploy failed. Check vercel_tts_update.log."

    STACK_STATE_FILE.write_text(
        json.dumps(
            {
                "tts_url": tts_url,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return True, f"Ready. Vercel now points to {tts_url}"


def start_voice_stack(progress=None) -> tuple[bool, str]:
    ok, message = start_tts_server(progress)
    if not ok:
        return ok, message

    ok, message = start_backend_server(progress)
    if not ok:
        return ok, message

    ok, tunnel_url = start_cloudflared(progress)
    if not ok:
        return ok, tunnel_url

    return update_vercel_tts_url(tunnel_url, progress)


def stop_voice_stack() -> tuple[bool, str]:
    stop_pid_file(CLOUDFLARED_PID_FILE)
    stop_pid_file(BACKEND_PID_FILE, 8000)
    stop_pid_file(TTS_PID_FILE, 8020)
    STACK_STATE_FILE.unlink(missing_ok=True)
    return True, "Stopped TTS server, backend, and tunnel."


def load_state() -> dict:
    try:
        return json.loads(STACK_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


class TtsSwitchApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MindBuddhi Voice Server Switch")
        self.root.geometry("520x320")
        self.root.resizable(False, False)
        self.status_var = tk.StringVar(value="Checking status...")
        self.detail_var = tk.StringVar(value="")
        self.busy = False
        self.auto_connect_attempted = False

        frame = tk.Frame(root, padx=22, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="MindBuddhi Voice Server", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 12), fg="#166534", pady=10).pack(anchor="w")
        tk.Label(
            frame,
            textvariable=self.detail_var,
            font=("Segoe UI", 9),
            fg="#555555",
            wraplength=460,
            justify="left",
        ).pack(anchor="w")

        buttons = tk.Frame(frame, pady=16)
        buttons.pack(fill="x")

        self.start_btn = tk.Button(buttons, text="Start + Connect Vercel", width=22, command=self.start_clicked)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = tk.Button(buttons, text="Stop", width=10, command=self.stop_clicked)
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.refresh_btn = tk.Button(buttons, text="Refresh", width=10, command=self.refresh)
        self.refresh_btn.pack(side="left")

        log_buttons = tk.Frame(frame)
        log_buttons.pack(fill="x")
        tk.Button(log_buttons, text="TTS Log", command=lambda: self.open_path(TTS_ERR_LOG)).pack(side="left", padx=(0, 8))
        tk.Button(log_buttons, text="Tunnel Log", command=lambda: self.open_path(CLOUDFLARED_LOG)).pack(side="left", padx=(0, 8))
        tk.Button(log_buttons, text="Vercel Log", command=lambda: self.open_path(VERCEL_LOG)).pack(side="left")

        tk.Label(
            frame,
            text="Start waits until the model is ready, creates a quick tunnel, updates Vercel, and redeploys production.",
            font=("Segoe UI", 9),
            fg="#777777",
            pady=12,
            wraplength=460,
            justify="left",
        ).pack(anchor="w")

        self.refresh()
        self.root.after(1000, self.auto_connect_if_needed)
        self.root.after(4000, self.auto_refresh)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.start_btn.configure(state=state)
        self.stop_btn.configure(state=state)
        self.refresh_btn.configure(state=state)

    def auto_refresh(self) -> None:
        if not self.busy:
            self.refresh(show_detail=False)
            self.auto_connect_if_needed()
        self.root.after(4000, self.auto_refresh)

    def auto_connect_if_needed(self) -> None:
        if self.busy or self.auto_connect_attempted:
            return
        state = load_state()
        if is_tts_ready() and not (is_backend_ready() and state.get("tts_url")):
            self.auto_connect_attempted = True
            self.run_in_background(start_voice_stack, "Voice Server")

    def refresh(self, show_detail: bool = True) -> None:
        state = load_state()
        if is_tts_ready() and is_backend_ready() and state.get("tts_url"):
            self.status_var.set("Status: ON and connected")
            self.detail_var.set(f"Vercel TTS URL: {state['tts_url']}")
        elif is_tts_ready():
            self.status_var.set("Status: local TTS ready")
            self.detail_var.set("TTS is ready locally, but Vercel is not marked connected from this switch.")
        else:
            self.status_var.set("Status: OFF")
            if show_detail:
                self.detail_var.set("Press Start before using Buddhi voice on the .com site.")

    def run_in_background(self, action, success_title: str) -> None:
        def progress(message: str) -> None:
            self.root.after(0, lambda: self.detail_var.set(message))

        def worker() -> None:
            ok, message = action(progress) if action is start_voice_stack else action()
            self.root.after(0, lambda: self.finish_action(ok, message, success_title))

        self.set_busy(True)
        self.status_var.set("Working...")
        threading.Thread(target=worker, daemon=True).start()

    def finish_action(self, ok: bool, message: str, success_title: str) -> None:
        self.set_busy(False)
        self.refresh(show_detail=False)
        self.detail_var.set(message)
        if not ok:
            messagebox.showerror("MindBuddhi Voice Server Switch", message)
        else:
            messagebox.showinfo(success_title, message)

    def start_clicked(self) -> None:
        self.run_in_background(start_voice_stack, "Voice Server")

    def stop_clicked(self) -> None:
        self.run_in_background(stop_voice_stack, "Voice Server")

    def open_path(self, path: Path) -> None:
        if not path.exists():
            path.write_text("", encoding="utf-8")
        os.startfile(path)


def main() -> int:
    root = tk.Tk()
    TtsSwitchApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
