# Agent Workflow Tips

This repository expects agents to follow a tight loop when modifying Apache Druid source code and validating the running stack. A good default flow:

1. **Prepare the stack**
   - Ensure Docker Desktop is running.
   - From repo root run `docker compose up -d`; wait until every service reports `Up` (`docker compose ps`).

2. **Make code changes in `druid-src/`**
   - Run a "git stash" to make sure no changes from previous sessions are included
   - Edit Java modules inside `druid-src`, not `druid-runtime/`.
   - Keep the change focused; 

3. **Rebuild & deploy with the hotswap script**
   - Invoke `python3 tools/hotswap.py` (use `--dry-run` first if unsure). The script will automatically figure out which modules to rebuild. However, if you absolutely know what you are doing, you can tell it exactly which modules to rebuild via python3 tools/hotswap.py --modules <module>
   - The script will:
     - Build the targeted Maven modules.
     - Remove stale jars from `druid-runtime/overrides` before copying in the new artifacts.
     - Clear `druid-runtime/logs` so the next startup contains only fresh output.
     - Run `docker compose restart` to bounce all services.
   - Watch the stdout for the JSON summary; it should list the jars deployed and services restarted.
   - The script can take up to 3 minutes to complete.

4. **Verify results**
   - Tail logs from `druid-runtime/logs/` (e.g., `tail -n 100 druid-runtime/logs/router.log`) or via `docker compose logs <service>`.
   - Confirm behavior from logs if any
   - If verification fails, repeat: adjust code, rerun the script, re-check logs.

5. **Cleanup**
   - Remove temporary `.pyc` caches if created manually.
   - Leave Docker services running if you intend more edits; use `docker compose down` only when finished.

Keeping to this loop avoids stale jars or logs confusing subsequent validation passes.

# Profiling

There are some requests for the agent that will necessarily require the agent to profile Druid. To this end, every Druid container ships with async-profiler https://github.com/async-profiler/async-profiler/tree/master. A typical workflow:

1. **Find the Java process ID for the Druid service container**
   - This is typically just PID: 1
   - To double check, run `ps | grep '/usr/bin/java'`

2. **Run the profiler (assuming PID: 1)**
   - `asprof -d 10 -o tree 1 -f '/tmp/[FLAMEGRAPH_PROFILE_FROM_SESSION].html` You should copy this file from the docker container in to the repo directory `./sessions/[CODEX_SESSION_ID]` for review later. You can youse BeautifulSoup to parse this profile and grab insights from it.

3. **Execute action under profile**
   - If a query is what's being profiled, note that by default Druid caches query results. To get a real profile you must disable this. 
```
    {"query":"SELECT COUNT(*) FROM \"wikipedia-2\" WHERE contains_string(\"comment\", 'bot')","context":
        {"useCache":false,"populateCache":false,"useResultLevelCache":false,"populateResultLevelCache":false}}
```
