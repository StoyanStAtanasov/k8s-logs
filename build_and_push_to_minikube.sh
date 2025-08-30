# deprecated now is built with github actions and pushed to ghcr.io

VERSION=$(cat VERSION)
IMAGE="ghcr.io/stoyanstatanasov/k8s-logs:${VERSION}"

echo "Building Docker image ${IMAGE}..."
docker build -t "${IMAGE}" .

echo "Loading Docker image into Minikube..."
minikube image load "${IMAGE}"

echo "Applying Kubernetes manifests..."
kubectl apply -f deploy.yml

echo "Rolling out new deployment..."
kubectl rollout restart deployment k8s-logs

echo "Getting service URL..."
sleep 10
minikube service k8s-logs --url
