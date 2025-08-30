# k8s-logs — FastAPI app for viewing Kubernetes logs

Quick reference for running, building, deploying and troubleshooting the project.

## What this repo contains
- `main.py` — FastAPI app exposing endpoints: `/` (HTML list), `/logs/{namespace}/{pod}` (pod logs), `/health` (readiness), `/heartbeat` (liveness).
- `Dockerfile` — minimal image to run the FastAPI app with uvicorn.
- `deploy.yml` — Kubernetes Deployment + Service (used in Minikube).
- `build_and_push_to_minikube.sh` — convenience script to build image, load into Minikube, apply manifests and show service URL.

## Prerequisites
- Docker
- Minikube (or a Kubernetes cluster)
- kubectl configured to talk to the cluster / minikube

## Run locally (development)
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Run with Uvicorn (auto-reload helpful during development):
```bash
uvicorn main:app --reload --log-level info
```
3. Open http://127.0.0.1:8000

## Build and run in Minikube
Two common flows:

A) Build into Minikube's docker daemon (recommended):
```bash
eval "$(minikube docker-env)"
docker build -t ghcr.io/stoyanstatanasov/k8s-logs:$(cat VERSION) .
kubectl apply -f deploy.yml
kubectl rollout restart deployment k8s-logs
kubectl rollout status deployment k8s-logs
minikube service k8s-logs --url
```

B) Build locally and load into minikube (script provided):
```bash
./build_and_push_to_minikube.sh
```

Notes:
- If Kubernetes reports ImagePullBackOff, either load the image into Minikube or set `imagePullPolicy: IfNotPresent` (the example manifest may default to pulling).

## RBAC / in-cluster configuration
- When running inside the cluster use `config.load_incluster_config()` in code; the Pod will use its ServiceAccount token mounted at `/var/run/secrets/kubernetes.io/serviceaccount`.
- The default service account has no privileges. To call the Kubernetes API (e.g., list pods or read pod logs) create a ServiceAccount and bind a Role/ClusterRole with the minimal verbs (`get`, `list`, `watch`) for `pods` and `pods/log` and set `spec.template.spec.serviceAccountName` in the Deployment.

Example minimal Role (namespace-scoped):
```yaml
kind: Role
rules:
  - apiGroups: [""]
    resources: ["pods","pods/log"]
    verbs: ["get","list","watch"]
```

## Versioning
- Single source of truth is the `VERSION` file. The app reads it at runtime, CI tags images from it, and `deploy.yml` pins the same tag.
- To release a new version, bump `VERSION`, push to `main`, and update `deploy.yml` if you maintain a pinned tag there.

## Endpoints and probes
- `/` — HTML list of pods with links to their logs endpoint.
- `/logs/{namespace}/{pod}` — returns pod logs (the app uses the Kubernetes Python client to fetch logs).
- `/health` — readiness-style check (suitable for readinessProbe).
- `/heartbeat` — cheap liveness check (suitable for livenessProbe).

Kubernetes probe example in `deploy.yml` shows how to use these endpoints for readiness and liveness.

## Logging and startup messages
- The app uses Python logging and a FastAPI lifespan handler to log startup/shutdown messages. If you don't see `logger.info(...)` in the console, run Uvicorn with `--log-level info` or configure `logging.basicConfig(level=logging.INFO)` early in `main.py` so handlers are present before startup.

## Type hints for `kubernetes` client
- The upstream `kubernetes` Python client ships generated code without full type stubs for API methods. Use `stubgen` (from `mypy`) to generate stubs and place them under a `typings/` folder, or add small `.pyi` stubs in your repo (example: `typings/kubernetes/client/api/discovery_v1_api.pyi`) so Pyright/Pylance resolves return types like `V1EndpointSliceList`.

## Troubleshooting
- SVC_UNREACHABLE / Service has no endpoints: `kubectl get pods` and `kubectl get endpoints <svc>` — check pods readiness and labels.
- ImagePullBackOff: ensure image is available in Minikube (use `minikube image load` or `eval $(minikube docker-env)` before `docker build`) or change `imagePullPolicy`.
- `ConfigException: Invalid kube-config file. No configuration found.`: running inside a pod without in-cluster config — use `config.load_incluster_config()` or mount a kubeconfig for local runs.
- `ApiException: (403) ... system:serviceaccount:... cannot list resource "pods"`: grant RBAC (Role/RoleBinding or ClusterRole/ClusterRoleBinding) to the ServiceAccount used by the Pod.

## Useful commands
```bash
kubectl get pods -o wide
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl rollout status deployment/k8s-logs
minikube image list
minikube service k8s-logs --url
```

## Where to look in this repo
- `main.py` — app logic and endpoints
- `deploy.yml` — Kubernetes manifests (Deployment, Service, RBAC)
- `Dockerfile`, `requirements.txt` — build and runtime dependencies
- `build_and_push_to_minikube.sh` — helper script

If you want, I can expand this README with exact manifests or add the generated `typings/` stubs to the repo.
