from typing import cast, Optional
import fastapi
import logging
from kubernetes.client.models import V1Pod, V1PodList, V1ObjectMeta
from kubernetes.config.config_exception import ConfigException
from kubernetes import client, config
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
from fastapi.logger import logger

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    logger.info("K8S Logs v1 starting")
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
        logger.info("K8S Logs v1 stopping")

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
        href = f"/logs/{namespace}/{name}"
        items.append(f'<li><a href="{href}">{namespace}/{name}</a></li>')
    html = "<html><body><h1>Pods</h1><ul>" + \
        "\n".join(items) + "</ul></body></html>"
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
def get_pod_logs2(namespace: str, pod_name: str):
    return get_pod_logs(namespace, pod_name)
