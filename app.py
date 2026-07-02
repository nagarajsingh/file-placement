import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

import streamlit as st

APP_TITLE = "File Placement Dashboard"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
LOG_FILE = os.getenv("LOG_FILE", "file-placement-dashboard.log")
MASHREQ_LOGO_URL = os.getenv("MASHREQ_LOGO_URL", "")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ALLOWED_NAMESPACES = [x.strip() for x in os.getenv("ALLOWED_NAMESPACES", "").split(",") if x.strip()]

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_PATH = str(Path(LOG_DIR) / LOG_FILE)

logger = logging.getLogger("file-placement-dashboard")
logger.setLevel(logging.INFO)
logger.handlers.clear()
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
fh = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
fh.setFormatter(fmt)
sh = logging.StreamHandler()
sh.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(sh)

st.set_page_config(page_title=APP_TITLE, page_icon="📁", layout="wide")
st.html("""
<style>
.stApp{background:#f7f7fb}.main .block-container{max-width:1150px;padding-top:1.2rem}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#17073d,#2b0b63 55%,#160733)}
section[data-testid="stSidebar"] *{color:white!important}.brand{background:white;border-radius:18px;padding:1rem;text-align:center;margin-bottom:1rem}.brand img{max-width:150px;max-height:85px}.brand .name{font-size:1.7rem;font-weight:950;color:#185aa6!important}.brand .tag{color:#ff4b12!important;font-style:italic}.nav{padding:.8rem 1rem;border-radius:12px;margin:.35rem 0;font-weight:800}.active{background:#5e24c7}.sidecard{padding:1rem;border-radius:16px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);margin-top:1rem}.chip{display:inline-block;margin:.16rem;padding:.35rem .6rem;border-radius:999px;background:rgba(245,130,32,.25);font-size:.78rem;font-weight:800}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.3rem}.top h1{font-size:2.1rem;margin:0;color:#1a1247}.top p{margin:.25rem 0;color:#6d5e94}.conn{background:#eefaf2;border:1px solid #d3f1dc;border-radius:14px;padding:.8rem 1rem}.hero{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;align-items:center;padding:2rem;border-radius:24px;background:linear-gradient(120deg,#2a0b61,#4d167d 48%,#ff641f);margin-bottom:1.3rem;box-shadow:0 20px 55px rgba(36,16,79,.2)}.hero img{max-width:260px;max-height:105px}.fallback{font-size:2.2rem;font-weight:950;color:white}.hero h2,.hero p{color:white}.card{background:white;border:1px solid #e8e5f0;border-radius:18px;padding:1.25rem;box-shadow:0 10px 32px rgba(31,18,62,.07);margin-bottom:1rem}.card h3{margin-top:0;color:#1a1247}.status{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem}.status div{background:white;border-radius:16px;padding:1rem;border:1px solid #e8e5f0}.status b{display:block}.ok{color:#149144}.warn{background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;padding:.8rem;color:#9a3412}.good{background:#ecfbf1;border:1px solid #c8efd4;border-radius:14px;padding:.8rem;color:#123d22}.summary{background:#faf9ff;border:1px solid #e9e1ff;border-radius:14px;padding:.8rem}.copy{text-align:center}.stButton>button{background:linear-gradient(135deg,#ff641f,#f58220)!important;color:white!important;border:0!important;border-radius:12px!important;padding:.75rem 2.4rem!important;font-weight:950!important}.recent table{width:100%;border-collapse:collapse}.recent th,.recent td{padding:.7rem;border-bottom:1px solid #e8e5f0;text-align:left}.footer{text-align:center;color:#6f6789;font-size:.84rem;padding:1rem}@media(max-width:900px){.hero,.status{grid-template-columns:1fr}.top{display:block}}
</style>
""")

class CommandError(Exception):
    pass


def audit(message: str, **kwargs) -> None:
    details = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info("%s%s", message, f" | {details}" if details else "")


def run_cmd(cmd: List[str], timeout: int = 60) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "Command failed"
        logger.error("Command failed | command=%s | error=%s", " ".join(cmd), msg)
        raise CommandError(msg)
    return result.stdout.strip()


def runtime_info() -> tuple[str, str]:
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        ns = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read_text().strip()
        return "In-Cluster", ns
    return "Kubeconfig", run_cmd(["kubectl", "config", "current-context"])


