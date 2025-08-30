# deprecated now is built with github actions and pushed to ghcr.io

echo "Building and pushing Docker image to Minikube..."
docker build -t k8s-logs:latest .

echo "Loading Docker image into Minikube..."
minikube image load k8s-logs:latest

echo "Applying Kubernetes manifests..."
kubectl apply -f deploy.yml

echo "Rolling out new deployment..."
kubectl rollout restart deployment k8s-logs

echo "Getting service URL..."
sleep 10
minikube service k8s-logs --url