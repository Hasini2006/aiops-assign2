# AIOps Module 3 Assignment — Repository Overview

Four folders, one per question. Each is self-contained (its own Dockerfile(s),
dependencies, and app code) so it can be built and run independently.

| Folder | Question |
|---|---|
| `spam-api/` | Question 1 — naive vs. multi-stage Docker build |
| `spam-api-redis/` | Question 2 — Docker Compose + Redis caching |
| `shard-validation/` | Question 3 — Kubernetes Indexed Job |
| `spam-deployment/` | Question 4 — Kubernetes Deployment + Service |

---

## Setup & Running

### Prerequisites

- Docker
- `minikube` and `kubectl` (Questions 3 and 4 only)
- Python 3.12+ with a virtual environment for running local scripts (`collect_results.py` in Question 3)

### Question 1 — Naive vs. Multi-Stage Docker Build

```bash
cd spam-api

docker build -f Dockerfile.single -t naive-image .
docker build -f Dockerfile.multi -t multistage-image .

docker images naive-image multistage-image --format "{{.Repository}}: {{.Size}}"

docker run -d --name naive-container -p 8000:8000 naive-image
curl http://localhost:8000/healthz
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"text": "WIN a FREE iPhone now! Click here: bit.ly/xyz123"}'
docker stop naive-container && docker rm naive-container

docker run -d --name multistage-container -p 8001:8000 multistage-image
curl http://localhost:8001/healthz
docker stop multistage-container && docker rm multistage-container
```

### Question 2 — Docker Compose + Redis Caching

```bash
cd spam-api-redis

docker compose up --build -d
docker compose ps

# cache MISS then cache HIT, with timing
curl -s -w "\n[elapsed: %{time_total}s]\n" -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" -d '{"text": "WIN a FREE iPhone now! Click here: bit.ly/xyz123"}'
curl -s -w "\n[elapsed: %{time_total}s]\n" -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" -d '{"text": "WIN a FREE iPhone now! Click here: bit.ly/xyz123"}'

docker compose logs api   # confirms [cache MISS] then [cache HIT]
docker compose down
```

### Question 3 — Kubernetes Indexed Job

```bash
cd shard-validation

minikube start --nodes=2 --cpus=2 --memory=4096 --driver=docker

python3 generate_shards.py
minikube image build --all -t shard-validator:latest -f Dockerfile.job .

kubectl apply -f job-2node.yaml
kubectl get pods -l job-name=shard-validation-2node -o wide
kubectl get job shard-validation-2node

pip install -r requirements.txt
python collect_results.py --job-name shard-validation-2node
kubectl delete -f job-2node.yaml

# scale to 3 nodes for the 6-CPU scenario
minikube node add
minikube image build --all -t shard-validator:latest -f Dockerfile.job .

kubectl apply -f job-3node.yaml
kubectl get pods -l job-name=shard-validation-3node -o wide
kubectl get job shard-validation-3node

python collect_results.py --job-name shard-validation-3node --out results_3node.csv
kubectl delete -f job-3node.yaml
```

### Question 4 — Kubernetes Deployment + Service

```bash
cd spam-deployment

# ensure Dockerfile.multi has: ARG APP_VERSION=v1
minikube image build --all -t spam-api:v1 -f Dockerfile.multi .

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/spam-api

minikube service spam-api-svc --url
curl http://192.168.49.2:30090/healthz
curl -X POST http://192.168.49.2:30090/predict -H "Content-Type: application/json" \
  -d '{"text": "WIN a FREE iPhone now! Click here: bit.ly/xyz123"}'

# self-healing
kubectl get pods -l app=spam-api
kubectl delete pod <pod-name> --wait=false; kubectl get pods -l app=spam-api -w
kubectl describe deployment spam-api | grep -A5 Events

# rolling update -- edit Dockerfile.multi: ARG APP_VERSION=v2
minikube image build --all -t spam-api:v2 -f Dockerfile.multi .
kubectl set image deployment/spam-api api=spam-api:v2
kubectl rollout status deployment/spam-api
kubectl rollout history deployment/spam-api
curl http://192.168.49.2:30090/healthz   # now shows "version":"v2"
```

---

## `spam-api/` — Question 1

