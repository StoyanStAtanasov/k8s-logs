from typing import cast, Optional
import fastapi
import logging
from kubernetes.client.models import V1Pod, V1PodList, V1ObjectMeta
from kubernetes.config.config_exception import ConfigException
from kubernetes import client, config
from contextlib import asynccontextmanager
from pathlib import Path

logging.basicConfig(level=logging.INFO)
from fastapi.logger import logger

def _read_version() -> str:
    try:
        return Path(__file__).with_name("VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "v0.0.0"

version = _read_version()

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    logger.info(f"K8S Logs {version} starting")
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster kube config")
    except ConfigException:
        try:
            config.load_kube_config()
            logger.info("Loaded local kubeconfig")
        except ConfigException as e:
            logger.error("No kube config available", exc_info=True)
            raise RuntimeError("No kube config available (not in cluster and no local kubeconfig)") from e
    try:
        yield
    finally:
        logger.info(f"K8S Logs {version} stopping")

app = fastapi.FastAPI(lifespan=lifespan)


@app.get("/health", response_class=fastapi.responses.JSONResponse)
def health_check():
    return {"status": "healthy"}


@app.get("/heartbeat", response_class=fastapi.responses.PlainTextResponse)
def heartbeat():
    return "ok"


@app.get("/", response_class=fastapi.responses.HTMLResponse)
def read_root():
    # list all pods
    v1_api = client.CoreV1Api()
    pods = cast(V1PodList, v1_api.list_pod_for_all_namespaces(watch=False))
    items = []
    for pod in cast(list[V1Pod], pods.items):
        meta = cast(Optional[V1ObjectMeta], pod.metadata)
        name = getattr(meta, "name", "unknown")
        namespace = getattr(meta, "namespace", "default")
        # list containers within the pod
        conts = []
        spec = getattr(pod, "spec", None)
        if spec and getattr(spec, "containers", None):
            for c in spec.containers:
                cname = getattr(c, "name", "")
                href = f"/logs/{namespace}/{name}/{cname}"
                conts.append(f'<li><a href="{href}">{namespace}/{name}:{cname}</a></li>')
        else:
            # fallback link to pod-level logs
            href = f"/logs/{namespace}/{name}"
            conts.append(f'<li><a href="{href}">{namespace}/{name}</a></li>')

        items.extend(conts)

    html = f"<html><body><h1>Pod containers {version}</h1><ul>" + "\n".join(items) + "</ul></body></html>"
    return html


def get_pod_logs(namespace: str, pod_name: str, container: Optional[str] = None, tail_lines: int = 200) -> str:
    from kubernetes import client, config
    # Use load_incluster_config() when running inside a pod with a service account
    v1 = client.CoreV1Api()
    logs: str = v1.read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        container=container,
        tail_lines=tail_lines,
        pretty=False,
        timestamps=False,
    )
    return logs


@app.get("/logs/{namespace}/{pod_name}", response_class=fastapi.responses.PlainTextResponse)
def get_pod_logs2(namespace: str, pod_name: str, container: Optional[str] = None):
    """Return logs for a pod. Optional query param `container` selects a container."""
    return get_pod_logs(namespace, pod_name, container=container)


@app.get("/logs/{namespace}/{pod_name}/{container}", response_class=fastapi.responses.PlainTextResponse)
def get_pod_container_logs(namespace: str, pod_name: str, container: str):
    """Return logs for a specific container in a pod."""
    return get_pod_logs(namespace, pod_name, container=container)
