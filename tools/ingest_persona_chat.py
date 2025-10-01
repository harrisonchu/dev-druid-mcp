#!/usr/bin/env python3
"""Download the Persona-Chat dataset and ingest it into Druid as `conversations-2`."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple


DATASET_REPO_ID = "AlekseyKorshuk/persona-chat"
CACHE_RELATIVE_PATH = Path("sessions") / "persona_chat_cache"
OUTPUT_RELATIVE_PATH = Path("druid") / "storage" / "ingestion" / "persona-chat-conversations-2.jsonl"
DATASOURCE_NAME = "conversations-2"

try:
    from datasets import load_dataset  # type: ignore
except ImportError as exc:  # pragma: no cover - helpful error path
    raise SystemExit(
        "The 'datasets' package is required. Install it with `pip install datasets`."
    ) from exc

try:
    import requests
except ImportError as exc:  # pragma: no cover - helpful error path
    raise SystemExit(
        "The 'requests' package is required. Install it with `pip install requests`."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the AlekseyKorshuk/persona-chat dataset from Hugging Face, "
            "persist each conversation as JSON strings, and submit a Druid "
            "index_parallel task that creates a datasource named 'conversations-2'."
        )
    )
    parser.add_argument(
        "--druid-url",
        default="http://localhost:8090",
        help="Base URL for the Druid Overlord API (default: http://localhost:8090).",
    )
    parser.add_argument(
        "--min-segments",
        type=int,
        default=5,
        help="Minimum number of hash partitions (segments) to create (default: 5).",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll the ingestion task until it succeeds or fails.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=10.0,
        help="Seconds between status checks when --wait is supplied (default: 10).",
    )
    return parser.parse_args()


def ensure_under_storage(repo_root: Path, output_path: Path) -> Path:
    storage_root = (repo_root / "druid" / "storage").resolve()
    resolved_output = output_path.resolve()
    try:
        resolved_output.relative_to(storage_root)
    except ValueError as exc:
        raise SystemExit(
            f"Output path {resolved_output} is outside the shared druid/storage directory; "
            "place the file under druid/storage so the containers can read it."
        ) from exc
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    return resolved_output


def export_conversations(dataset_dict, output_path: Path) -> Tuple[int, int]:
    base_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    conversation_counter = 0
    row_counter = 0
    with output_path.open("w", encoding="utf-8") as handle:
        if isinstance(dataset_dict, dict):
            iterable = dataset_dict.items()
        else:
            iterable = [("default", dataset_dict)]
        for split_name, split in iterable:
            for example_index, example in enumerate(split):
                conversation_id = f"{split_name}-{example_index:05d}"
                persona_values = example.get("personality") or []
                utterances = example.get("utterances") or []
                event_time = base_time + timedelta(minutes=conversation_counter)
                record = {
                    "event_time": event_time.isoformat().replace("+00:00", "Z"),
                    "conversation_id": conversation_id,
                    "split": split_name,
                    "personality": json.dumps(persona_values, ensure_ascii=True),
                    "utterances": json.dumps(utterances, ensure_ascii=True),
                }
                handle.write(json.dumps(record))
                handle.write("\n")
                conversation_counter += 1
                row_counter += 1
    return conversation_counter, row_counter


def build_ingestion_spec(
    data_source: str,
    container_base_dir: Path,
    filename: str,
    num_shards: int,
) -> dict:
    return {
        "type": "index_parallel",
        "spec": {
            "dataSchema": {
                "dataSource": data_source,
                "timestampSpec": {"column": "event_time", "format": "iso"},
                "dimensionsSpec": {
                    "dimensions": [
                        {"name": "conversation_id", "type": "string"},
                        {"name": "split", "type": "string"},
                        {"name": "personality", "type": "string"},
                        {"name": "utterances", "type": "string"},
                    ]
                },
                "metricsSpec": [
                    {"type": "count", "name": "message_count"},
                ],
                "granularitySpec": {
                    "type": "uniform",
                    "segmentGranularity": "day",
                    "queryGranularity": "none",
                    "rollup": True,
                },
            },
            "ioConfig": {
                "type": "index_parallel",
                "inputSource": {
                    "type": "local",
                    "baseDir": str(container_base_dir),
                    "filter": filename,
                },
                "inputFormat": {
                    "type": "json",
                    "keepNullColumns": True,
                    "flattenSpec": {"useFieldDiscovery": True},
                },
                "appendToExisting": False,
            },
            "tuningConfig": {
                "type": "index_parallel",
                "maxNumConcurrentSubTasks": 2,
                "partitionsSpec": {
                    "type": "hashed",
                    "numShards": num_shards,
                    "partitionDimensions": ["conversation_id"],
                },
                "forceGuaranteedRollup": True,
            },
        },
    }


def submit_task(base_url: str, spec: dict) -> str:
    endpoint = base_url.rstrip("/") + "/druid/indexer/v1/task"
    response = requests.post(endpoint, json=spec, timeout=60)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        details = response.text
        raise RuntimeError(
            f"Failed to submit ingestion task ({response.status_code}): {details}"
        ) from exc
    payload = response.json()
    task_id = payload.get("task")
    if not task_id:
        raise RuntimeError(f"Unexpected response from Druid Overlord: {payload}")
    return task_id


def wait_for_task(base_url: str, task_id: str, poll_interval: float) -> str:
    status_endpoint = base_url.rstrip("/") + f"/druid/indexer/v1/task/{task_id}/status"
    while True:
        time.sleep(max(poll_interval, 1.0))
        response = requests.get(status_endpoint, timeout=30)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status", {}).get("status")
        if status:
            print(f"Task {task_id} status: {status}")
        if status in {"SUCCESS", "FAILED"}:
            return status or "UNKNOWN"


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    args = parse_args()

    cache_dir = (repo_root / CACHE_RELATIVE_PATH).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    output_path = ensure_under_storage(repo_root, repo_root / OUTPUT_RELATIVE_PATH)

    print(f"Downloading dataset {DATASET_REPO_ID} ...")
    dataset_dict = load_dataset(DATASET_REPO_ID, cache_dir=str(cache_dir))

    print(f"Serializing conversations to {output_path} ...")
    conversations, rows = export_conversations(dataset_dict, output_path)
    if rows == 0:
        raise RuntimeError("No conversation rows were written; check the dataset contents.")

    storage_root = (repo_root / "druid" / "storage").resolve()
    relative_path = output_path.relative_to(storage_root)
    container_base_dir = Path("/opt/druid/var/druid") / relative_path.parent
    filename = relative_path.name

    num_shards = max(args.min_segments, 5)
    ingestion_spec = build_ingestion_spec(DATASOURCE_NAME, container_base_dir, filename, num_shards)

    print(
        "Submitting ingestion task to Druid Overlord at "
        f"{args.druid_url.rstrip('/')} ..."
    )
    task_id = submit_task(args.druid_url, ingestion_spec)
    print(
        f"Submitted task {task_id}. Conversations exported: {conversations}; rows: {rows}; "
        f"partitions requested: {num_shards}."
    )

    if args.wait:
        final_status = wait_for_task(args.druid_url, task_id, args.poll_interval)
        print(f"Task {task_id} finished with status: {final_status}")
        return 0 if final_status == "SUCCESS" else 1

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit("Interrupted")
