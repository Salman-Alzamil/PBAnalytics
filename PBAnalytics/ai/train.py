from ultralytics import YOLO
from pathlib import Path

MODEL_BASE  = "yolov8n-cls.pt"
DATA_DIR    = "dataset/"
EPOCHS      = 20
IMG_SIZE    = 224
BATCH       = 16
PROJECT     = "runs/classify"
RUN_NAME    = "run1"

def train():
    if not Path(DATA_DIR).exists():
        raise FileNotFoundError(f"Dataset not found at '{DATA_DIR}'. Run preprocess.py first.")

    model = YOLO(MODEL_BASE)
    results = model.train(
        data=DATA_DIR,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        patience=5,
        project=PROJECT,
        name=RUN_NAME,
        exist_ok=True,
        verbose=True,
    )
    print(f"\nTraining complete. Best model: {PROJECT}/{RUN_NAME}/weights/best.pt")
    return results

if __name__ == "__main__":
    train()