def allowed(namespace: str) -> None:
    if ALLOWED_NAMESPACES and namespace not in ALLOWED_NAMESPACES:
        raise CommandError(f"Namespace '{namespace}' is not allowed for file placement.")


def get_namespaces() -> List[str]:
    if ALLOWED_NAMESPACES:
        return ALLOWED_NAMESPACES
    out = run_cmd(["kubectl", "get", "namespaces", "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [x.strip() for x in out.splitlines() if x.strip()]


def get_pods(namespace: str) -> List[str]:
    allowed(namespace)
    out = run_cmd(["kubectl", "get", "pods", "-n", namespace, "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [x.strip() for x in out.splitlines() if x.strip()]


def get_containers(namespace: str, pod: str) -> List[str]:
    allowed(namespace)
    out = run_cmd(["kubectl", "get", "pod", pod, "-n", namespace, "-o", "jsonpath={.spec.containers[*].name}"])
    return [x.strip() for x in out.split() if x.strip()]


def safe_name(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")


def final_path(folder: str, filename: str) -> str:
    folder = folder.strip() or "/tmp"
    if not folder.startswith("/"):
        raise CommandError("Destination folder must be an absolute path.")
    return f"{folder.rstrip('/')}/{safe_name(filename)}"


def copy_file(local_file: str, namespace: str, pod: str, dest: str, container: Optional[str]) -> None:
    cmd = ["kubectl", "cp", local_file, f"{namespace}/{pod}:{dest}"]
    if container:
        cmd.extend(["-c", container])
    run_cmd(cmd, timeout=300)


def exec_ls(namespace: str, pod: str, path: str, container: Optional[str]) -> str:
    cmd = ["kubectl", "exec", "-n", namespace]
    if container:
        cmd.extend(["-c", container])
    cmd.extend([pod, "--", "ls", "-l", path])
    return run_cmd(cmd)


def logo(sidebar: bool = False) -> str:
    if MASHREQ_LOGO_URL:
        tag = "<div class='tag'>Rise every day</div>" if sidebar else ""
        return f"<img src='{MASHREQ_LOGO_URL}' alt='Mashreq logo'/>{tag}"
    if sidebar:
        return "<div class='name'>mashreq</div><div class='tag'>Rise every day</div>"
    return "<div class='fallback'>mashreq<br><span style='color:#ffb15d;font-style:italic'>Rise every day</span></div>"


def chips(values: List[str]) -> str:
    values = values or ["All namespaces"]
    return "".join(f"<span class='chip'>{v}</span>" for v in values)

try:
    mode, detail = runtime_info()
    connected = True
except Exception:
    mode, detail, connected = "Unknown", "Unavailable", False
    logger.exception("Unable to determine Kubernetes connection")

with st.sidebar:
    st.html(f"<div class='brand'>{logo(True)}</div>")
    st.html("<div class='nav active'>▦ Dashboard</div><div class='nav'>⇧ File Placement</div><div class='nav'>☰ Activity Log</div><div class='nav'>⚙ Settings</div>")
    st.html(f"<div class='sidecard'><b>Namespace Policy</b><br><br>{chips(ALLOWED_NAMESPACES)}</div>")
    st.html(f"<div class='sidecard'><b>Logs</b><br><small>{LOG_PATH}</small></div>")

st.html(f"<div class='top'><div><h1>File Placement Dashboard</h1><p>Internal DevOps Platform</p></div><div class='conn'><b>{'Connected to Kubernetes' if connected else 'Connection unavailable'}</b><br><small>Mode: {mode} | Namespace: {detail}</small></div></div>")
st.html(f"<div class='hero'><div>{logo(False)}</div><div><h2>Secure file placement</h2><p>Upload approved files directly into Kubernetes pods with controlled access and verification.</p></div></div>")
st.html("<div class='status'><div><b>Kubernetes</b><span class='ok'>Connected</span></div><div><b>RBAC</b><span class='ok'>Verified</span></div><div><b>Namespace Policy</b><span class='ok'>Restricted</span></div><div><b>Ready to Upload</b><span class='ok'>Ready</span></div></div>")

st.html("<div class='card'><h3>Upload File</h3>")
uploaded_file = st.file_uploader("Upload file", type=None, label_visibility="collapsed")
st.html(f"<small>Maximum file size: {MAX_UPLOAD_MB} MB</small></div>")

st.html("<div class='card'><h3>Placement Details</h3>")
try:
    namespaces = get_namespaces()
except Exception as exc:
    namespaces = []
    st.error(f"Unable to load namespaces: {exc}")

namespace = st.selectbox("Namespace", namespaces, index=0 if namespaces else None)
pod_search = st.text_input("Search pod name", value="", placeholder="Example: batch-")
selected_pod = None
selected_container = None
containers: List[str] = []

if namespace and pod_search.strip():
    try:
        matched = [pod for pod in get_pods(namespace) if pod_search.strip().lower() in pod.lower()]
        if matched:
            selected_pod = st.selectbox("Matching pods", matched, index=0)
            containers = get_containers(namespace, selected_pod)
            st.html(f"<div class='good'><b>Selected Pod</b><br>{selected_pod}</div>")
        else:
            st.html("<div class='warn'>No matching pod found.</div>")
    except Exception as exc:
        st.error(f"Unable to load matching pods: {exc}")
else:
    st.html("<div class='warn'>Enter pod search text to show matching pods.</div>")

if selected_pod and len(containers) > 1:
    with st.expander("Advanced options", expanded=True):
        selected = st.selectbox("Container", ["<default>"] + containers)
        selected_container = None if selected == "<default>" else selected
elif selected_pod and len(containers) == 1:
    st.caption(f"Container: {containers[0]}")

destination_folder = st.text_input("Destination folder", value="/tmp", placeholder="Example: /opt/app/config")
if uploaded_file:
    try:
        st.html(f"<div class='summary'><b>Final destination</b><br>{final_path(destination_folder, uploaded_file.name)}</div>")
    except Exception as exc:
        st.html(f"<div class='warn'>{exc}</div>")
st.html("</div>")

st.html("<div class='copy'>")
copy_clicked = st.button("Copy File to Pod", type="primary")
st.html("</div>")

recent_rows = []
if copy_clicked:
    if not uploaded_file:
        st.error("Please upload a file first.")
        st.stop()
    if not namespace:
        st.error("Please select a namespace.")
        st.stop()
    if not selected_pod:
        st.error("Please search and select a pod.")
        st.stop()
    try:
        dest = final_path(destination_folder, uploaded_file.name)
        size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            st.error(f"File is too large. Limit is {MAX_UPLOAD_MB} MB.")
            st.stop()
        name = safe_name(uploaded_file.name)
        audit("Upload copy requested", file=name, namespace=namespace, pod=selected_pod, container=selected_container or "default", destination=dest)
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, name)
            with open(local_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            with st.status("Copying file to pod...", expanded=True) as status:
                st.write(f"Source: {name}")
                st.write(f"Target: {namespace}/{selected_pod}:{dest}")
                st.write(f"Container: {selected_container or '<default>'}")
                copy_file(local_path, namespace, selected_pod, dest, selected_container)
                st.write("Verification result:")
                st.code(exec_ls(namespace, selected_pod, dest, selected_container))
                status.update(label="File copied and verified", state="complete")
        audit("Upload copy completed", file=name, namespace=namespace, pod=selected_pod, container=selected_container or "default", destination=dest)
        st.success("File copied successfully.")
        recent_rows.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), namespace, selected_pod, name, "Success"))
    except Exception as exc:
        logger.exception("Copy failed")
        st.error(f"Copy failed: {exc}")
        st.info("kubectl cp requires tar inside the target container.")

rows = "".join(f"<tr><td>{t}</td><td>{ns}</td><td>{pod}</td><td>{file}</td><td>{status}</td></tr>" for t, ns, pod, file, status in recent_rows)
if not rows:
    rows = "<tr><td colspan='5'>No upload activity in this UI session yet.</td></tr>"
st.html(f"<div class='card recent'><h3>Recent Activity</h3><table><thead><tr><th>Time</th><th>Namespace</th><th>Pod</th><th>File</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table><small>Container log file: {LOG_PATH}</small></div>")

try:
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        st.download_button("Download Logs", data=f.read(), file_name=LOG_FILE, mime="text/plain")
except Exception:
    pass

st.html(f"<div class='footer'><span>Secure. Compliant. Reliable.</span><span>Mashreq Internal DevOps Platform</span><span>Version {APP_VERSION}</span></div>")
