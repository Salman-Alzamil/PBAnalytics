"""
publish_model.py  —  copy a checkpoint from a training run into backend/model/
and update the active_model.json config so the backend picks it up.

Usage:
    python publish_model.py --list                              # show all checkpoints + val metrics
    python publish_model.py --run run2 --checkpoint best       # publish best.pt
    python publish_model.py --run run2 --checkpoint epoch15    # publish epoch15.pt
    python publish_model.py --run run2 --checkpoint last --version v2.0-last
"""

import argparse
import csv
import json
import shutil
from pathlib import Path

RUNS_DIR    = Path("runs/classify")
BACKEND_DIR = Path("../backend/model")
CONFIG_PATH = BACKEND_DIR / "active_model.json"


def find_weights_dir(run_name: str) -> Path:
    direct = RUNS_DIR / run_name / "weights"
    if direct.exists():
        return direct
    nested = RUNS_DIR / "runs" / "classify" / run_name / "weights"
    if nested.exists():
        return nested
    raise FileNotFoundError(
        f"Could not find weights directory for run '{run_name}'.\n"
        f"Tried:\n  {direct}\n  {nested}"
    )


def _read_results_csv(run_name: str) -> dict[str, dict]:
    """Return {epoch_str: row_dict} from results.csv, keyed by 0-indexed epoch string."""
    for candidate in [
        RUNS_DIR / run_name / "results.csv",
        RUNS_DIR / "runs" / "classify" / run_name / "results.csv",
    ]:
        if candidate.exists():
            rows = {}
            with open(candidate, newline="") as f:
                for row in csv.DictReader(f):
                    rows[row["epoch"].strip()] = row
            return rows
    return {}


def _recommend(results: dict[str, dict]) -> str | None:
    """Return the 0-indexed epoch string with the lowest val/loss."""
    if not results:
        return None
    best_epoch = min(results, key=lambda e: float(results[e].get("val/loss", "inf")))
    return best_epoch


def list_checkpoints(run_name: str) -> None:
    weights_dir = find_weights_dir(run_name)
    pts         = sorted(weights_dir.glob("*.pt"))
    results     = _read_results_csv(run_name)
    recommend   = _recommend(results)

    if not pts:
        print(f"No .pt files found in {weights_dir}")
        return

    print(f"\nCheckpoints in '{run_name}'  ({weights_dir})")
    print()

    # Show epoch-by-epoch metrics from results.csv
    if results:
        print(f"  Training curves (from results.csv):")
        print(f"  {'Epoch':>6}  {'Train Loss':>12}  {'Val Loss':>10}  {'Val Acc':>9}  {'File exists?':>13}  {'Recommendation'}")
        print(f"  {'─'*6}  {'─'*12}  {'─'*10}  {'─'*9}  {'─'*13}  {'─'*20}")
        for ep_str, row in sorted(results.items(), key=lambda x: int(x[0])):
            ep_int  = int(ep_str)
            ep_disp = ep_int + 1       # display as 1-indexed
            tl      = float(row.get("train/loss", 0))
            vl      = float(row.get("val/loss", 0))
            va      = float(row.get("metrics/accuracy_top1", 0))
            ep_file = weights_dir / f"epoch{ep_int}.pt"
            exists  = "yes" if ep_file.exists() else "no (not saved)"
            rec     = "<-- lowest val/loss" if ep_str == recommend else ""
            print(f"  {ep_disp:>6}  {tl:>12.5f}  {vl:>10.5f}  {va:>9.4f}  {exists:>13}  {rec}")
        print()
        if recommend is not None:
            print(
                f"  HOW TO PICK: epoch with the lowest val/loss before it starts rising.\n"
                f"  Suggested: epoch{int(recommend)+1} (epoch{recommend}.pt)\n"
                f"  YOLO's best.pt = highest val accuracy checkpoint (usually a safe pick).\n"
                f"  Avoid last.pt — it's the final epoch and is often the most overfit.\n"
            )

    print(f"  {'File':<25}  {'Size':>8}")
    print(f"  {'─'*25}  {'─'*8}")
    for pt in pts:
        size_mb = pt.stat().st_size / 1_048_576
        print(f"  {pt.name:<25}  {size_mb:>7.2f} MB")
    print()


def publish(run_name: str, checkpoint: str, version: str, description: str) -> None:
    weights_dir = find_weights_dir(run_name)

    stem = checkpoint if not checkpoint.endswith(".pt") else checkpoint[:-3]
    src  = weights_dir / f"{stem}.pt"
    if not src.exists():
        raise FileNotFoundError(f"Checkpoint not found: {src}")

    dest_dir = BACKEND_DIR / version
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{stem}.pt"

    shutil.copy2(src, dest)
    print(f"Copied  {src}")
    print(f"     →  {dest}")

    rel_path = str(dest.relative_to(BACKEND_DIR.parent)).replace("\\", "/")
    config = {
        "version": version,
        "checkpoint": stem,
        "path": rel_path,
        "description": description or f"Run '{run_name}' — checkpoint '{stem}'",
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nactive_model.json updated:")
    print(json.dumps(config, indent=2))
    print(
        "\nThe backend will switch to this model on the next request "
        "(or call POST /ai/model/select with the same path to force an immediate reload)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a training checkpoint to the backend.")
    parser.add_argument("--run",         default="run2",  help="Run folder name (default: run2)")
    parser.add_argument("--checkpoint",  default="best",  help="Checkpoint stem: best | last | epoch5 | epoch10 … (default: best)")
    parser.add_argument("--version",     default="v2.0",  help="Version label for active_model.json (default: v2.0)")
    parser.add_argument("--description", default="",      help="Optional note about this checkpoint")
    parser.add_argument("--list",        action="store_true", help="List checkpoints + training metrics for --run and exit")
    args = parser.parse_args()

    if args.list:
        list_checkpoints(args.run)
        return

    publish(args.run, args.checkpoint, args.version, args.description)


if __name__ == "__main__":
    main()
