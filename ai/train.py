from ultralytics import YOLO
from pathlib import Path

<<<<<<< HEAD
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
=======

MODEL_BASE   = "yolov8n-cls.pt"
DATA_DIR     = "dataset/"
EPOCHS       = 30   # more epochs so the val/train loss gap (overfitting signal) is visible
IMG_SIZE     = 224
BATCH        = 16
PROJECT      = "runs/classify"
RUN_NAME     = "run2"           # v2.0 — separate folder, keeps run1 intact
SAVE_PERIOD  = 5                # checkpoint every 5 epochs for manual selection


# ── Per-class accuracy callback ──────────────────────────────────────────────
# Runs after every training + validation cycle.
# Prints how accurate the model is on EACH class individually.
# A class that hits 100% early while others lag is a memorization signal.

def _per_class_accuracy(trainer):
    try:
        cm = getattr(trainer.validator, "confusion_matrix", None)
        if cm is None or cm.matrix is None:
            return

        matrix = cm.matrix          # shape (nc, nc) or (nc+1, nc+1) depending on YOLO version
        names  = trainer.data.get("names", {})
        # Use only the real named classes — YOLO sometimes adds a phantom background row
        nc     = len(names) if names else matrix.shape[0]
        epoch  = trainer.epoch + 1

        print(f"\n{'─' * 58}")
        print(f"Epoch {epoch:>3}  Per-Class Validation Accuracy")
        print(f"{'Class':<22} {'Acc':>8}  {'Correct':>8}  {'Total':>8}  Note")
        print(f"{'─' * 58}")

        suspicious = []
        underfit   = []

        for i in range(nc):
            total_actual = int(matrix[:, i].sum())   # all images whose true label = i
            correct      = int(matrix[i, i])          # correctly predicted as i
            acc          = correct / total_actual if total_actual > 0 else 0.0
            name         = names.get(i, str(i))

            if acc >= 0.999 and total_actual > 0:
                note = "<-- SUSPICIOUS: perfect score"
                suspicious.append(name)
            elif acc < 0.80:
                note = "<-- POOR: confused or underfit"
                underfit.append(name)
            else:
                note = ""

            print(f"{name:<22} {acc:>8.4f}  {correct:>8}  {total_actual:>8}  {note}")

        print(f"{'─' * 58}")

        if suspicious:
            print(
                f"\n[WARNING] Suspicious 100% accuracy on: {suspicious}\n"
                "  Likely causes:\n"
                "  1. Pre-computed augmented copies — model memorized static _aug*.jpg files.\n"
                "     Each epoch sees the exact same pixels; no true randomness per epoch.\n"
                "  2. Val set too small (60/class) — 60/60 correct ≠ genuine generalisation.\n"
                "  3. Classes are visually trivial for a pretrained backbone to separate.\n"
            )
        if underfit:
            print(
                f"\n[WARNING] Low accuracy on: {underfit}\n"
                "  Likely causes: too few samples, high intra-class variance, or class confusion.\n"
            )
        if not suspicious and not underfit:
            print("[OK] No suspicious classes detected this epoch.\n")

    except Exception as exc:
        print(f"[per_class_accuracy callback error]: {exc}")


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    if not Path(DATA_DIR).exists():
        raise FileNotFoundError(
            f"Dataset not found at '{DATA_DIR}'. Run preprocess.py first."
        )

    model = YOLO(MODEL_BASE)
    model.add_callback("on_fit_epoch_end", _per_class_accuracy)

>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0
    results = model.train(
        data=DATA_DIR,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
<<<<<<< HEAD
        patience=5,
=======
        patience=10,          # wider window so overfitting gap becomes visible
>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0
        project=PROJECT,
        name=RUN_NAME,
        exist_ok=True,
        verbose=True,
<<<<<<< HEAD
    )
    print(f"\nTraining complete. Best model: {PROJECT}/{RUN_NAME}/weights/best.pt")
    return results

=======
        save_period=SAVE_PERIOD,  # save epoch0/5/10/.../25.pt + best.pt + last.pt
        # ── Anti-overfitting ──────────────────────────────────────────────
        dropout=0.3,          # dropout on the classification head
        label_smoothing=0.1,  # soft labels — penalises overconfident logits (deprecated in YOLO 8.4+, still works)
        weight_decay=0.001,   # doubled L2 vs. YOLO default (0.0005)
        cos_lr=True,          # cosine decay is smoother than step decay
    )

    print(f"\nTraining complete. Best model: {PROJECT}/{RUN_NAME}/weights/best.pt")
    return results


>>>>>>> 0a855a0b120d022102947e6e8cda7bac455a71b0
if __name__ == "__main__":
    train()
