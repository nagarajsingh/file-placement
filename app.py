import logging
import os
import subprocess
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

import streamlit as st

APP_TITLE = "File Placement"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
LOG_FILE = os.getenv("LOG_FILE", "file-placement-dashboard.log")
LOG_PATH = str(Path(LOG_DIR) / LOG_FILE)
MASHREQ_LOGO_URL = os.getenv(
    "MASHREQ_LOGO_URL",
    "https://www.mashreq.com/-/jssmedia/Images/logos-mobile/Neo-logo-mob-en.ashx?iar=0&hash=2C256BD0300FBC5E02CD7BEA04AC281F",
)
ALLOWED_NAMESPACES = [x.strip() for x in os.getenv("ALLOWED_NAMESPACES", "").split(",") if x.strip()]
DESTINATION_FOLDERS = [x.strip() for x in os.getenv("DESTINATION_FOLDERS", "/tmp").split(",") if x.strip()]

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("file-placement")
logger.setLevel(logging.INFO)
logger.handlers.clear()
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

st.set_page_config(page_title=APP_TITLE, page_icon="📤", layout="wide", initial_sidebar_state="expanded")

st.html(f"""
<style>
:root{{--orange:#ff651f;--orange2:#f58220;--ink:#171717;--muted:#686868;--line:#e7e7e7;}}
*{{box-sizing:border-box}} .stApp{{background:#fff;color:var(--ink)}}
header[data-testid="stHeader"]{{display:none}} .main .block-container{{max-width:none;padding:1.3rem 2rem 2rem}}
section[data-testid="stSidebar"]{{background:#fff;border-right:1px solid #e5e5e5;width:290px!important}}
section[data-testid="stSidebar"]>div{{width:290px!important}} div[data-testid="stSidebarUserContent"]{{padding:1rem .8rem}}
[data-testid="stSidebarCollapseButton"]{{display:none}}
.neo-logo{{padding:1rem .6rem 1.4rem;text-align:center;border-bottom:1px solid #eee}}
.neo-logo img{{max-width:215px;max-height:82px;object-fit:contain}}
.nav-active{{margin:1.1rem 0 .4rem;border-left:5px solid var(--orange);background:linear-gradient(90deg,#fff2ea,#fff);padding:1rem 1.1rem;border-radius:0 12px 12px 0;color:var(--orange);font-weight:800}}
.side-section{{padding:1rem 1.05rem;margin-top:.55rem;border-radius:12px;color:#555}}
.side-section b{{display:block;color:#222;margin-bottom:.45rem}} .chips{{display:flex;flex-wrap:wrap;gap:.35rem}}
.chip{{padding:.3rem .55rem;border-radius:999px;background:#fff2ea;color:#d94d09;font-size:.74rem;font-weight:700}}
.side-log{{font-size:.75rem;color:#777;word-break:break-all}}
.top-tools{{display:flex;justify-content:flex-end;gap:2rem;color:var(--orange);font-weight:700;margin-bottom:1.4rem}}
.page-title h1{{font-size:2rem;margin:0;color:#171717}} .page-title p{{margin:.3rem 0 1.4rem;color:#5f5f5f;font-size:1rem}}
.workspace{{background:#fff;border:1px solid #e8e8e8;border-radius:22px;box-shadow:0 12px 34px rgba(0,0,0,.08);padding:1.6rem;display:grid;grid-template-columns:.9fr 1.1fr;gap:2rem}}
.upload-pane{{border-right:1px solid #ececec;padding-right:2rem}} .pane-title{{font-size:1.05rem;font-weight:800;margin-bottom:.8rem}}
[data-testid="stFileUploader"] section{{min-height:210px;border:1.6px dashed var(--orange)!important;border-radius:14px;background:#fff!important;padding:2.3rem!important}}
[data-testid="stFileUploader"] button{{border:1px solid var(--orange)!important;color:var(--orange)!important;background:#fff!important;border-radius:8px!important}}
.small-note{{text-align:center;color:#777;font-size:.8rem;margin-top:.6rem}}
.field-note{{color:#777;font-size:.78rem;margin-top:.25rem}} .selected-card{{background:#effbf4;border:1px solid #cdeed9;border-radius:10px;padding:.7rem .85rem;color:#166534;margin-top:.55rem}}
.copy-wrap{{text-align:center;margin-top:1.25rem}} .stButton>button{{width:100%;background:linear-gradient(90deg,var(--orange),#ff7d21)!important;color:#fff!important;border:0!important;border-radius:9px!important;padding:.8rem 1rem!important;font-weight:800!important;font-size:1rem!important}}
.status-box{{margin-top:1rem}} .success-card{{background:#effbf4;border:1px solid #ccefd8;border-radius:12px;padding:1rem;color:#166534}}
.footer{{text-align:center;color:#888;font-size:.78rem;padding:1.5rem 0 .3rem}}
.splash{{position:fixed;inset:0;z-index:999999;background:#fff;display:flex;align-items:center;justify-content:center;animation:splashHide 1.15s forwards}}
.splash:before,.splash:after{{content:"";position:absolute;width:48vw;height:260px;opacity:.28;background-image:radial-gradient(circle,var(--orange) 2px,transparent 2.6px);background-size:14px 14px;transform:rotate(12deg);border-radius:50%}}
.splash:before{{left:-8vw;top:20vh}} .splash:after{{right:-8vw;top:18vh;transform:rotate(-12deg)}}
.splash-card{{position:relative;z-index:2;width:min(590px,82vw);min-height:330px;background:#fff;border:1px solid #e5e5e5;border-radius:42px;box-shadow:0 18px 48px rgba(0,0,0,.12);display:flex;flex-direction:column;align-items:center;justify-content:center}}
.splash-card img{{max-width:360px;max-height:125px;object-fit:contain}} .spinner{{width:72px;height:72px;margin-top:1.5rem;border:8px dotted #ffc6a7;border-top-color:var(--orange);border-radius:50%;animation:spin .8s linear infinite}}
.splash-text{{margin-top:1rem;color:#666}} @keyframes spin{{to{{transform:rotate(360deg)}}}} @keyframes splashHide{{0%,82%{{opacity:1;visibility:visible}}100%{{opacity:0;visibility:hidden;pointer-events:none}}}}
@media(max-width:900px){{.workspace{{grid-template-columns:1fr}}.upload-pane{{border-right:0;border-bottom:1px solid #eee;padding-right:0;padding-bottom:1.5rem}}}}
</style>
<div class="splash"><div class="splash-card"><img src="{MASHREQ_LOGO_URL}" alt="Mashreq NEO CORP"><div class="spinner"></div><div class="splash-text">Loading your workspace...</div></div></div>
""")


