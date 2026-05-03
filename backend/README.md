# Backend Skeleton

Three runnable surfaces:

- `apps/admin_api`
- `apps/gateway_api`
- `apps/worker`

Shared domain code lives in `app/`.

## Local Milvus Flow

One-command local integration flow:

```bash
cd /Users/liyinghui/Desktop/harness
make local-flow
```

Keep admin/gateway running after smoke test for frontend联调:

```bash
cd /Users/liyinghui/Desktop/harness
make local-flow-up
```

What it does:

1. installs backend dev dependencies
2. starts Milvus with Docker Compose
3. initializes the `Canary` database and collections
4. starts `admin_api` on `127.0.0.1:8000` by default, or the next free local port
5. starts `gateway_api` on `127.0.0.1:8001` by default, or the next free local port
6. runs the smoke test

Useful commands:

```bash
make milvus-up
make milvus-down
make local-flow-up
make local-flow-stop
python3 /Users/liyinghui/Desktop/harness/scripts/init_milvus_canary.py
python3 /Users/liyinghui/Desktop/harness/scripts/smoke_test_canary.py
```

Environment variables supported by `scripts/run_local_milvus_flow.sh`:

- `ADMIN_PORT`
- `GATEWAY_PORT`
- `MILVUS_HOST`
- `MILVUS_PORT`
- `MILVUS_ALIAS`
- `MILVUS_DB_NAME`
- `MILVUS_IMAGE`
- `ETCD_IMAGE`
- `MINIO_IMAGE`
- `KEEP_MILVUS_UP=1` keeps the containers running after the script exits
- `KEEP_SERVICES_UP=1` keeps `admin_api` and `gateway_api` running after smoke test

Behavior notes:

- If `MILVUS_HOST:MILVUS_PORT` is already reachable, the script reuses that Milvus instance and skips `docker compose up`
- The compose file uses `pull_policy: never`, so it only uses local images
- `make local-flow-up` writes the chosen ports and base URLs to `/Users/liyinghui/Desktop/harness/.run/local-flow.env`
