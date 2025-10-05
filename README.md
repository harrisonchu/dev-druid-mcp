# dev-druid-mcp

`druid-agent-sandbox` gives your agent CLI a sandbox to deeply understand the Druid source code to give you answers and suggestions grounded in runtime reality. It enables the agent to make code changes, deploy quickly, and the tools to observe and profile the results. Artifacts from each "session" are stored under the `session` directory for review later. These artifacts can be written markdowns, unit tests, or even sequence diagrams.

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
4. At the end of each session, codex will store all the relevant artifacts, scripts to reproduce and more under a unique folder in the `/sessions` directory.

## What you get
- Local Docker Compose stack with Zookeeper, PostgreSQL metadata store, standalone Druid services (`coordinator`, `overlord`, `broker`, `router`, `historical`, `middleManager`), and configuration tree under `druid-runtime/conf` with lighter memory footprints for laptop use.
- Bind mounts for logs (`druid-runtime/logs`), deep storage (`druid-runtime/storage`), and override jars (`druid-runtime/overrides`).
- Artifacts from each session with the agent will be persisted in the top level `sessions` directory.
- Tools that the agent can use to either deploy code, profile, or ingest data.
```
.
├── compose.yaml
├── .env
├── druid-runtime/
│   ├── conf/druid/cluster
│   │   ├── _common/
│   │   ├── master/{coordinator,overlord}/
│   │   ├── query/{broker,router}/
│   │   └── data/{historical,middleManager}/
│   ├── logs/
│   ├── overrides/
│   └── storage/
├── druid-src/           # quickstart script will create this for you. This is where modifiable Druid source code lives.
├── sessions/           # agent will drop any artifacts from each session here. e.g. explanations, graphs, etc
└── tools/              # (TODO)
```


## Tools

### Persona-Chat dataset ingestion
- Script: `tools/ingest_persona_chat.py`
- Purpose: downloads the Hugging Face Persona-Chat dataset, writes a JSONL file under `druid-runtime/storage/ingestion/`, and submits an `index_parallel` task that loads into the `conversations-2` datasource with at least five hash partitions. This is a good dataset to use if you are testing or profiling something that can take advantage of either high segment counts or columns with long text strings.
- Usage:
  ```bash
  python tools/ingest_persona_chat.py --wait
  ```
  The command emits progress, waits for the ingestion task to finish, and leaves the exported file at `druid-runtime/storage/ingestion/persona-chat-conversations-2.jsonl` for reuse.

### Wikipedia dataset ingestion
- Script: `tools/ingest_wikipedia.py`
- Purpose: downloads the wikipedia dataset. This is suitable for general tasks.
- Usage:
  ```bash
  python tools/ingest_wikipedia.py --wait
  ```

### Overrides and custom Druid code
- Script: `tools/hotswap.py`
- Purpose: identifies which modules any code change in `druid-src` affects, builds those jars, drops those jars in `druid-runtime/overrides` to make them visible under `/opt/druid/overrides` inside every container.

## Troubleshooting tips
- `docker compose ps -a` surfaces exited containers. Inspect their logs via `docker compose logs <service>` or copy the on-disk log, e.g.:
  ```bash
  docker cp druid-broker:/opt/druid/log/\${sys:druid.node.type}.log ./broker.log
  ```
- If a service complains about missing extensions, ensure the extension name in `_common/common.runtime.properties` matches the directory under `/opt/druid/extensions` (use `docker run --rm --entrypoint ls apache/druid:29.0.0 /opt/druid/extensions`).
- If you are running into issues that seem stateful in any way, deleting everything under `/druid-runtime/storage` and restarting will give you a fresh start.
- Historicals can be a memory hog especially with the chat dataset. Be sure to give Docker enough memory as well as adjusting JVM configs for the historicals.

## Next steps
- quickstart should check python and dependencies installed
- figure out why AGENTS.md not respected
- bind mount Postgres instead of docker mount
- test end to end mermaid / flamegraph / using substring search query