class CommandError(Exception):
    pass


def run_cmd(cmd: List[str], timeout: int = 60) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        logger.error("Command failed | command=%s | error=%s", " ".join(cmd), message)
        raise CommandError(message)
    return result.stdout.strip()


def get_namespaces() -> List[str]:
    if ALLOWED_NAMESPACES:
        return ALLOWED_NAMESPACES
    output = run_cmd(["kubectl", "get", "namespaces", "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [x.strip() for x in output.splitlines() if x.strip()]


def get_pods(namespace: str) -> List[str]:
    output = run_cmd(["kubectl", "get", "pods", "-n", namespace, "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [x.strip() for x in output.splitlines() if x.strip()]


def get_containers(namespace: str, pod: str) -> List[str]:
    output = run_cmd(["kubectl", "get", "pod", pod, "-n", namespace, "-o", "jsonpath={.spec.containers[*].name}"])
    return [x.strip() for x in output.split() if x.strip()]


def safe_name(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")


def copy_file(local_path: str, namespace: str, pod: str, destination: str, container: Optional[str]) -> None:
    cmd = ["kubectl", "cp", local_path, f"{namespace}/{pod}:{destination}"]
    if container:
        cmd.extend(["-c", container])
    run_cmd(cmd, timeout=300)


def verify_file(namespace: str, pod: str, destination: str, container: Optional[str]) -> str:
    cmd = ["kubectl", "exec", "-n", namespace]
    if container:
        cmd.extend(["-c", container])
    cmd.extend([pod, "--", "ls", "-l", destination])
    return run_cmd(cmd)


with st.sidebar:
    st.html(f'<div class="neo-logo"><img src="{MASHREQ_LOGO_URL}" alt="Mashreq NEO CORP"></div>')
    st.html('<div class="nav-active">☁ &nbsp; File Placement</div>')
    st.html(f'<div class="side-section"><b>Namespace Policy</b><div class="chips">{"".join(f"<span class=\"chip\">{n}</span>" for n in ALLOWED_NAMESPACES) or "<span class=\"chip\">RBAC controlled</span>"}</div></div>')
    st.html(f'<div class="side-section"><b>Application Logs</b><div class="side-log">{LOG_PATH}</div></div>')

st.html('<div class="top-tools"><span>English⌄</span><span>☏ Customer Care</span></div>')
st.html('<div class="page-title"><h1>File Placement</h1><p>Securely upload and place files inside Kubernetes pods</p></div>')
st.html('<div class="workspace"><div class="upload-pane"><div class="pane-title">Upload File</div>')
uploaded_file = st.file_uploader("Upload file", type=None, label_visibility="collapsed")
st.html(f'<div class="small-note">Maximum file size: {MAX_UPLOAD_MB} MB</div></div><div>')

try:
    namespaces = get_namespaces()
except Exception as exc:
    namespaces = []
    st.error(f"Unable to load namespaces: {exc}")

namespace = st.selectbox("Namespace", namespaces, index=None, placeholder="Select Namespace")
selected_pod = None
containers: List[str] = []
selected_container: Optional[str] = None

if namespace:
    try:
        pods = get_pods(namespace)
        selected_pod = st.selectbox("Pod", pods, index=None, placeholder="Type to search and select pod")
        if selected_pod:
            containers = get_containers(namespace, selected_pod)
            st.html(f'<div class="selected-card">Selected pod: <b>{selected_pod}</b></div>')
    except Exception as exc:
        st.error(f"Unable to load pods: {exc}")

if selected_pod and len(containers) > 1:
    selected_container = st.selectbox("Container", containers, index=0)

destination_folder = st.selectbox("Destination Folder", DESTINATION_FOLDERS, index=None, placeholder="Select destination folder inside the pod")
overwrite = st.checkbox("Overwrite if file exists", value=False)
st.html('<div class="copy-wrap">')
copy_clicked = st.button("⇧  Upload and Copy File", type="primary")
st.html('</div></div></div>')

if copy_clicked:
    if not uploaded_file:
        st.error("Please upload a file.")
        st.stop()
    if not namespace or not selected_pod or not destination_folder:
        st.error("Select namespace, pod, and destination folder.")
        st.stop()

    filename = safe_name(uploaded_file.name)
    destination = f"{destination_folder.rstrip('/')}/{filename}"
    size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        st.error(f"File exceeds the {MAX_UPLOAD_MB} MB limit.")
        st.stop()

    if not overwrite:
        check_cmd = ["kubectl", "exec", "-n", namespace]
        if selected_container:
            check_cmd.extend(["-c", selected_container])
        check_cmd.extend([selected_pod, "--", "test", "-e", destination])
        exists = subprocess.run(check_cmd, capture_output=True, check=False).returncode == 0
        if exists:
            st.error("File already exists. Enable overwrite to replace it.")
            st.stop()

    with tempfile.TemporaryDirectory() as temp_dir:
        local_path = os.path.join(temp_dir, filename)
        with open(local_path, "wb") as handle:
            handle.write(uploaded_file.getvalue())
        try:
            with st.status("Uploading and placing file...", expanded=True) as status:
                copy_file(local_path, namespace, selected_pod, destination, selected_container)
                verification = verify_file(namespace, selected_pod, destination, selected_container)
                st.code(verification)
                status.update(label="File placed successfully", state="complete")
            logger.info("Upload success | namespace=%s | pod=%s | file=%s | destination=%s", namespace, selected_pod, filename, destination)
            st.html(f'<div class="status-box"><div class="success-card"><b>Upload completed</b><br>{namespace} / {selected_pod}<br>{destination}</div></div>')
        except Exception as exc:
            logger.exception("Upload failed")
            st.error(f"Upload failed: {exc}")

st.html('<div class="footer">Mashreq NEO CORP · Internal DevOps File Placement</div>')
