# dev-druid-mcp

Local Apache Druid development environment wired for MCP agents.

## What you get
- Docker Compose stack with Zookeeper, PostgreSQL metadata store, and standalone Druid services (`coordinator`, `overlord`, `broker`, `router`, `historical`, `middleManager`).
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
│   │   ├── query/{broker,router}/
│   │   └── data/{historical,middleManager}/
│   ├── logs/
│   ├── overrides/
│   └── storage/
└── druid-src/            # drop a Druid distribution here if you want to build from source
```

## Prerequisites
- Docker and Docker Compose (Compose V2 CLI).
- Enough free RAM/CPU for six JVMs plus the router; defaults stay under ~8 GiB RAM.

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
3. Access the Druid web console via the router at <http://localhost:8888>.
4. Tail logs (examples):
   ```bash
   docker compose logs -f router
   docker compose logs -f coordinator
   docker compose logs -f overlord
   ```
   Service-specific logs also land in `druid/logs/${sys:druid.node.type}.log` because of the bind mount.
5. Restart a component after tweaking configs:
   ```bash
   docker compose restart broker
   ```
6. Shut everything down (keeps the metadata volume):
   ```bash
   docker compose down
   ```
7. Rebuild and hot swap edited Druid modules without a full cluster restart:
   ```bash
   python3 tools/hotswap.py --dry-run
   ```
   The Python helper inspects your changes (or an explicit `--modules` list), runs a targeted `mvn -pl <modules> -am -DskipTests package`, copies the resulting `target/*.jar` outputs into `druid/overrides/`, restarts the Docker services, and reports a JSON status summary. Drop the `--dry-run` flag to apply changes for real once you’re satisfied with the detected modules.

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
- Router: `.../query/router/runtime.properties`
- Historical: `.../data/historical/runtime.properties`
- MiddleManager: `.../data/middleManager/runtime.properties`

Use these files for port changes, cache sizes, processing buffers, and service-specific behaviour. Keep property values literal (no inline comments after the value) to avoid Jackson parsing errors.

### JVM tuning
Each service directory also contains a `jvm.config`. Update the `-Xms`, `-Xmx`, or direct memory flags there when you need to adjust heap sizes.

### Overrides and custom code
- Drop additional jars in `druid/overrides` to make them visible under `/opt/druid/overrides` inside every container.
- Bind mount `druid-override.sh` over `/opt/druid/bin/druid.sh` so those jars are first on the runtime classpath; configure `DRUID_OVERRIDES` if you need a different glob.
  ```yaml
  volumes:
    - ./druid/overrides:/opt/druid/overrides:ro
    - ./druid-override.sh:/opt/druid/bin/druid.sh:ro
  environment:
    - DRUID_OVERRIDES=/opt/druid/overrides/*
  ```
- Place a full Druid distro in `druid-src/` if you want to swap binaries; the compose stack currently uses the official `apache/druid:29.0.0` image.

## Troubleshooting tips
- `docker compose ps -a` surfaces exited containers. Inspect their logs via `docker compose logs <service>` or copy the on-disk log, e.g.:
  ```bash
  docker cp druid-broker:/opt/druid/log/\${sys:druid.node.type}.log ./broker.log
  ```
- If a service complains about missing extensions, ensure the extension name in `_common/common.runtime.properties` matches the directory under `/opt/druid/extensions` (use `docker run --rm --entrypoint ls apache/druid:29.0.0 /opt/druid/extensions`).
- Postgres schema issues? Remove the Docker volume with `docker volume rm dev-druid-mcp_metadata-data` to reset metadata storage.

## Tools

### Persona-Chat ingest helper
- Script: `tools/ingest_persona_chat.py`
- Purpose: downloads the Hugging Face Persona-Chat dataset, writes a JSONL file under `druid/storage/ingestion/`, and submits an `index_parallel` task that loads each conversation (persona plus utterances JSON blobs) into the `conversations-2` datasource with at least five hash partitions.
- Usage:
  ```bash
  conda activate druid
  python tools/ingest_persona_chat.py --wait
  ```
  The command emits progress, waits for the ingestion task to finish, and leaves the exported file at `druid/storage/ingestion/persona-chat-conversations-2.jsonl` for reuse.

## Next steps
- Load additional sample data via the Druid console (`http://localhost:8888`) or API once the stack is up.
- Explore segment health with `curl http://localhost:8081/druid/coordinator/v1/datasources`.
