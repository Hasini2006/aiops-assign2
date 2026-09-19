import argparse
import csv
import os
import random

ROWS_PER_SHARD = 30
NAMES = [
    "Alice Kumar", "Ben Ortiz", "Chidi Okafor", "Deepa Rao",
    "Elena Petrova", "Farid Haidari", "Grace Lin", "Hassan Ali",
]
DOMAINS = ["example.com", "mail.com", "shop.co"]


def build_shard(index: int, base_seed: int):
    rng = random.Random(base_seed + index)
    invalid_count = 2 + index

    rows = []
    for i in range(ROWS_PER_SHARD):
        name = rng.choice(NAMES)
        local = name.split()[0].lower()
        email = f"{local}{i}@{rng.choice(DOMAINS)}"
        rows.append({
            "id": i,
            "name": name,
            "email": email,
            "signup_date": f"2026-{1 + i % 9:02d}-15",
        })

    broken_indices = rng.sample(range(ROWS_PER_SHARD), invalid_count)
    for n, i in enumerate(broken_indices):
        if n % 2 == 0:
            rows[i]["name"] = ""
        else:
            rows[i]["email"] = rng.choice(["not-an-email", "missing-at-sign.com", ""])

    rng.shuffle(rows)
    return rows, invalid_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--n-shards", type=int, default=8)
    parser.add_argument("--base-seed", type=int, default=1000)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    for index in range(args.n_shards):
        rows, invalid_count = build_shard(index, args.base_seed)
        path = os.path.join(args.out_dir, f"shard_{index}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "email", "signup_date"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path}: {len(rows)} rows, {invalid_count} deliberately invalid")


if __name__ == "__main__":
    main()