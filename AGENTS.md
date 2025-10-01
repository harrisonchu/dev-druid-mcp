# Agent Workflow Tips

This repository expects agents to follow a tight loop when modifying Apache Druid source code and validating the running stack. A good default flow:

1. **Prepare the stack**
   - Ensure Docker Desktop is running.
   - From repo root run `docker compose up -d`; wait until every service reports `Up` (`docker compose ps`).

2. **Make code changes in `druid-src/`**
   - Edit Java modules inside `druid-src`, not `druid/`. The Docker containers mount jars from `druid/overrides`, so rebuilding must happen from source.
   - Keep the change focused; capture a recognizable log message or behaviour to confirm later.

3. **Rebuild & deploy with the hotswap script**
   - Invoke `python3 tools/hotswap.py --modules <module>` (use `--dry-run` first if unsure).
   - The script will:
     - Build the targeted Maven modules.
     - Remove stale jars from `druid/overrides` before copying in the new artifacts.
     - Clear `druid/logs` so the next startup contains only fresh output.
     - Run `docker compose restart` to bounce all services.
   - Watch the stdout for the JSON summary; it should list the jars deployed and services restarted.

4. **Verify results**
   - Tail logs from `druid/logs/` (e.g., `tail -n 100 druid/logs/router.log`) or via `docker compose logs <service>`.
   - Confirm the new log line or behaviour appears and that old log entries are gone.
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
   - `asprof -d 10 1 -f '/tmp/[PROFILE_FROM_SESSION]'`. This outputs a version of the profile in text which is suitable for LLM consumption
   - `asprof -d 10 1 -f '/tmp/[FLAMEGRAPH_PROFILE_FROM_SESSION].html`. This outputs a version of the profile that is human readable. This is useful if you are compiling an artifact for human review later. You should copy this file from the docker container in to the repo directory `./sessions/[CODEX_SESSION_ID]` for review later


