import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import streamlit as st


APP_TITLE = "Kubernetes File Placement Dashboard"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_NAMESPACES = [ns.strip() for ns in os.getenv("ALLOWED_NAMESPACES", "").split(",") if ns.strip()]


st.set_page_config(page_title=APP_TITLE, page_icon="📁", layout="wide")


class CommandError(Exception):
    pass


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
        raise CommandError(message)
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


st.title("📁 Kubernetes File Placement Dashboard")
st.caption("Upload a file from the UI and copy it directly into a Kubernetes pod using kubectl.")

with st.sidebar:
    st.header("Runtime checks")
    if kubectl_available():
        st.success("kubectl found")
    else:
        st.error("kubectl not found in container/server PATH")

    try:
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
            st.success("Connected to Kubernetes (In-Cluster)")
            running_namespace = open(
                "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
            ).read().strip()
            st.caption(f"Running in namespace: {running_namespace}")
        else:
            current_context = run_cmd(["kubectl", "config", "current-context"])
            st.success(f"Connected to Kubernetes ({current_context})")
    except Exception:
        st.warning("Unable to determine Kubernetes connection.")

uploaded_file = st.file_uploader("Upload file", type=None)

col1, col2 = st.columns(2)

with col1:
    try:
        namespaces = get_namespaces()
    except Exception as exc:
        namespaces = []
        st.error(f"Unable to load namespaces: {exc}")

    namespace = st.selectbox("Namespace", namespaces, index=0 if namespaces else None)
    pod_search = st.text_input("Pod name contains", value="file-processor")

with col2:
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

copy_clicked = st.button("Copy uploaded file to pod", type="primary")

if copy_clicked:
    if not uploaded_file:
        st.error("Please upload a file first.")
        st.stop()

    if not namespace:
        st.error("Please select a namespace.")
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
        st.stop()

    safe_name = safe_uploaded_filename(uploaded_file.name)

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

            st.success("File copied successfully.")
        except Exception as exc:
            st.error(f"Copy failed: {exc}")
            st.info("Note: kubectl cp requires tar inside the target container. If tar is missing, use the fallback command described in README.md.")