| File | What it does |
|---|---|
| `.dockerignore` | Keeps local `venv/`, `__pycache__/`, and generated files out of the Docker build context. |
| `app.py` | FastAPI service exposing `POST /predict` and `GET /healthz`. |
| `Dockerfile.single` | Naive, single-stage build — everything (training deps and runtime deps) baked into one image. |
| `Dockerfile.multi` | Multi-stage build — trains in a throwaway `builder` stage, ships only the trained model + runtime deps in a minimal final stage. |
| `generate_data.py` | Generates the deterministic, seeded synthetic spam/ham dataset. |
| `requirements.txt` | Combined dependencies used by `Dockerfile.single`. |
| `requirements-train.txt` | Training-only dependencies (pandas, scikit-learn, joblib) for `Dockerfile.multi`'s builder stage. |
| `requirements-serve.txt` | Serving-only dependencies (fastapi, uvicorn, scikit-learn, joblib — no pandas) for `Dockerfile.multi`'s runtime stage. |
| `train.py` | Trains the TF-IDF + MultinomialNB pipeline on the full dataset and saves `model.joblib`. |
| `spam_dataset.csv` | Generated dataset from local testing (regenerated fresh inside every image build; not needed for the build itself). |

## `spam-api-redis/` — Question 2

| File | What it does |
|---|---|
| `.dockerignore` | Same purpose as above. |
| `app.py` | Same API as Question 1, plus a Redis cache in front of `/predict` (hash the input text, check cache, compute on miss, store with a TTL, degrade gracefully if Redis is unreachable). |
| `docker-compose.yml` | Defines the `api` and `cache` (`redis:7-alpine`) services, their resource-free internal networking, and a healthcheck-gated startup order. |
| `Dockerfile.multi` | Same multi-stage build as Question 1, reused to build the `api` service's image. |
| `generate_data.py`, `requirements-train.txt`, `requirements-serve.txt`, `train.py`, `spam_dataset.csv` | Same roles as their `spam-api/` counterparts. |

## `shard-validation/` — Question 3

| File | What it does |
|---|---|
| `generate_shards.py` | Run once, ahead of time: writes the 8 deterministic, seeded shard CSVs (`data/shard_0.csv` … `shard_7.csv`), each with a known number of deliberately invalid rows. |
| `data/` | The 8 generated shard CSVs, baked into the validator image by `Dockerfile.job`. |
| `validate_shard.py` | Runs inside each pod: reads `JOB_COMPLETION_INDEX` to pick its own shard, validates every row, prints one `RESULT_JSON:{...}` line. |
| `Dockerfile.job` | Builds the shard-validator image (bakes in `validate_shard.py` and `data/` — no shared volume needed for input data). |
| `job-2node.yaml` | Indexed Job manifest for the 4-CPU scenario (2 nodes × 2 CPUs) — `parallelism: 4`. |
| `job-3node.yaml` | Indexed Job manifest for the 6-CPU scenario (3 nodes × 2 CPUs) — `parallelism: 6`, with `topologySpreadConstraints` to spread pods across all 3 nodes. |
| `collect_results.py` | Run locally: pulls every pod's `RESULT_JSON` log line via the Kubernetes API (not a shared volume) and prints/saves the aggregated results table. |
| `requirements.txt` | Dependencies for `collect_results.py` (`kubernetes`, `pandas`) — run on your machine, never baked into the image. |
| `results_3node.csv` | Saved output of `collect_results.py` from the 3-node run, kept as evidence. |

## `spam-deployment/` — Question 4

| File | What it does |
|---|---|
| `app.py` | Same API, plus an `APP_VERSION` field returned by `/healthz` — this is what makes the rolling update in part 3 visible. |
| `Dockerfile.multi` | Multi-stage build with an `ARG`/`ENV APP_VERSION` baked in at build time, so `spam-api:v1` and `spam-api:v2` are genuinely different images. |
| `generate_data.py`, `requirements.txt`, `requirements-train.txt`, `requirements-serve.txt`, `train.py` | Same roles as in `spam-api/`. |
| `k8s/deployment.yaml` | Deployment manifest — 2 replicas, CPU/memory requests+limits, readiness probe (traffic gating) and liveness probe (stuck-container restart) both on `/healthz`, a zero-downtime rolling-update strategy. |
| `k8s/service.yaml` | NodePort Service routing to the Deployment's pods by label, on a fixed port (`30090`) for repeatable testing. |
| `deployment.yaml` | Appears to duplicate `k8s/deployment.yaml` at the folder root — worth removing if it's a leftover copy rather than intentional. |

## Root

| File | What it does |
|---|---|
| `Report-2-DA24B041` | Explanations for required questions |
| `AI_DISCLOSURE.md` | Disclosure of AI assistance used in this assignment. |
| `README.md` | This file. |
