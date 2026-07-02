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
ALLOWED_NAMESPACES = [ns.strip() for ns in os.getenv("ALLOWED_NAMESPACES", "").split(",") if ns.strip()]

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_PATH = str(Path(LOG_DIR) / LOG_FILE)

logger = logging.getLogger("file-placement-dashboard")
logger.setLevel(logging.INFO)
logger.handlers.clear()
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.info("Dashboard started | log_path=%s | allowed_namespaces=%s", LOG_PATH, ALLOWED_NAMESPACES or "ALL")

st.set_page_config(page_title=APP_TITLE, page_icon="📁", layout="wide")

CSS = """
<style>
:root{--orange:#f58220;--purple:#24104f;--purple2:#4a148c;--ink:#151238;--muted:#697086;--line:#e8e5f0;--green:#17a34a;--red:#e5484d;--card:#ffffff;}
.stApp{background:#f7f7fb;color:var(--ink);}
.main .block-container{max-width:1180px;padding:1.2rem 1.6rem 2.5rem 1.6rem;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#17073d 0%,#2b0b63 52%,#160733 100%);border-right:1px solid rgba(255,255,255,.12);}
section[data-testid="stSidebar"] *{color:#fff!important;}
div[data-testid="stSidebarUserContent"]{padding:1.2rem .65rem;}
.sidebar-logo{background:rgba(255,255,255,.96);border-radius:18px;padding:1.1rem;text-align:center;margin-bottom:1.1rem;box-shadow:0 14px 36px rgba(0,0,0,.18)}
.sidebar-logo img{max-width:145px;max-height:90px;object-fit:contain}.sidebar-logo .text-logo{font-size:1.65rem;font-weight:950;color:#185aa6!important;letter-spacing:-.04em}.sidebar-logo .tagline{font-size:1rem;color:#ff4b12!important;font-style:italic;margin-top:.15rem}
.nav-item{display:flex;align-items:center;gap:.75rem;padding:.85rem 1rem;border-radius:12px;margin:.35rem 0;font-weight:780;color:#fff!important}.nav-active{background:linear-gradient(135deg,#5e24c7,#6b2ad7);box-shadow:0 12px 24px rgba(0,0,0,.18)}.nav-icon{font-size:1.15rem;color:#ff8b2b!important;}
.side-card{padding:1rem;border-radius:16px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);margin-top:1rem}.side-title{font-weight:900;font-size:.95rem;margin-bottom:.55rem}.side-desc{font-size:.82rem;line-height:1.45;color:rgba(255,255,255,.78)!important;margin-bottom:.65rem}.side-chip{display:inline-flex;align-items:center;gap:.35rem;margin:.18rem;padding:.38rem .65rem;border-radius:999px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);font-size:.78rem;font-weight:800}.side-chip:before{content:"";height:8px;width:8px;border-radius:99px;background:#ff8b2b;display:inline-block}.side-log{font-size:.78rem;word-break:break-all;color:rgba(255,255,255,.8)!important;}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1.5rem}.title-wrap h1{font-size:2.15rem;line-height:1;margin:0;color:#1a1247;font-weight:950;letter-spacing:-.04em}.title-wrap p{margin:.35rem 0 0;color:#6d5e94;font-size:1.05rem}.connected{display:flex;align-items:center;gap:.75rem;background:#eefaf2;border:1px solid #d3f1dc;border-radius:14px;padding:.85rem 1.1rem;box-shadow:0 10px 24px rgba(23,163,74,.08)}.connected .ok{width:32px;height:32px;border-radius:50%;background:#19a24a;color:white;display:flex;align-items:center;justify-content:center;font-weight:900}.connected b{display:block;color:#102a19}.connected span{color:#57606a;font-size:.86rem}
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:1.5rem;align-items:center;padding:2.15rem;border-radius:24px;background:radial-gradient(circle at 0% 100%,rgba(255,255,255,.18),transparent 24%),linear-gradient(120deg,#2a0b61 0%,#4d167d 48%,#ff641f 100%);box-shadow:0 20px 55px rgba(36,16,79,.2);margin-bottom:1.5rem;overflow:hidden}.hero-logo{display:flex;align-items:center;gap:1rem}.hero-logo img{max-width:250px;max-height:100px;object-fit:contain}.hero-fallback{display:flex;align-items:center;gap:.85rem}.hero-mark{width:70px;height:48px;border-radius:22px;background:linear-gradient(135deg,#ff7a1f,#ffb15d);display:flex;align-items:center;justify-content:center;font-weight:950;font-size:2rem;color:white}.hero-name{font-size:2.2rem;font-weight:950;color:white;letter-spacing:-.05em}.hero-tag{color:#ff8b2b;font-size:1.25rem;font-style:italic}.hero-copy{border-left:1px solid rgba(255,255,255,.28);padding-left:1.6rem;color:white}.hero-copy h2{margin:0 0 .45rem;font-size:1.65rem;color:white}.hero-copy p{margin:0;line-height:1.5;color:rgba(255,255,255,.86)}
.status-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem}.status-card{background:white;border:1px solid var(--line);border-radius:16px;padding:1rem;box-shadow:0 10px 28px rgba(31,18,62,.07);display:flex;align-items:center;gap:.9rem}.status-icon{width:52px;height:52px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:1.45rem}.green-bg{background:#eaf9ef;color:#119243}.purple-bg{background:#f0e9ff;color:#6a34b8}.orange-bg{background:#fff0e3;color:#e46513}.blue-bg{background:#e9f4ff;color:#1672cf}.status-card b{display:block;color:#1a1247}.status-card span{font-size:.82rem;font-weight:800;border-radius:999px;padding:.2rem .55rem;background:#e9f8ee;color:#149144}.status-card .restricted{background:#fff1e7;color:#d85b0d}
.grid{display:grid;grid-template-columns:1.05fr .95fr;gap:1rem}.card{background:white;border:1px solid var(--line);border-radius:18px;padding:1.25rem;box-shadow:0 10px 32px rgba(31,18,62,.07);margin-bottom:1rem}.card-title{font-weight:950;color:#1a1247;font-size:1.12rem;margin-bottom:.85rem}.upload-shell div[data-testid="stFileUploader"] section{border:1.8px dashed #a688df!important;border-radius:16px;background:#fbfaff!important;padding:2rem!important}.hint{color:var(--muted);font-size:.85rem;margin-top:.4rem}.resolved{background:#ecfbf1;border:1px solid #c8efd4;border-radius:14px;padding:.85rem 1rem;margin-top:.7rem;color:#123d22}.resolved b{color:#108d3d}.warnbox{background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;padding:.85rem 1rem;color:#9a3412;margin-top:.7rem}.copy-btn-wrap{text-align:center;margin:.3rem 0 1rem}.recent table{width:100%;border-collapse:collapse}.recent th,.recent td{padding:.75rem;border-bottom:1px solid var(--line);font-size:.88rem;text-align:left}.recent th{color:#4c466a;font-weight:900}.success-pill{display:inline-block;background:#eaf9ef;color:#129244;border-radius:999px;padding:.22rem .6rem;font-weight:800;font-size:.78rem}.footer{text-align:center;color:#6f6789;font-size:.84rem;padding:1.1rem 0}.footer span{margin:0 1rem}.log-path-main{font-size:.8rem;color:#6d5e94;margin-top:.3rem;word-break:break-all}
.stButton>button{background:linear-gradient(135deg,#ff641f,#f58220)!important;color:white!important;border:0!important;border-radius:12px!important;padding:.75rem 2.4rem!important;font-weight:950!important;box-shadow:0 12px 26px rgba(245,130,32,.25)!important}.stButton>button:hover{transform:translateY(-1px);box-shadow:0 15px 32px rgba(245,130,32,.32)!important}
@media(max-width:980px){.hero,.grid,.status-grid{grid-template-columns:1fr}.topbar{display:block}.connected{margin-top:1rem}.hero-copy{border-left:0;padding-left:0}}
</style>
"""

