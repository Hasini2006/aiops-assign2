# Evidence

Screenshots for each question, in order. Replace each `![]()` placeholder with
your actual screenshot (e.g. `![](screenshots/q1-01-naive-build.png)`); the
caption underneath each one explains what it needs to show.

---

## Question 1 — Naive vs. Multi-Stage Docker Build

**1.1 — Naive image build**

![](attachments/Naive-image-proof.png)

`docker build -f Dockerfile.single -t naive-image .` completing successfully.

**1.2 — Multi-stage image build**
![](attachments/Multistage-image-proof.png)
`docker build -f Dockerfile.multi -t multistage-image .` completing successfully.

**1.3 — Size comparison**
![](attachments/Size-Comparision.png)
`docker images naive-image multistage-image --format "{{.Repository}}: {{.Size}}"` — the core evidence for the size claim in the write-up.

**1.4 — Naive image serving correctly**
![](attachments/Containers-working-proof.png)
`docker run` the naive image, then `curl .../healthz` and `curl -X POST .../predict` both returning correct responses.

**1.5 — Multi-stage image serving correctly**
![](attachments/Curl-commands.png)
Same two `curl` calls against the multi-stage image, showing identical behavior to 1.4.

---

## Question 2 — Docker Compose + Redis Caching

**2.1 — Stack starting up**
![](attachments/re/2.1.png)
`docker compose up --build -d` completing, both `api` and `cache` containers created.

**2.2 — Both services running**
![](attachments/re/2.2.png)
`docker compose ps` (or `docker ps`) showing `spam-api` and `spam-cache` both `Up`.

**2.3 — Cache miss then cache hit, with timing**
![](attachments/re/2.2.png)

**2.4 — Server-side confirmation**
![](attachments/re/2.1.png)
`docker compose logs api` showing the `[cache MISS]` line followed by a `[cache HIT]` line for the same hashed key.

---

## Question 3 — Kubernetes Indexed Job

**3.1 — Image built and loaded onto every node**
![](attachments/re/3.1.png)
`minikube image build --all -t shard-validator:latest ...` output, plus `minikube ssh --node <name> -- docker images | grep shard-validator` confirming it landed on each node.

**3.2 — 2-node run: pods and parallelism**
![](attachments/re/3.2.png)
`kubectl get pods -l job-name=shard-validation-2node -o wide` — the `NODE` column should show pods on both nodes, and matching `AGE` values across multiple pods as evidence that `parallelism: 4` produced genuinely concurrent pods, not a sequential queue.

**3.3 — 2-node run: Job completion**
![](attachments/re/3.3.png)
`kubectl get job shard-validation-2node` showing `COMPLETIONS: 8/8`.

**3.4 — 2-node run: collected results**
![](attachments/re/3.4.png)
`python collect_results.py --job-name shard-validation-2node` output — all 8 shards, `invalid_rows` matching the planted counts (2–9), `Nodes that participated` showing both nodes.

**3.5 — 3-node run: pods spread across all 3 nodes**
![](attachments/re/3.5.png)
`kubectl get pods -l job-name=shard-validation-3node -o wide` — the `NODE` column should show all 3 distinct nodes in use, evidence for the `parallelism: 6` / `topologySpreadConstraints` change made for the 6-CPU scenario.

**3.6 — 3-node run: Job completion**
![](attachments/re/3.6.png)
`kubectl get job shard-validation-3node` showing `COMPLETIONS: 8/8`.

**3.7 — 3-node run: collected results**
![](attachments/re/3.7.png)
`python collect_results.py --job-name shard-validation-3node --out results_3node.csv` output — `Nodes that participated` showing all 3 nodes; corresponds to `results_3node.csv` in the repo.

---

## Question 4 — Kubernetes Deployment + Service

**4.1 — Deployment and Service applied**
![](attachments/re/4.1.png)
`kubectl apply -f k8s/deployment.yaml` and `kubectl apply -f k8s/service.yaml`, then `kubectl get pods -l app=spam-api -o wide` showing 2 `Running` pods, and `kubectl get svc spam-api-svc`.

**4.2 — Service reachable, v1**
![](attachments/re/4.2.png)
`curl .../healthz` returning `{"status":"ok","version":"v1"}` and `curl -X POST .../predict` returning a correct prediction.

**4.3 — Self-healing: before deletion**
![](attachments/re/4.3.png)
`kubectl get pods -l app=spam-api` showing the 2 original pod names and their `AGE`.

**4.4 — Self-healing: pod deleted, replacement created**
![](attachments/re/4.4.png)
`kubectl delete pod <name>` followed immediately by `kubectl get pods -l app=spam-api` (showing a `Terminating`/new pod), then again a few seconds later showing 2 `Running` pods, one with a new name and near-zero `AGE`.

**4.5 — Self-healing: controller evidence**
![](attachments/re/4.5.png)
`kubectl describe deployment spam-api` — the `Events` section showing the ReplicaSet scaling back up.

**4.6 — Rolling update: new image built**
![](attachments/re/4.6.png)
`minikube image build --all -t spam-api:v2 ...` completing successfully.

**4.7 — Rolling update: rollout triggered and completed**
![](attachments/re/4.6.png)
`kubectl set image deployment/spam-api api=spam-api:v2`, then `kubectl rollout status deployment/spam-api` reaching `successfully rolled out`.

**4.8 — Rolling update: history**
![](attachments/re/44.png)
`kubectl rollout history deployment/spam-api` showing at least two revisions.

**4.9 — Rolling update: version visibly changed**
![](attachments/re/4.7.png)
`curl .../healthz` now returning `{"status":"ok","version":"v2"}`.

**4.10 — Rolling update: no downtime**
![](attachments/re/4.9.png)
Output of a loop (`while true; do curl -s .../healthz; echo; sleep 0.5; done`) run during the rollout, showing responses flip from `v1` to `v2` with no failed or empty lines in between.