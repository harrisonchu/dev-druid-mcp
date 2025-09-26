#!/usr/bin/env python3
"""Compile updated Druid modules and hot swap their jars into the dev stack."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild selected Druid modules, copy their jars into the overrides "
            "directory, and restart the Docker deployment so freshly built code "
            "is picked up."
        )
    )
    parser.add_argument(
        "--modules",
        "-m",
        action="append",
        metavar="MODULE",
        help=(
            "Explicit Maven module(s) to rebuild. Accepts repeated flags or "
            "comma-separated values."
        ),
    )
    parser.add_argument(
        "--since",
        metavar="GIT_REF",
        help=(
            "Git ref to diff against when determining which modules changed. "
            "If omitted and --modules is not supplied, uncommitted changes in "
            "druid-src are inspected instead."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the actions that would be performed without making changes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    druid_src = repo_root / "druid-src"
    overrides_dir = repo_root / "druid" / "overrides"

    if not druid_src.exists():
        print(
            f"druid-src directory not found at {druid_src}. "
            "Clone or unpack the Druid source tree before running this tool.",
            file=sys.stderr,
        )
        return 1

    start = time.perf_counter()
    modules = detect_modules(druid_src, args.modules, args.since)
    if not modules:
        print(
            "No Maven modules could be resolved from the provided arguments.",
            file=sys.stderr,
        )
        return 1

    log_heading("Building modules", ", ".join(modules))
    run_maven_build(druid_src, modules, dry_run=args.dry_run)

    log_heading("Deploying jars", f"-> {overrides_dir}")
    jars = deploy_jars(druid_src, overrides_dir, modules, dry_run=args.dry_run)

    log_heading("Restarting Docker", "docker compose restart")
    services = restart_docker(repo_root, dry_run=args.dry_run)

    elapsed = time.perf_counter() - start
    status = {
        "modules_built": modules,
        "jars_deployed": jars,
        "services_restarted": services,
        "elapsed_seconds": round(elapsed, 2),
        "dry_run": args.dry_run,
    }
    print(json.dumps(status, indent=2))
    return 0


def detect_modules(
    druid_src: Path,
    explicit_modules: Sequence[str] | None,
    since: str | None,
) -> List[str]:
    if explicit_modules:
        return _dedupe([m for part in explicit_modules for m in _split_modules(part)])

    changed_files = list(_find_changed_files(druid_src, since))
    modules: List[str] = []
    for rel_path in changed_files:
        module = _module_for_path(druid_src, rel_path)
        if module and module not in modules:
            modules.append(module)
    return modules


def _find_changed_files(druid_src: Path, since: str | None) -> Iterable[Path]:
    if since:
        cmd = ["git", "diff", "--name-only", f"{since}..HEAD"]
    else:
        cmd = ["git", "status", "--porcelain=1"]
    try:
        result = subprocess.run(
            cmd,
            cwd=druid_src,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(
            "Failed to inspect git changes:\n" + exc.stderr,
            file=sys.stderr,
        )
        raise SystemExit(exc.returncode) from exc

    lines = [line.strip("\n") for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return []

    if since:
        return [Path(line) for line in lines]

    files: List[Path] = []
    for line in lines:
        path_fragment = line[3:] if len(line) > 3 else ""
        if " -> " in path_fragment:
            path_fragment = path_fragment.split(" -> ", 1)[1]
        if path_fragment:
            files.append(Path(path_fragment))
    return files


def _module_for_path(druid_src: Path, rel_path: Path) -> str | None:
    absolute = druid_src / rel_path
    if not absolute.exists():
        absolute = absolute.resolve()
    try:
        absolute.relative_to(druid_src)
    except ValueError:
        return None

    current = absolute
    while current != druid_src:
        if (current / "pom.xml").exists():
            return current.relative_to(druid_src).as_posix()
        current = current.parent
    return None


def run_maven_build(druid_src: Path, modules: Sequence[str], dry_run: bool = False) -> None:
    if dry_run:
        print("  dry-run: skipping mvn build")
        return

    module_selector = ",".join(modules)
    cmd = [
        "mvn",
        "-pl",
        module_selector,
        "-am",
        "-DskipTests",
        "package",
    ]
    try:
        subprocess.run(cmd, cwd=druid_src, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


def deploy_jars(
    druid_src: Path,
    overrides_dir: Path,
    modules: Sequence[str],
    dry_run: bool = False,
) -> List[str]:
    jars_copied: List[str] = []
    if not dry_run:
        overrides_dir.mkdir(parents=True, exist_ok=True)

    for module in modules:
        target_dir = druid_src / module / "target"
        if not target_dir.exists():
            print(f"  warning: no target/ directory for module {module}")
            continue
        for jar in sorted(target_dir.glob("*.jar")):
            dest = overrides_dir / jar.name
            jars_copied.append(dest.relative_to(overrides_dir).as_posix())
            if dry_run:
                print(f"  dry-run: would copy {jar} -> {dest}")
            else:
                shutil.copy2(jar, dest)
                print(f"  copied {jar.name} -> overrides/{dest.name}")
    return jars_copied


def restart_docker(repo_root: Path, dry_run: bool = False) -> List[str]:
    compose_cmd = _resolve_compose_command()
    if compose_cmd is None:
        print(
            "  warning: docker compose not available; please restart containers manually.",
            file=sys.stderr,
        )
        return []

    services: List[str] = []
    if dry_run:
        print("  dry-run: skipping docker compose restart")
        try:
            services = _list_compose_services(compose_cmd, repo_root)
        except subprocess.CalledProcessError:
            services = []
        return services

    try:
        services = _list_compose_services(compose_cmd, repo_root)
    except subprocess.CalledProcessError:
        services = []

    restart_cmd = compose_cmd + ["restart"]
    try:
        subprocess.run(restart_cmd, cwd=repo_root, check=True)
    except subprocess.CalledProcessError as exc:
        print(
            "  warning: docker compose restart failed; restart services manually.",
            file=sys.stderr,
        )
        return services
    return services


def _list_compose_services(compose_cmd: Sequence[str], repo_root: Path) -> List[str]:
    result = subprocess.run(
        list(compose_cmd) + ["ps", "--services"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _resolve_compose_command() -> List[str] | None:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def _split_modules(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _dedupe(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def log_heading(title: str, detail: str | None = None) -> None:
    if detail:
        print(f"\n==> {title}: {detail}")
    else:
        print(f"\n==> {title}")


if __name__ == "__main__":
    sys.exit(main())
