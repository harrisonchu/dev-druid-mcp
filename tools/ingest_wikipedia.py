#!/usr/bin/env python3
"""Ingest the bundled Druid Wikipedia sample dataset as the `wikipedia` datasource."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DATASET_FILENAME = "wikiticker-2015-09-12-sampled.json.gz"
SOURCE_RELATIVE_PATH = (
    Path("druid-src") / "examples" / "quickstart" / "tutorial" / DATASET_FILENAME
)
DESTINATION_RELATIVE_PATH = (
    Path("druid-runtime") / "storage" / "ingestion" / "wikipedia" / DATASET_FILENAME
)
DATASOURCE_NAME = "wikipedia"
INTERVAL = "2015-09-12/2015-09-13"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy the bundled wikipedia sample data into the shared Druid storage directory and "
            "submit an index_parallel task that loads it into a datasource named 'wikipedia'."
        )
    )
    parser.add_argument(
        "--druid-url",
        default="http://localhost:8090",
        help="Base URL for the Druid Overlord API (default: http://localhost:8090).",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll the ingestion task until it finishes.",
    )
    return parser.parse_args()


def ensure_under_storage(repo_root: Path, output_path: Path) -> Path:
    storage_root = (repo_root / "druid-runtime" / "storage").resolve()
    resolved_output = output_path.resolve()
    try:
        resolved_output.relative_to(storage_root)
    except ValueError as exc:
        raise SystemExit(
            f"Output path {resolved_output} is outside druid-runtime/storage; place files under druid-runtime/storage "
            "so the containers can read them."
        ) from exc
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    return resolved_output


def copy_dataset(repo_root: Path) -> Path:
    source_path = (repo_root / SOURCE_RELATIVE_PATH).resolve()
    if not source_path.exists():
        raise SystemExit(f"Could not locate the bundled dataset at {source_path}.")

    destination_path = ensure_under_storage(repo_root, repo_root / DESTINATION_RELATIVE_PATH)
    shutil.copy2(source_path, destination_path)
    return destination_path


def build_ingestion_spec(container_base_dir: Path, filename: str) -> dict:
    return {
        "type": "index_parallel",
        "spec": {
            "dataSchema": {
                "dataSource": DATASOURCE_NAME,
                "timestampSpec": {"column": "time", "format": "iso"},
                "dimensionsSpec": {
                    "dimensions": [
                        "channel",
                        "cityName",
                        "comment",
                        "countryIsoCode",
                        "countryName",
                        "isAnonymous",
                        "isMinor",
                        "isNew",
                        "isRobot",
                        "isUnpatrolled",
                        "metroCode",
                        "namespace",
                        "page",
                        "regionIsoCode",
                        "regionName",
                        "user",
                        {"name": "added", "type": "long"},
                        {"name": "deleted", "type": "long"},
                        {"name": "delta", "type": "long"},
                    ]
                },
                "metricsSpec": [],
                "granularitySpec": {
                    "type": "uniform",
                    "segmentGranularity": "day",
                    "queryGranularity": "none",
                    "intervals": [INTERVAL],
                    "rollup": False,
                },
            },
            "ioConfig": {
                "type": "index_parallel",
                "inputSource": {
                    "type": "local",
                    "baseDir": str(container_base_dir),
                    "filter": filename,
                },
                "inputFormat": {"type": "json"},
                "appendToExisting": False,
            },
            "tuningConfig": {
                "type": "index_parallel",
                "maxRowsPerSegment": 5_000_000,
                "maxRowsInMemory": 25_000,
            },
        },
    }


def submit_task(base_url: str, spec: dict) -> str:
    endpoint = base_url.rstrip("/") + "/druid/indexer/v1/task"
    body = json.dumps(spec).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Failed to submit ingestion task ({exc.code}): {details}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to submit ingestion task: {exc}") from exc

    task_id = payload.get("task")
    if not task_id:
        raise RuntimeError(f"Unexpected response payload: {payload}")
    return task_id


def wait_for_task(base_url: str, task_id: str) -> str:
    status_endpoint = base_url.rstrip("/") + f"/druid/indexer/v1/task/{task_id}/status"
    while True:
        time.sleep(10.0)
        request = urllib.request.Request(status_endpoint, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", "replace")
            raise RuntimeError(
                f"Failed to fetch status for task {task_id} ({exc.code}): {details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Failed to fetch status for task {task_id}: {exc}") from exc
        status = payload.get("status", {}).get("status")
        if status:
            print(f"Task {task_id} status: {status}")
        if status in {"SUCCESS", "FAILED"}:
            return status or "UNKNOWN"


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    args = parse_args()

    print("Copying bundled wikipedia dataset into druid-runtime/storage ...")
    dataset_path = copy_dataset(repo_root)

    storage_root = (repo_root / "druid-runtime" / "storage").resolve()
    relative_path = dataset_path.relative_to(storage_root)
    container_base_dir = Path("/opt/druid/var/druid") / relative_path.parent
    filename = relative_path.name

    ingestion_spec = build_ingestion_spec(container_base_dir, filename)

    print(f"Submitting wikipedia ingestion task to {args.druid_url.rstrip('/')} ...")
    task_id = submit_task(args.druid_url, ingestion_spec)
    print(
        f"Submitted task {task_id}. Data copied to {dataset_path}. "
        "Datasource: wikipedia."
    )

    if args.wait:
        final_status = wait_for_task(args.druid_url, task_id)
        print(f"Task {task_id} finished with status: {final_status}")
        return 0 if final_status == "SUCCESS" else 1

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit("Interrupted")
