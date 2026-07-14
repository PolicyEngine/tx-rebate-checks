"""Spawn the deployed statewide pipeline function and poll for its
result, writing the CSVs locally when it finishes.

The plain ``modal run`` client has to stay alive for the whole
simulation; on machines that cap foreground process time, spawning the
deployed function and polling survives client restarts:

    modal deploy scripts/modal_pipeline.py       # once per code change
    uv run --with modal python scripts/run_state_pipeline_detached.py
    uv run --with modal python scripts/run_state_pipeline_detached.py --poll <call-id>
"""

import os
import sys
import time

import modal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modal_pipeline import _save_csvs  # noqa: E402

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "public",
    "data",
)


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--poll":
        call = modal.FunctionCall.from_id(sys.argv[2])
    else:
        fn = modal.Function.from_name(
            "tx-rebate-checks-pipeline", "calculate_impacts"
        )
        call = fn.spawn()
        print(f"spawned: {call.object_id}", flush=True)

    while True:
        try:
            result = call.get(timeout=15)
            break
        except TimeoutError:
            print("computing...", flush=True)
            time.sleep(15)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    _save_csvs(result, OUTPUT_DIR)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
