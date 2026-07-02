import logging
import os
import shutil
import subprocess
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

import streamlit as st


APP_TITLE = "Kubernetes File Placement Dashboard"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
LOG_FILE = os.getenv("LOG_FILE", "file-placement-dashboard.log")
MASHREQ_LOGO_URL = os.getenv("MASHREQ_LOGO_URL", "")
ALLOWED_NAMESPACES = [
    ns.strip()
    for ns in os.getenv("ALLOWED_NAMESPACES", "").split(",")
    if ns.strip()
]

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_PATH = str(Path(LOG_DIR) / LOG_FILE)

logger = logging.getLogger("file-placement-dashboard")
logger.setLevel(logging.INFO)
logger.handlers.clear()
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info(
    "Dashboard startup completed | log_path=%s | allowed_namespaces=%s",
    LOG_PATH,
    ALLOWED_NAMESPACES or "ALL",
)

st.set_page_config(page_title=APP_TITLE, page_icon="📁", layout="wide")


PREMIUM_CSS = """
<style>
:root {
    --mashreq-orange: #f58220;
    --mashreq-deep: #2b124c;
    --mashreq-ink: #171321;
    --mashreq-muted: #667085;
    --mashreq-card: rgba(255, 255, 255, 0.92);
    --mashreq-border: rgba(43, 18, 76, 0.12);
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(245, 130, 32, 0.20), transparent 28%),
        radial-gradient(circle at top right, rgba(43, 18, 76, 0.20), transparent 30%),
        linear-gradient(135deg, #fff8f1 0%, #f7f4fb 45%, #ffffff 100%);
    color: var(--mashreq-ink);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2b124c 0%, #3c1768 52%, #1f1232 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.12);
}

section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

div[data-testid="stSidebarUserContent"] {
    padding-top: 1.5rem;
}

.main .block-container {
    padding-top: 1.25rem;
    max-width: 1200px;
}

.mashreq-hero {
    padding: 2rem;
    border-radius: 28px;
    background: linear-gradient(135deg, #2b124c 0%, #4b1d78 52%, #f58220 140%);
    color: #ffffff;
    box-shadow: 0 24px 60px rgba(43, 18, 76, 0.22);
    margin-bottom: 1.25rem;
    position: relative;
    overflow: hidden;
}

.mashreq-hero::after {
    content: "";
    position: absolute;
    width: 230px;
    height: 230px;
    right: -70px;
    top: -70px;
    background: rgba(245, 130, 32, 0.30);
    border-radius: 50%;
}

.mashreq-logo-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.2rem;
    position: relative;
    z-index: 2;
}

.mashreq-logo-lockup {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0.9rem;
    border: 1px solid rgba(255, 255, 255, 0.22);
    background: rgba(255, 255, 255, 0.12);
    border-radius: 999px;
    backdrop-filter: blur(10px);
}

.mashreq-logo-mark {
    width: 34px;
    height: 34px;
    border-radius: 11px;
    background: linear-gradient(135deg, #f58220 0%, #ffb060 100%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #ffffff !important;
    font-size: 1.1rem;
    font-weight: 950;
    box-shadow: 0 8px 18px rgba(245, 130, 32, 0.28);
}

.mashreq-logo-img {
    max-height: 34px;
    max-width: 150px;
    object-fit: contain;
    display: block;
}

.mashreq-logo-text {
    font-size: 1.15rem;
    font-weight: 950;
    letter-spacing: -0.03em;
    color: #ffffff !important;
    line-height: 1;
}

.mashreq-logo-subtitle {
    font-size: 0.72rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.74) !important;
    margin-top: 0.12rem;
    letter-spacing: 0.02em;
}

.mashreq-secure-badge {
    padding: 0.45rem 0.75rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: rgba(255, 255, 255, 0.82) !important;
    font-size: 0.78rem;
    font-weight: 800;
    position: relative;
    z-index: 2;
}

.mashreq-hero h1 {
    font-size: 2.6rem;
    line-height: 1.1;
    margin: 0 0 0.6rem 0;
    color: #ffffff;
    position: relative;
    z-index: 2;
}

.mashreq-hero p {
    font-size: 1.05rem;
    color: rgba(255, 255, 255, 0.84);
    max-width: 780px;
    margin: 0;
    position: relative;
    z-index: 2;
}

.mashreq-card {
    padding: 1.25rem;
    border-radius: 22px;
    background: var(--mashreq-card);
    border: 1px solid var(--mashreq-border);
    box-shadow: 0 14px 38px rgba(43, 18, 76, 0.08);
    margin-bottom: 1rem;
}

.mashreq-section-title {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--mashreq-deep);
    margin-bottom: 0.25rem;
}

.mashreq-help {
    color: var(--mashreq-muted);
    font-size: 0.92rem;
    margin-bottom: 0.75rem;
}

.namespace-pill {
    display: inline-block;
    padding: 0.35rem 0.75rem;
    margin: 0.15rem 0.2rem 0.15rem 0;
    border-radius: 999px;
    background: rgba(245, 130, 32, 0.12);
    color: #8a3f00;
    border: 1px solid rgba(245, 130, 32, 0.22);
    font-weight: 700;
    font-size: 0.82rem;
}

.sidebar-policy-card {
    padding: 1rem;
    margin-top: 0.75rem;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.16);
    box-shadow: 0 16px 34px rgba(0, 0, 0, 0.14);
}

.sidebar-policy-title {
    font-size: 0.95rem;
    font-weight: 850;
    color: #ffffff !important;
    margin-bottom: 0.25rem;
}

.sidebar-policy-desc {
    font-size: 0.78rem;
    line-height: 1.35;
    color: rgba(255, 255, 255, 0.72) !important;
    margin-bottom: 0.75rem;
}

.sidebar-chip-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.sidebar-namespace-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.62rem;
    border-radius: 999px;
    background: rgba(245, 130, 32, 0.18);
    border: 1px solid rgba(245, 130, 32, 0.42);
    color: #ffffff !important;
    font-size: 0.78rem;
    font-weight: 800;
    white-space: nowrap;
}

.sidebar-namespace-chip::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: #f58220;
    box-shadow: 0 0 0 4px rgba(245, 130, 32, 0.16);
}

.sidebar-open-scope {
    padding: 0.65rem;
    border-radius: 14px;
    background: rgba(245, 130, 32, 0.16);
    border: 1px solid rgba(245, 130, 32, 0.34);
    color: #ffffff !important;
    font-size: 0.82rem;
    font-weight: 750;
}

.log-path-box {
    padding: 0.65rem;
    margin-top: 0.75rem;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.16);
    font-size: 0.74rem;
    word-break: break-all;
}

div.stButton > button:first-child {
    background: linear-gradient(135deg, #f58220 0%, #ff9b3d 100%);
    color: #ffffff;
    border: 0;
    border-radius: 14px;
    padding: 0.75rem 1.2rem;
    font-weight: 800;
    box-shadow: 0 12px 24px rgba(245, 130, 32, 0.26);
}

div.stButton > button:first-child:hover {
    border: 0;
    transform: translateY(-1px);
    box-shadow: 0 16px 30px rgba(245, 130, 32, 0.32);
}

div[data-testid="stFileUploader"] section {
    border-radius: 18px;
    border: 1.5px dashed rgba(245, 130, 32, 0.45);
    background: rgba(255, 255, 255, 0.78);
}

div[data-testid="stStatusWidget"] {
    border-radius: 18px;
}

.footer-note {
    text-align: center;
    color: var(--mashreq-muted);
    font-size: 0.82rem;
    padding: 1rem 0 0.25rem;
}
</style>
"""

