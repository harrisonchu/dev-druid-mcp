# dev-druid-mcp

`druid-agent-sandbox` gives your agent CLI a sandbox to deeply understand the Druid sourcecode to give you answers and suggestions grounded in runtime reality. It enables the agent to make code changes, deploy quickly, and the tools to observe and profile the results. Artifacts from each "session" are stored under the `session` directory for review later. These artifacts can be written markdowns, unit tests, or even sequence diagrams.

## Usage
1. Setup the repo
   ```bash
   ./quickstart.sh
   ```
2. (Optional) Check status:
   ```bash
   docker compose ps
   ```
   All services should show `Up`; Postgres reports `healthy` once ready.
   Access the Druid web console via the router at <http://localhost:8888>.
3. At the root directory, ask `codex` any question:
   ```bash
   codex "I'm interested in the performance chatacteristics of Druids contains_string text search filter. Profile this and tell me what are the most likely areas of improvement. you can use the 'utterances' column in the 'conversations-2' datasource. Before you begin please remember to read AGENTS.md for common workflows and tips to get your job done"
   ```

## What you get
- Local Docker Compose stack with Zookeeper, PostgreSQL metadata store, standalone Druid services (`coordinator`, `overlord`, `broker`, `router`, `historical`, `middleManager`), and configuration tree under `druid/conf` with lighter memory footprints for laptop use.
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
