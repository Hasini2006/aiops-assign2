import argparse
import json
import re
import sys

import pandas as pd
from kubernetes import client, config

RESULT_LINE_RE = re.compile(r"RESULT_JSON:(\{.*\})")

def load_kube_config():
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

def collect(job_name, namespace="default"):
    load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace=namespace, label_selector=f"job-name={job_name}")
    if not pods.items:
        print(f"No pods found for job '{job_name}'.", file=sys.stderr)
        return pd.DataFrame()
    rows = []
    for pod in pods.items:
        pod_name = pod.metadata.name
        try:
            logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        except client.exceptions.ApiException as e:
            print(f"  Could not read logs for {pod_name}: {e.reason}", file=sys.stderr)
            continue
        match = RESULT_LINE_RE.search(logs)
        if not match:
            print(f"  No RESULT_JSON line in {pod_name} yet.", file=sys.stderr)
            continue
        result = json.loads(match.group(1))
        result["k8s_pod_phase"] = pod.status.phase
        rows.append(result)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("shard_index").reset_index(drop=True)
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    df = collect(args.job_name, args.namespace)
    if df.empty:
        print("No results collected.")
    else:
        pd.set_option("display.width", 120)
        print(df.to_string(index=False))
        print("\nNodes that participated:", sorted(df["node_name"].unique()))
        print("Total invalid rows across all shards:", int(df["invalid_rows"].sum()))
        if args.out:
            df.to_csv(args.out, index=False)