st.html(PREMIUM_CSS)


class CommandError(Exception):
    pass


def audit(message: str, **kwargs) -> None:
    details = " | ".join(f"{key}={value}" for key, value in kwargs.items())
    logger.info("%s%s", message, f" | {details}" if details else "")


def run_cmd(cmd: List[str], timeout: int = 60) -> str:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        logger.error("Command failed | command=%s | error=%s", " ".join(cmd), message)
        raise CommandError(message)
    logger.info("Command completed | command=%s", " ".join(cmd))
    return result.stdout.strip()


def kubectl_available() -> bool:
    return shutil.which("kubectl") is not None


def get_namespaces() -> List[str]:
    if ALLOWED_NAMESPACES:
        return ALLOWED_NAMESPACES

    output = run_cmd([
        "kubectl",
        "get",
        "namespaces",
        "--no-headers",
        "-o",
        "custom-columns=:metadata.name",
    ])
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_pods(namespace: str) -> List[str]:
    if ALLOWED_NAMESPACES and namespace not in ALLOWED_NAMESPACES:
        raise CommandError(f"Namespace '{namespace}' is not allowed for file placement.")

    output = run_cmd([
        "kubectl",
        "get",
        "pods",
        "-n",
        namespace,
        "--no-headers",
        "-o",
        "custom-columns=:metadata.name",
    ])
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_containers(namespace: str, pod_name: str) -> List[str]:
    if ALLOWED_NAMESPACES and namespace not in ALLOWED_NAMESPACES:
        raise CommandError(f"Namespace '{namespace}' is not allowed for file placement.")

    output = run_cmd([
        "kubectl",
        "get",
        "pod",
        pod_name,
        "-n",
        namespace,
        "-o",
        "jsonpath={.spec.containers[*].name}",
    ])
    return [name.strip() for name in output.split() if name.strip()]


