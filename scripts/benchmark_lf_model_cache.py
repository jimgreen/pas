"""Alternating-order LF cache benchmark with exact result equality checks."""
import argparse
import contextlib
import io
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pas.config import load_config
from pas.kernels import run_lf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--pairs", type=int, default=8)
    args = parser.parse_args()
    config = load_config(args.config)
    times = {"fresh": [], "cached": []}
    reads = {"fresh": [], "cached": []}
    with contextlib.redirect_stdout(io.StringIO()):
        expected = run_lf(config.tasks["lf"], config.kernel_root, use_model_cache=False)
        expected.pop("performance")
        run_lf(config.tasks["lf"], config.kernel_root)  # Warm imports and template.
        for pair in range(max(2, args.pairs)):
            for cache in ((False, True) if pair % 2 == 0 else (True, False)):
                started = time.perf_counter()
                actual = run_lf(config.tasks["lf"], config.kernel_root, use_model_cache=cache)
                elapsed = time.perf_counter() - started
                perf = actual.pop("performance")
                assert actual == expected, "LF numerical results changed"
                name = "cached" if cache else "fresh"
                times[name].append(elapsed)
                reads[name].append(perf["model_read_seconds"])
    result = {"model": str(config.tasks["lf"].model_file), "kernel": str(config.kernel_root),
              "pairs": len(times["fresh"]), "devices": len(expected["devices"]),
              "exact_results_equal": True, "total_seconds": times, "model_seconds": reads,
              "total_median_seconds": {key: statistics.median(values) for key, values in times.items()},
              "model_median_seconds": {key: statistics.median(values) for key, values in reads.items()}}
    result["total_speedup"] = statistics.median(times["fresh"]) / statistics.median(times["cached"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
