"""
evaluate.py  —  run per-class accuracy diagnostics on any checkpoint.

Usage:
    python evaluate.py                              # uses default MODEL_PATH
    python evaluate.py --model runs/classify/run2/weights/epoch15.pt
    python evaluate.py --model runs/classify/run2/weights/best.pt --split val
    python evaluate.py --model runs/classify/run2/weights/last.pt  --split test
"""

import argparse
from collections import defaultdict
from pathlib import Path
from ultralytics import YOLO


DEFAULT_MODEL_PATH = "runs/classify/runs/classify/run1/weights/best.pt"
DATA_DIR           = "dataset/"


def _eval_split(model: YOLO, split_dir: Path) -> None:
    true_labels: list[str] = []
    pred_labels: list[str] = []
    correct_by_class: dict[str, int] = defaultdict(int)
    total_by_class:   dict[str, int] = defaultdict(int)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for cls_dir in sorted(split_dir.iterdir()):
        if not cls_dir.is_dir():
            continue
        true_cls = cls_dir.name
        images   = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.png"))

        for img_path in images:
            result   = model.predict(str(img_path), verbose=False)[0]
            pred_idx = result.probs.top1
            pred_cls = result.names[pred_idx]

            true_labels.append(true_cls)
            pred_labels.append(pred_cls)
            total_by_class[true_cls] += 1
            confusion[pred_cls][true_cls] += 1
            if pred_cls == true_cls:
                correct_by_class[true_cls] += 1

    all_classes = sorted(total_by_class.keys())
    total_imgs  = sum(total_by_class.values())
    total_corr  = sum(correct_by_class.values())
    overall_acc = total_corr / total_imgs if total_imgs > 0 else 0.0

    print(f"\nOverall accuracy: {overall_acc:.4f}  ({total_corr}/{total_imgs})")
    print(f"\n{'─' * 60}")
    print(f"Per-Class Breakdown")
    print(f"{'Class':<22} {'Acc':>8}  {'Correct':>8}  {'Total':>8}  Note")
    print(f"{'─' * 60}")

    suspicious = []
    poor       = []

    for cls in all_classes:
        total   = total_by_class[cls]
        correct = correct_by_class[cls]
        acc     = correct / total if total > 0 else 0.0

        if acc >= 0.999 and total > 0:
            note = "<-- SUSPICIOUS: perfect score"
            suspicious.append(cls)
        elif acc < 0.80:
            note = "<-- POOR"
            poor.append(cls)
        else:
            note = ""

        print(f"{cls:<22} {acc:>8.4f}  {correct:>8}  {total:>8}  {note}")

    print(f"{'─' * 60}")

    # Confusion matrix (rows = predicted, cols = actual)
    print(f"\nConfusion Matrix  (rows = predicted, cols = actual true class)")
    label  = "Pred / True"
    header = f"{label:<22}" + "".join(f"{c:>12}" for c in all_classes)
    print(header)
    for pred_cls in all_classes:
        row = f"{pred_cls:<22}" + "".join(
            f"{confusion[pred_cls][true_cls]:>12}" for true_cls in all_classes
        )
        print(row)

    # Diagnosis
    if suspicious:
        print(
            f"\n[OVERFITTING SIGNAL] Perfect score on: {suspicious}\n"
            "\n  Most likely causes (in order of probability):\n"
            "\n  1. Pre-computed static augmentation (preprocess.py)\n"
            "     _aug0/1/2.jpg files are identical every epoch — the model\n"
            "     memorises those exact pixels rather than learning invariance.\n"
            "     Fix: remove the pre-computed augmentation step; rely on YOLO's\n"
            "     built-in on-the-fly transforms (mosaic, hsv, fliplr, etc.).\n"
            "\n  2. Validation set too small (~60 images/class)\n"
            "     60 correct out of 60 is not statistically meaningful.\n"
            "     Fix: collect more data or use k-fold cross-validation.\n"
            "\n  3. Classes are visually trivial for a pretrained backbone\n"
            "     (not_human vs saudi_formal vs casual are very distinct).\n"
            "     A pretrained ImageNet model already encodes these features.\n"
            "\n  4. Possible identity leakage\n"
            "     If the same person/object appears across multiple source images\n"
            "     the model may have seen near-duplicate frames in both train and val.\n"
        )
    if poor:
        print(
            f"\n[UNDERFIT / CONFUSION] Low accuracy on: {poor}\n"
            "  Check the confusion matrix above to see which class they are\n"
            "  being confused with.\n"
        )
    if not suspicious and not poor:
        print("\n[OK] No suspicious or poor classes found — accuracy looks balanced.\n")


def evaluate(model_path: str, splits: list[str]) -> None:
    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"Model not found at '{model_path}'.\n"
            "Run train.py first, or pass --model <path>."
        )

    print(f"\nModel: {model_path}")
    model = YOLO(model_path)

    split_map = {"val": "valid", "test": "test"}
    for split_name in splits:
        split_dir = Path(DATA_DIR) / split_map[split_name]
        if not split_dir.exists():
            print(f"Skipping {split_name} — directory '{split_dir}' not found.")
            continue
        print(f"\n{'═' * 60}")
        print(f"  Evaluating split: {split_name.upper()}")
        print(f"{'═' * 60}")
        _eval_split(model, split_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a YOLO classification checkpoint.")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL_PATH,
        help="Path to the .pt checkpoint to evaluate (default: run1 best.pt)",
    )
    parser.add_argument(
        "--split", choices=["val", "test", "both"], default="both",
        help="Which split to evaluate (default: both)",
    )
    args = parser.parse_args()

    splits = ["val", "test"] if args.split == "both" else [args.split]
    evaluate(args.model, splits)


if __name__ == "__main__":
    main()
