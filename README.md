# dev-druid-mcp

Local Apache Druid development environment wired for MCP agents.

## What you get
- Docker Compose stack with Zookeeper, PostgreSQL metadata store, and standalone Druid services (`coordinator`, `overlord`, `broker`, `historical`, `middleManager`).
- Quickstart-derived configuration tree under `druid/conf` with lighter memory footprints for laptop use.
- Bind mounts for logs (`druid/logs`), deep storage (`druid/storage`), and override jars (`druid/overrides`).

```
.
├── compose.yaml
├── .env
├── druid/
│   ├── conf/druid/cluster
│   │   ├── _common/
│   │   ├── master/{coordinator,overlord}/
│   │   ├── query/broker/
│   │   └── data/{historical,middleManager}/
│   ├── logs/
│   ├── overrides/
│   └── storage/
└── druid-src/            # drop a Druid distribution here if you want to build from source
```

## Prerequisites
- Docker and Docker Compose (Compose V2 CLI).
- Enough free RAM/CPU for six JVMs; defaults stay under ~8 GiB RAM.

## Usage
1. Start the stack:
   ```bash
   docker compose up -d
   ```
2. Check status:
   ```bash
   docker compose ps
   ```
   All services should show `Up`; Postgres reports `healthy` once ready.
3. Tail logs (examples):
   ```bash
   docker compose logs -f coordinator
   docker compose logs -f overlord
   ```
   Service-specific logs also land in `druid/logs/${sys:druid.node.type}.log` because of the bind mount.
4. Restart a component after tweaking configs:
   ```bash
   docker compose restart broker
   ```
5. Shut everything down (keeps the metadata volume):
   ```bash
   docker compose down
   ```

## Configuration knobs
### Shared settings
- `.env` – change `POSTGRES_*` credentials or the default log/tmp directories.
- `druid/conf/druid/cluster/_common/common.runtime.properties`
  - Extension list already includes `postgresql-metadata-storage`.
  - Metadata connection string targets the bundled Postgres service (`metadata-storage`).
  - Adjust deep storage and indexing log locations here if you relocate bind mounts.

### Service runtime properties
- Coordinator: `druid/conf/druid/cluster/master/coordinator/runtime.properties`
- Overlord: `.../master/overlord/runtime.properties`
- Broker: `.../query/broker/runtime.properties`
- Historical: `.../data/historical/runtime.properties`
- MiddleManager: `.../data/middleManager/runtime.properties`

Use these files for port changes, cache sizes, processing buffers, and service-specific behaviour. Keep property values literal (no inline comments after the value) to avoid Jackson parsing errors.

### JVM tuning
Each service directory also contains a `jvm.config`. Update the `-Xms`, `-Xmx`, or direct memory flags there when you need to adjust heap sizes.

### Overrides and custom code
- Drop additional jars in `druid/overrides` to make them visible under `/opt/druid/overrides` inside every container.
- Place a full Druid distro in `druid-src/` if you want to swap binaries; the compose stack currently uses the official `apache/druid:29.0.0` image.

## Troubleshooting tips
- `docker compose ps -a` surfaces exited containers. Inspect their logs via `docker compose logs <service>` or copy the on-disk log, e.g.:
  ```bash
  docker cp druid-broker:/opt/druid/log/\${sys:druid.node.type}.log ./broker.log
  ```
- If a service complains about missing extensions, ensure the extension name in `_common/common.runtime.properties` matches the directory under `/opt/druid/extensions` (use `docker run --rm --entrypoint ls apache/druid:29.0.0 /opt/druid/extensions`).
- Postgres schema issues? Remove the Docker volume with `docker volume rm dev-druid-mcp_metadata-data` to reset metadata storage.

## Next steps
- Load sample data via the Druid console (`http://localhost:8888`) or API once the stack is up.
- Wire additional observability tooling (Prometheus, Grafana) by extending `compose.yaml` if needed.