def safe_uploaded_filename(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")


def copy_file_to_pod(
    local_file: str,
    namespace: str,
    pod_name: str,
    destination_path: str,
    container_name: Optional[str],
) -> str:
    if ALLOWED_NAMESPACES and namespace not in ALLOWED_NAMESPACES:
        raise CommandError(f"Namespace '{namespace}' is not allowed for file placement.")

    cmd = ["kubectl", "cp", local_file, f"{namespace}/{pod_name}:{destination_path}"]
    if container_name:
        cmd.extend(["-c", container_name])
    return run_cmd(cmd, timeout=300)


def verify_file(
    namespace: str,
    pod_name: str,
    destination_path: str,
    container_name: Optional[str],
) -> str:
    cmd = ["kubectl", "exec", "-n", namespace]
    if container_name:
        cmd.extend(["-c", container_name])
    cmd.extend([pod_name, "--", "ls", "-l", destination_path])
    return run_cmd(cmd)


def list_destination_dir(
    namespace: str,
    pod_name: str,
    destination_path: str,
    container_name: Optional[str],
) -> str:
    destination_dir = str(Path(destination_path).parent)
    cmd = ["kubectl", "exec", "-n", namespace]
    if container_name:
        cmd.extend(["-c", container_name])
    cmd.extend([pod_name, "--", "ls", "-l", destination_dir])
    return run_cmd(cmd)


def render_html(html: str) -> None:
    st.html(html)


def mashreq_logo_html() -> str:
    if MASHREQ_LOGO_URL:
        logo = f"<img class='mashreq-logo-img' src='{MASHREQ_LOGO_URL}' alt='Mashreq logo' />"
    else:
        logo = "<span class='mashreq-logo-mark'>M</span>"

    return (
        "<div class='mashreq-logo-lockup'>"
        f"{logo}"
        "<div>"
        "<div class='mashreq-logo-text'>mashreq</div>"
        "<div class='mashreq-logo-subtitle'>Internal DevOps</div>"
        "</div>"
        "</div>"
    )


def namespace_policy_html() -> str:
    if not ALLOWED_NAMESPACES:
        return "<span class='namespace-pill'>All namespaces visible</span>"

    return "".join(
        f"<span class='namespace-pill'>{namespace}</span>"
        for namespace in ALLOWED_NAMESPACES
    )


def sidebar_namespace_policy_html() -> str:
    if not ALLOWED_NAMESPACES:
        return (
            "<div class='sidebar-policy-card'>"
            "<div class='sidebar-policy-title'>Namespace policy</div>"
            "<div class='sidebar-policy-desc'>No namespace restriction is configured.</div>"
            "<div class='sidebar-open-scope'>All namespaces visible if RBAC allows it</div>"
            "</div>"
        )

    chips = "".join(
        f"<span class='sidebar-namespace-chip'>{namespace}</span>"
        for namespace in ALLOWED_NAMESPACES
    )
    return (
        "<div class='sidebar-policy-card'>"
        "<div class='sidebar-policy-title'>Namespace policy</div>"
        "<div class='sidebar-policy-desc'>Uploads are restricted by <b>ALLOWED_NAMESPACES</b>.</div>"
        f"<div class='sidebar-chip-wrap'>{chips}</div>"
        "</div>"
    )


render_html(
    "<div class='mashreq-hero'>"
    "<div class='mashreq-logo-row'>"
    f"{mashreq_logo_html()}"
    "<div class='mashreq-secure-badge'>Secure file placement</div>"
    "</div>"
    "<h1>File Placement Dashboard</h1>"
    "<p>Upload approved files directly into Kubernetes pods with controlled namespace access, pod discovery, container selection, and post-copy verification.</p>"
    "</div>"
)

with st.sidebar:
    st.markdown("### Runtime checks")
    if kubectl_available():
        st.success("kubectl found")
    else:
        st.error("kubectl not found in container/server PATH")

    try:
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
            st.success("Connected to Kubernetes")
            running_namespace = open(
                "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
            ).read().strip()
            st.caption(f"Mode: In-Cluster | Namespace: {running_namespace}")
            audit("Kubernetes connection detected", mode="in-cluster", namespace=running_namespace)
        else:
            current_context = run_cmd(["kubectl", "config", "current-context"])
            st.success("Connected to Kubernetes")
            st.caption(f"Context: {current_context}")
            audit("Kubernetes connection detected", mode="kubeconfig", context=current_context)
    except Exception:
        st.warning("Unable to determine Kubernetes connection.")
        logger.exception("Unable to determine Kubernetes connection")

    st.markdown("---")
    render_html(sidebar_namespace_policy_html())
    render_html(f"<div class='log-path-box'>Logs: <b>{LOG_PATH}</b></div>")

render_html(
    "<div class='mashreq-card'>"
    "<div class='mashreq-section-title'>Allowed namespace scope</div>"
    "<div class='mashreq-help'>Manage this list using the <b>ALLOWED_NAMESPACES</b> environment variable.</div>"
    f"{namespace_policy_html()}"
    "</div>"
)

render_html(
    "<div class='mashreq-card'>"
    "<div class='mashreq-section-title'>Upload file</div>"
    "<div class='mashreq-help'>Choose a file from your machine. The file is temporarily stored only during the copy operation.</div>"
    "</div>"
)

uploaded_file = st.file_uploader("Upload file", type=None, label_visibility="collapsed")

col1, col2 = st.columns(2, gap="large")

with col1:
    render_html(
        "<div class='mashreq-card'>"
        "<div class='mashreq-section-title'>Target pod</div>"
        "<div class='mashreq-help'>Select an allowed namespace and provide unique pod search text.</div>"
        "</div>"
    )

    try:
        namespaces = get_namespaces()
    except Exception as exc:
        namespaces = []
        st.error(f"Unable to load namespaces: {exc}")
        logger.exception("Unable to load namespaces")

    namespace = st.selectbox("Namespace", namespaces, index=0 if namespaces else None)
    pod_search = st.text_input("Pod name contains", value="file-processor")

with col2:
    render_html(
        "<div class='mashreq-card'>"
        "<div class='mashreq-section-title'>Destination</div>"
        "<div class='mashreq-help'>Use an absolute path inside the target container.</div>"
        "</div>"
    )

    destination_path = st.text_input("Destination path inside pod", value="/tmp/sample.txt")
    manual_container = st.text_input("Container name optional", value="")

resolved_pod = None
containers: List[str] = []
selected_container = manual_container.strip() or None

if namespace and pod_search:
    try:
        pods = get_pods(namespace)
        matched_pods = [pod for pod in pods if pod_search in pod]

        if len(matched_pods) == 1:
            resolved_pod = matched_pods[0]
            st.success(f"Resolved pod: {resolved_pod}")
            containers = get_containers(namespace, resolved_pod)
            if containers:
                container_options = ["<default>"] + containers
                selected = st.selectbox("Select container", container_options)
                selected_container = None if selected == "<default>" else selected
        elif len(matched_pods) > 1:
            st.warning("Multiple pods matched. Please make the search text more specific.")
            st.code("\n".join(matched_pods))
        else:
            st.warning("No matching pod found.")
    except Exception as exc:
        st.error(f"Unable to resolve pod/container: {exc}")
        logger.exception(
            "Unable to resolve pod/container | namespace=%s | pod_search=%s",
            namespace,
            pod_search,
        )

copy_clicked = st.button("Copy uploaded file to pod", type="primary")

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
        logger.warning(
            "Blocked oversized upload | file=%s | size_mb=%.2f | limit_mb=%s",
            uploaded_file.name,
            upload_size_mb,
            MAX_UPLOAD_MB,
        )
        st.stop()

    safe_name = safe_uploaded_filename(uploaded_file.name)
    audit(
        "Upload copy requested",
        file=safe_name,
        size_mb=round(upload_size_mb, 3),
        namespace=namespace,
        pod=resolved_pod,
        container=selected_container or "default",
        destination=destination_path,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, safe_name)
        with open(local_path, "wb") as handle:
            handle.write(uploaded_file.getvalue())

        try:
            with st.status("Copying file to pod...", expanded=True) as status:
                st.write(f"Source: {safe_name}")
                st.write(f"Target: {namespace}/{resolved_pod}:{destination_path}")
                st.write(f"Container: {selected_container or '<default>'}")

                copy_output = copy_file_to_pod(
                    local_file=local_path,
                    namespace=namespace,
                    pod_name=resolved_pod,
                    destination_path=destination_path,
                    container_name=selected_container,
                )
                if copy_output:
                    st.code(copy_output)

                verification = verify_file(namespace, resolved_pod, destination_path, selected_container)
                st.write("Verification result:")
                st.code(verification)

                directory_listing = list_destination_dir(namespace, resolved_pod, destination_path, selected_container)
                st.write("Destination directory listing:")
                st.code(directory_listing)

                status.update(label="File copied and verified", state="complete")

            audit(
                "Upload copy completed",
                file=safe_name,
                namespace=namespace,
                pod=resolved_pod,
                container=selected_container or "default",
                destination=destination_path,
            )
            st.success("File copied successfully.")
        except Exception as exc:
            logger.exception(
                "Copy failed | file=%s | namespace=%s | pod=%s | destination=%s",
                safe_name,
                namespace,
                resolved_pod,
                destination_path,
            )
            st.error(f"Copy failed: {exc}")
            st.info("Note: kubectl cp requires tar inside the target container. If tar is missing, use the fallback command described in README.md.")

render_html(
    "<div class='footer-note'>Mashreq Internal DevOps Utility · Controlled Kubernetes File Placement</div>"
)