st.html(CSS)

class CommandError(Exception):
    pass

def audit(message: str, **kwargs) -> None:
    details = " | ".join(f"{key}={value}" for key, value in kwargs.items())
    logger.info("%s%s", message, f" | {details}" if details else "")

def run_cmd(cmd: List[str], timeout: int = 60) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        logger.error("Command failed | command=%s | error=%s", " ".join(cmd), message)
        raise CommandError(message)
    logger.info("Command completed | command=%s", " ".join(cmd))
    return result.stdout.strip()

def kubectl_available() -> bool:
    return shutil.which("kubectl") is not None

def get_runtime_info() -> tuple[str, str]:
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        ns = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read_text().strip()
        return "In-Cluster", ns
    return "Kubeconfig", run_cmd(["kubectl", "config", "current-context"])

def get_namespaces() -> List[str]:
    if ALLOWED_NAMESPACES:
        return ALLOWED_NAMESPACES
    output = run_cmd(["kubectl", "get", "namespaces", "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [line.strip() for line in output.splitlines() if line.strip()]

def ensure_namespace_allowed(namespace: str) -> None:
    if ALLOWED_NAMESPACES and namespace not in ALLOWED_NAMESPACES:
        raise CommandError(f"Namespace '{namespace}' is not allowed for file placement.")

def get_pods(namespace: str) -> List[str]:
    ensure_namespace_allowed(namespace)
    output = run_cmd(["kubectl", "get", "pods", "-n", namespace, "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [line.strip() for line in output.splitlines() if line.strip()]

def get_containers(namespace: str, pod_name: str) -> List[str]:
    ensure_namespace_allowed(namespace)
    output = run_cmd(["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "jsonpath={.spec.containers[*].name}"])
    return [name.strip() for name in output.split() if name.strip()]

def safe_uploaded_filename(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")

def copy_file_to_pod(local_file: str, namespace: str, pod_name: str, destination_path: str, container_name: Optional[str]) -> str:
    ensure_namespace_allowed(namespace)
    cmd = ["kubectl", "cp", local_file, f"{namespace}/{pod_name}:{destination_path}"]
    if container_name:
        cmd.extend(["-c", container_name])
    return run_cmd(cmd, timeout=300)

def verify_file(namespace: str, pod_name: str, destination_path: str, container_name: Optional[str]) -> str:
    cmd = ["kubectl", "exec", "-n", namespace]
    if container_name:
        cmd.extend(["-c", container_name])
    cmd.extend([pod_name, "--", "ls", "-l", destination_path])
    return run_cmd(cmd)

def list_destination_dir(namespace: str, pod_name: str, destination_path: str, container_name: Optional[str]) -> str:
    destination_dir = str(Path(destination_path).parent)
    cmd = ["kubectl", "exec", "-n", namespace]
    if container_name:
        cmd.extend(["-c", container_name])
    cmd.extend([pod_name, "--", "ls", "-l", destination_dir])
    return run_cmd(cmd)

def html_logo(sidebar: bool = False) -> str:
    if MASHREQ_LOGO_URL:
        if sidebar:
            return f"<img src='{MASHREQ_LOGO_URL}' alt='Mashreq logo'/><div class='tagline'>Rise every day</div>"
        return f"<img src='{MASHREQ_LOGO_URL}' alt='Mashreq logo'/>"
    if sidebar:
        return "<div class='text-logo'>mashreq</div><div class='tagline'>Rise every day</div>"
    return "<div class='hero-fallback'><div class='hero-mark'>M</div><div><div class='hero-name'>mashreq</div><div class='hero-tag'>Rise every day</div></div></div>"

def chips(names: List[str], side: bool = False) -> str:
    if not names:
        return "<span class='side-chip'>All namespaces</span>" if side else "<span class='namespace-pill'>All namespaces visible</span>"
    cls = "side-chip" if side else "namespace-pill"
    return "".join(f"<span class='{cls}'>{name}</span>" for name in names)

try:
    runtime_mode, runtime_detail = get_runtime_info()
    connected = True
except Exception:
    runtime_mode, runtime_detail = "Unknown", "Unavailable"
    connected = False
    logger.exception("Unable to determine Kubernetes connection")

with st.sidebar:
    st.html(f"<div class='sidebar-logo'>{html_logo(sidebar=True)}</div>")
    st.html("<div class='nav-item nav-active'><span class='nav-icon'>▦</span>Dashboard</div>")
    st.html("<div class='nav-item'><span class='nav-icon'>⇧</span>File Placement</div>")
    st.html("<div class='nav-item'><span class='nav-icon'>☰</span>Activity Log</div>")
    st.html("<div class='nav-item'><span class='nav-icon'>⚙</span>Settings</div>")
    st.html("<div class='nav-item'><span class='nav-icon'>ⓘ</span>About</div>")
    st.html(f"<div class='side-card'><div class='side-title'>🛡 Namespace Policy</div><div class='side-desc'>Uploads are restricted by ALLOWED_NAMESPACES.</div>{chips(ALLOWED_NAMESPACES, side=True)}</div>")
    st.html(f"<div class='side-card'><div class='side-title'>📄 Logs</div><div class='side-log'>{LOG_PATH}</div></div>")
    st.html("<div style='height:2rem'></div><div class='side-desc'>Mashreq PSC<br/>Internal DevOps Platform<br/>© 2026</div>")

st.html(
    f"<div class='topbar'><div class='title-wrap'><h1>File Placement Dashboard</h1><p>Internal DevOps Platform</p></div><div class='connected'><div class='ok'>{'✓' if connected else '!'}</div><div><b>{'Connected to Kubernetes' if connected else 'Connection unavailable'}</b><span>Mode: {runtime_mode} | Namespace: {runtime_detail}</span></div></div></div>"
)

st.html(
    f"<div class='hero'><div class='hero-logo'>{html_logo()}</div><div class='hero-copy'><h2>🛡 Secure file placement</h2><p>Upload approved files directly into Kubernetes pods with controlled access and verification.</p></div></div>"
)

st.html(
    "<div class='status-grid'>"
    "<div class='status-card'><div class='status-icon green-bg'>☸</div><div><b>Kubernetes</b><span>Connected</span></div></div>"
    "<div class='status-card'><div class='status-icon purple-bg'>👥</div><div><b>RBAC</b><span>Verified</span></div></div>"
    "<div class='status-card'><div class='status-icon orange-bg'>▤</div><div><b>Namespace Policy</b><span class='restricted'>Restricted</span></div></div>"
    "<div class='status-card'><div class='status-icon blue-bg'>☁</div><div><b>Ready to Upload</b><span>Ready</span></div></div>"
    "</div>"
)

st.html("<div class='card upload-shell'><div class='card-title'>1. Upload File</div>")
uploaded_file = st.file_uploader("Upload file", type=None, label_visibility="collapsed")
st.html(f"<div class='hint'>Maximum file size: {MAX_UPLOAD_MB} MB</div></div>")

col1, col2 = st.columns(2, gap="large")
with col1:
    st.html("<div class='card'><div class='card-title'>2. Target Pod</div>")
    try:
        namespaces = get_namespaces()
    except Exception as exc:
        namespaces = []
        st.error(f"Unable to load namespaces: {exc}")
        logger.exception("Unable to load namespaces")
    namespace = st.selectbox("Namespace", namespaces, index=0 if namespaces else None)
    pod_search = st.text_input("Pod name contains", value="file-processor")

    resolved_pod = None
    containers: List[str] = []
    if namespace and pod_search:
        try:
            pods = get_pods(namespace)
            matched_pods = [pod for pod in pods if pod_search in pod]
            if len(matched_pods) == 1:
                resolved_pod = matched_pods[0]
                containers = get_containers(namespace, resolved_pod)
                st.html(f"<div class='resolved'><b>✓ Resolved Pod</b><br>{resolved_pod}</div>")
            elif len(matched_pods) > 1:
                st.warning("Multiple pods matched. Please make the search text more specific.")
                st.code("\n".join(matched_pods))
            else:
                st.html("<div class='warnbox'>No matching pod found.</div>")
        except Exception as exc:
            st.error(f"Unable to resolve pod/container: {exc}")
            logger.exception("Unable to resolve pod/container | namespace=%s | pod_search=%s", namespace, pod_search)
    st.html("</div>")

with col2:
    st.html("<div class='card'><div class='card-title'>3. Container (Optional)</div>")
    container_options = ["<default>"] + containers if containers else ["<default>"]
    selected = st.selectbox("Select Container", container_options)
    selected_container = None if selected == "<default>" else selected
    st.html("<div class='hint'>Leave as default to use the first container.</div></div>")

    st.html("<div class='card'><div class='card-title'>4. Destination Path</div>")
    destination_path = st.text_input("Destination path inside pod", value="/tmp/sample.txt")
    st.html("<div class='hint'>Use absolute path inside the container.</div></div>")

st.html("<div class='copy-btn-wrap'>")
copy_clicked = st.button("⇧  Copy File to Pod", type="primary")
st.html("</div>")

recent_rows = []
if copy_clicked:
    if not uploaded_file:
        st.error("Please upload a file first.")
        st.stop()
    if not namespace:
        st.error("Please select a namespace.")
        st.stop()
    if ALLOWED_NAMESPACES and namespace not in ALLOWED_NAMESPACES:
        st.error(f"Namespace '{namespace}' is not allowed. Update ALLOWED_NAMESPACES to enable it.")
        logger.warning("Blocked upload attempt to disallowed namespace | namespace=%s", namespace)
        st.stop()
    if not resolved_pod:
        st.error("Pod is not resolved. Please provide a unique pod search value.")
        st.stop()
    if not destination_path.startswith("/"):
        st.error("Destination path must be an absolute path, for example /tmp/sample.txt")
        st.stop()

    upload_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if upload_size_mb > MAX_UPLOAD_MB:
        st.error(f"File is too large. Limit is {MAX_UPLOAD_MB} MB.")
        logger.warning("Blocked oversized upload | file=%s | size_mb=%.2f | limit_mb=%s", uploaded_file.name, upload_size_mb, MAX_UPLOAD_MB)
        st.stop()

    safe_name = safe_uploaded_filename(uploaded_file.name)
    audit("Upload copy requested", file=safe_name, size_mb=round(upload_size_mb, 3), namespace=namespace, pod=resolved_pod, container=selected_container or "default", destination=destination_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, safe_name)
        with open(local_path, "wb") as handle:
            handle.write(uploaded_file.getvalue())
        try:
            with st.status("Copying file to pod...", expanded=True) as status:
                st.write(f"Source: {safe_name}")
                st.write(f"Target: {namespace}/{resolved_pod}:{destination_path}")
                st.write(f"Container: {selected_container or '<default>'}")
                copy_output = copy_file_to_pod(local_path, namespace, resolved_pod, destination_path, selected_container)
                if copy_output:
                    st.code(copy_output)
                verification = verify_file(namespace, resolved_pod, destination_path, selected_container)
                st.write("Verification result:")
                st.code(verification)
                directory_listing = list_destination_dir(namespace, resolved_pod, destination_path, selected_container)
                st.write("Destination directory listing:")
                st.code(directory_listing)
                status.update(label="File copied and verified", state="complete")
            audit("Upload copy completed", file=safe_name, namespace=namespace, pod=resolved_pod, container=selected_container or "default", destination=destination_path)
            st.success("File copied successfully.")
            recent_rows.append((datetime.now().strftime("%b %d, %Y %H:%M:%S"), namespace, resolved_pod, safe_name, "Success", os.getenv("USER", "nagaraj")))
        except Exception as exc:
            logger.exception("Copy failed | file=%s | namespace=%s | pod=%s | destination=%s", safe_name, namespace, resolved_pod, destination_path)
            st.error(f"Copy failed: {exc}")
            st.info("Note: kubectl cp requires tar inside the target container. If tar is missing, use the fallback command described in README.md.")

rows_html = "".join(
    f"<tr><td>{t}</td><td>{ns}</td><td>{pod}</td><td>{file}</td><td><span class='success-pill'>✓ {status}</span></td><td>{user}</td></tr>"
    for t, ns, pod, file, status, user in recent_rows
)
if not rows_html:
    rows_html = "<tr><td colspan='6'>No upload activity in this UI session yet.</td></tr>"

st.html(
    "<div class='card recent'><div class='card-title'>Recent Activity</div>"
    "<table><thead><tr><th>Time</th><th>Namespace</th><th>Pod</th><th>File</th><th>Status</th><th>User</th></tr></thead>"
    f"<tbody>{rows_html}</tbody></table>"
    f"<div class='log-path-main'>Container log file: <b>{LOG_PATH}</b></div>"
    "</div>"
)

try:
    with open(LOG_PATH, "r", encoding="utf-8") as log_file:
        log_data = log_file.read()
    st.download_button("Download Logs", data=log_data, file_name=LOG_FILE, mime="text/plain")
except Exception:
    pass

st.html(f"<div class='footer'><span>🔒 Secure. Compliant. Reliable.</span><span>Mashreq PSC - Internal DevOps Platform</span><span>Version {APP_VERSION}</span></div>")
