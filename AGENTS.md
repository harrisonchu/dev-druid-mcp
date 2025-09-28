# Agent Workflow Tips

This repository expects MCP agents to follow a tight loop when modifying Apache Druid source code and validating the running stack. A good default flow:

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
