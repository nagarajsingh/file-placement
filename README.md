# Kubernetes File Placement Dashboard

A Streamlit UI to upload a file and copy it directly into a Kubernetes pod without using Azure DevOps pipeline.

## Features

- Upload file from browser UI
- Select namespace
- Search pod by name text
- Auto-resolve matching pod
- Auto-load container names
- Copy file into pod using `kubectl cp`
- Verify copied file using `kubectl exec ls -l`
- Optional namespace restriction using `ALLOWED_NAMESPACES`

## Important notes

This app runs `kubectl` from the server/container where the UI is hosted. That server must have Kubernetes API connectivity and the correct RBAC permissions.

`kubectl cp` requires `tar` inside the target application container. If the target image does not have `tar`, the copy can fail.

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Your local machine must already have working Kubernetes access:

```bash
kubectl config current-context
kubectl get pods -n default
```

## Docker build

```bash
docker build -t file-placement-dashboard:latest .
docker run --rm -p 8501:8501 \
  -v $HOME/.kube:/root/.kube:ro \
  file-placement-dashboard:latest
```

Open:

```text
http://localhost:8501
```

## Kubernetes deployment

Update the namespace in the manifests if you do not want to deploy in `default`.

```bash
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployment.yaml
```

For ingress:

```bash
kubectl apply -f k8s/ingress.yaml
```

Before applying ingress, update the host:

```yaml
host: file-placement.example.com
```

## RBAC permissions

The app needs:

```yaml
pods: get, list
pods/exec: create
namespaces: get, list
```

`kubectl cp` internally uses pod exec, so `pods/exec create` is required.

## Restrict namespaces

Set this env variable in `k8s/deployment.yaml`:

```yaml
- name: ALLOWED_NAMESPACES
  value: "h2h-dev,h2h-sit,mobile-orchestration-sit"
```

When empty, the app tries to list all namespaces.

## Upload limit

Default upload limit in app logic is 50 MB:

```yaml
- name: MAX_UPLOAD_MB
  value: "50"
```

For NGINX ingress, this is also configured:

```yaml
nginx.ingress.kubernetes.io/proxy-body-size: "50m"
```

## If target container does not have tar

`kubectl cp` may fail with tar-related errors. Use one of these options:

1. Add `tar` to the target container image.
2. Copy to a sidecar/shared volume that has tar.
3. Implement a fallback using base64 over `kubectl exec`.

Example fallback command pattern:

```bash
base64 local-file.txt | kubectl exec -i -n <namespace> <pod> -- sh -c 'base64 -d > /tmp/local-file.txt'
```

## Security recommendation

Do not expose this dashboard publicly without authentication. Prefer internal ingress, VPN, SSO, or network restrictions.
