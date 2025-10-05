# dev-druid-mcp
`druid-agent-sandbox` is a self-contained runtime sandbox for LLM agents.
Your agent (e.g. Codex / Claude Code) can pull Druid source, modify code, hot-swap JARs, load datasets, and run live queries — producing runtime-grounded traces instead of static guesses.

It gives an agent a safe, reproducible environment to:
- Build and run a full Druid stack locally (via Docker Compose)
- Load Datasources (Persona-Chat, Wikipedia, etc.)
- Modify source code, re-build, and hot-swap changed modules
- Generate runtime artifacts (logs, flamegraphs, ingestion tasks) for human analysis after each session.

Think of it as a perfect environment you would give a smart intern to delegate a lot of the typical pre / background work you'd like to do before starting a big project.

## Usage
```bash
# 1. Bring up stack + fetch Druid source
./quickstart.sh

# 2. Confirm it’s running
docker compose ps
# Open http://localhost:8888 to verify

# 3. Ingest sample dataset (Persona-Chat)
python tools/ingest_persona_chat.py --wait

# 4. Hand control to your agent
codex "Profile Druid's contains_string text filter on the 'utterances' column in the 'conversations-2' datasource and propose improvements. Read AGENTS.md first."
```

At the end of each session, codex will store all the relevant artifacts, scripts to reproduce and more under a unique folder in the `/sessions` directory.

## Repo layout
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

## Next steps (notes for harrison)
- figure out why AGENTS.md are not respected
- Current tools for loading data are hyper specific. Explore using something like MCP with broader capabilities while giving better "insertion points" for the agent to express creativity. eventually these can be used to generate traces for SFT as a next potential interesting direction for this project
