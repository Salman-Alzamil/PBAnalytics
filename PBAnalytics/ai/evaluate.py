from ultralytics import YOLO
from pathlib import Path

MODEL_PATH = "runs/classify/runs/classify/run1/weights/best.pt"
DATA_DIR   = "dataset/"

def evaluate():
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(f"Model not found at '{MODEL_PATH}'. Run train.py first.")

    model  = YOLO(MODEL_PATH)
    splits = ["val", "test"]

    for split in splits:
        split_dir = Path(DATA_DIR) / ("valid" if split == "val" else split)
        if not split_dir.exists():
            print(f"  Skipping {split} — directory not found")
            continue
        results = model.val(data=DATA_DIR, split=split, imgsz=224, device="cpu", verbose=False)
        acc = results.results_dict.get("metrics/accuracy_top1", "N/A")
        print(f"{split:5s} accuracy: {acc}")

if __name__ == "__main__":
    evaluate()
