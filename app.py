import logging
import os
import subprocess
import tempfile
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

import streamlit as st

APP_TITLE = "File Placement"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
LOG_FILE = os.getenv("LOG_FILE", "file-placement-dashboard.log")
MASHREQ_LOGO_URL = os.getenv("MASHREQ_LOGO_URL", "")
ALLOWED_NAMESPACES = [x.strip() for x in os.getenv("ALLOWED_NAMESPACES", "").split(",") if x.strip()]
DESTINATION_FOLDERS = [x.strip() for x in os.getenv("DESTINATION_FOLDERS", "/tmp").split(",") if x.strip()]

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_PATH = str(Path(LOG_DIR) / LOG_FILE)
logger = logging.getLogger("file-placement")
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

CSS = """
<style>
:root{--orange:#ff661f;--blue:#0b4a8b;--ink:#26222b;--muted:#6d696f;--line:#e7e4e2;}
.stApp{background:#fff;color:var(--ink)}
.main .block-container{max-width:1280px;padding:1.1rem 1.7rem 2rem}
header[data-testid="stHeader"]{background:transparent}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e8e5e3}
section[data-testid="stSidebar"] *{color:#4a4548!important}
.brand{padding:1.2rem .8rem;text-align:center;border-bottom:1px solid #eee}.brand img{max-width:210px;max-height:92px;object-fit:contain}.brand-fallback{font-size:1.5rem;font-weight:900;color:var(--orange)!important}.neo{font-size:1rem;color:var(--blue)!important;font-weight:800}
.menu{padding:.9rem 1rem;border-radius:8px;margin:.35rem 0;font-weight:700}.menu.active{background:#fff3ed;border-left:5px solid var(--orange);color:var(--orange)!important}.side-note{position:relative;margin-top:18rem;padding:1rem;border-radius:12px;background:#fafafa;border:1px solid #eee;font-size:.84rem}
.topline{display:flex;justify-content:flex-end;gap:2rem;color:var(--orange);font-weight:700;margin-bottom:.5rem}.title h1{margin:0;font-size:2rem}.title p{margin:.25rem 0 1.2rem;color:var(--muted)}
.panel{background:#fff;border:1px solid var(--line);border-radius:18px;padding:1.4rem;box-shadow:0 10px 28px rgba(49,36,28,.08)}
.grid{display:grid;grid-template-columns:1fr 1.2fr;gap:2rem;align-items:start}
.upload-title{font-size:1.05rem;font-weight:800;margin-bottom:.7rem}.upload-wrap div[data-testid="stFileUploader"] section{border:1.6px dashed var(--orange)!important;border-radius:12px;background:#fff!important;padding:2rem!important}.small{font-size:.82rem;color:var(--muted);text-align:center;margin-top:.4rem}
.form-block label{font-weight:700!important}.summary{background:#fff7f2;border:1px solid #ffd2bc;border-radius:10px;padding:.75rem;margin-top:.65rem;color:#8c3b13}.selected{background:#edf9f0;border:1px solid #cfead6;border-radius:10px;padding:.75rem;margin-top:.65rem;color:#205c31}
.stButton>button{background:var(--orange)!important;color:#fff!important;border:0!important;border-radius:8px!important;font-weight:800!important;padding:.75rem 2rem!important}.copy{text-align:center;margin-top:1rem}
.splash-bg{position:fixed;inset:0;z-index:999999;background:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden}.splash-bg:before,.splash-bg:after{content:"";position:absolute;width:620px;height:230px;border-radius:50%;border:12px dotted rgba(255,102,31,.18);transform:rotate(18deg)}.splash-bg:before{left:-120px;top:150px}.splash-bg:after{right:-130px;top:120px}.splash-card{position:relative;z-index:2;width:min(650px,80vw);padding:4rem 3rem;text-align:center;border-radius:28px;background:#fff;border:1px solid #e5e1df;box-shadow:0 18px 45px rgba(0,0,0,.12)}.splash-card img{max-width:360px;max-height:130px;object-fit:contain}.splash-logo{font-size:2.6rem;font-weight:900;color:var(--orange)}.splash-sub{font-size:1.5rem;color:var(--blue);font-weight:800}.spinner{width:58px;height:58px;margin:2rem auto 1rem;border-radius:50%;border:8px solid #ffe4d7;border-top-color:var(--orange);animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:900px){.grid{grid-template-columns:1fr}.side-note{margin-top:2rem}}
</style>
"""
st.html(CSS)

class CommandError(Exception):
    pass


def run_cmd(cmd: List[str], timeout: int = 60) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "Command failed"
        logger.error("Command failed | command=%s | error=%s", " ".join(cmd), msg)
        raise CommandError(msg)
    return result.stdout.strip()


def get_namespaces() -> List[str]:
    if ALLOWED_NAMESPACES:
        return ALLOWED_NAMESPACES
    out = run_cmd(["kubectl", "get", "namespaces", "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [x.strip() for x in out.splitlines() if x.strip()]


def get_pods(namespace: str) -> List[str]:
    out = run_cmd(["kubectl", "get", "pods", "-n", namespace, "--no-headers", "-o", "custom-columns=:metadata.name"])
    return [x.strip() for x in out.splitlines() if x.strip()]


def get_containers(namespace: str, pod: str) -> List[str]:
    out = run_cmd(["kubectl", "get", "pod", pod, "-n", namespace, "-o", "jsonpath={.spec.containers[*].name}"])
    return [x.strip() for x in out.split() if x.strip()]


def safe_name(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")


def destination_path(folder: str, filename: str) -> str:
    return f"{folder.rstrip('/')}/{safe_name(filename)}"


def copy_file(local_file: str, namespace: str, pod: str, dest: str, container: Optional[str]) -> None:
    cmd = ["kubectl", "cp", local_file, f"{namespace}/{pod}:{dest}"]
    if container:
        cmd.extend(["-c", container])
    run_cmd(cmd, timeout=300)


def verify(namespace: str, pod: str, dest: str, container: Optional[str]) -> str:
    cmd = ["kubectl", "exec", "-n", namespace]
    if container:
        cmd.extend(["-c", container])
    cmd.extend([pod, "--", "ls", "-l", dest])
    return run_cmd(cmd)


def logo_html() -> str:
    if MASHREQ_LOGO_URL:
        return f"<img src='{MASHREQ_LOGO_URL}' alt='Mashreq NEO CORP logo'>"
    return "<div class='splash-logo'>mashreq المشـرق</div><div class='splash-sub'>NEO CORP</div>"


if "splash_seen" not in st.session_state:
    splash = st.empty()
    splash.html(
        "<div class='splash-bg'><div class='splash-card'>"
        f"{logo_html()}"
        "<div class='spinner'></div>"
        "<div style='color:#6d696f'>Loading your workspace...</div>"
        "</div></div>"
    )
    time.sleep(1)
    splash.empty()
    st.session_state.splash_seen = True

with st.sidebar:
    st.html(f"<div class='brand'>{logo_html()}</div>")
    st.html("<div class='menu active'>☁ File Placement</div>")
    st.html("<div class='side-note'><b>Namespace Policy</b><br><br>Uploads are limited to approved namespaces.<br><br><small>Logs: " + LOG_PATH + "</small></div>")

st.html("<div class='topline'><span>English⌄</span><span>Customer Care</span></div>")
st.html("<div class='title'><h1>File Placement</h1><p>Securely upload and place files inside Kubernetes pods</p></div>")
st.html("<div class='panel'><div class='grid'>")

left, right = st.columns([1, 1.2], gap="large")
with left:
    st.html("<div class='upload-title'>Upload File</div>")
    st.html("<div class='upload-wrap'>")
    uploaded_file = st.file_uploader("Upload file", label_visibility="collapsed")
    st.html(f"<div class='small'>Maximum file size: {MAX_UPLOAD_MB} MB</div></div>")

with right:
    st.html("<div class='form-block'>")
    try:
        namespaces = get_namespaces()
    except Exception as exc:
        namespaces = []
        st.error(f"Unable to load namespaces: {exc}")

    namespace = st.selectbox("Namespace", namespaces, index=None, placeholder="Select Namespace")
    selected_pod = None
    selected_container = None
    containers: List[str] = []

    if namespace:
        try:
            pods = get_pods(namespace)
            selected_pod = st.selectbox(
                "Pod",
                pods,
                index=None,
                placeholder="Type to search and select pod",
            )
            if selected_pod:
                containers = get_containers(namespace, selected_pod)
                st.html(f"<div class='selected'><b>Selected Pod</b><br>{selected_pod}</div>")
        except Exception as exc:
            st.error(f"Unable to load pods: {exc}")
    else:
        st.selectbox("Pod", [], index=None, placeholder="Select namespace first", disabled=True)

    folder = st.selectbox("Destination Folder", DESTINATION_FOLDERS, index=None, placeholder="Select destination folder inside the pod")

    if selected_pod and len(containers) > 1:
        with st.expander("Advanced options"):
            choice = st.selectbox("Container", ["<default>"] + containers)
            selected_container = None if choice == "<default>" else choice

    if uploaded_file and folder:
        st.html(f"<div class='summary'><b>Final destination</b><br>{destination_path(folder, uploaded_file.name)}</div>")

    st.html("</div>")

st.html("</div>")
st.html("<div class='copy'>")
copy_clicked = st.button("Upload and Copy File", type="primary")
st.html("</div></div>")

if copy_clicked:
    if not uploaded_file:
        st.error("Please upload a file.")
        st.stop()
    if not namespace:
        st.error("Please select a namespace.")
        st.stop()
    if not selected_pod:
        st.error("Please select a pod.")
        st.stop()
    if not folder:
        st.error("Please select a destination folder.")
        st.stop()

    size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        st.error(f"File is too large. Maximum allowed size is {MAX_UPLOAD_MB} MB.")
        st.stop()

    name = safe_name(uploaded_file.name)
    dest = destination_path(folder, name)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, name)
        with open(local_path, "wb") as handle:
            handle.write(uploaded_file.getvalue())
        try:
            with st.status("Uploading and copying file...", expanded=True) as status:
                st.write(f"Namespace: {namespace}")
                st.write(f"Pod: {selected_pod}")
                st.write(f"Destination: {dest}")
                copy_file(local_path, namespace, selected_pod, dest, selected_container)
                st.code(verify(namespace, selected_pod, dest, selected_container))
                status.update(label="File uploaded and verified", state="complete")
            logger.info("Upload completed | namespace=%s | pod=%s | file=%s | destination=%s", namespace, selected_pod, name, dest)
            st.success("File uploaded successfully.")
        except Exception as exc:
            logger.exception("Upload failed")
            st.error(f"Upload failed: {exc}")
