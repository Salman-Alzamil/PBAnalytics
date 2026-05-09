"""Cross-similarity test for the InsightFace buffalo_l pipeline.

Uses _get_app().get() directly and takes the largest detected face per
image. The detection-confidence filter is intentionally bypassed here
so we can measure recognition quality across the full test set even
when RetinaFace's det_score sits below the production threshold.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

import numpy as np  # noqa: E402

from utils.face_embeddings import _get_app, _pil_to_bgr  # noqa: E402

TEST_DIR = REPO / "test_imgs"
REF_NAME = "download.jfif"

SAME_PERSON = [
    ("download (1).jfif", "Ronaldo pose 1 (was 0.74)"),
    ("download (2).jfif", "Ronaldo pose 2 (was 0.57)"),
    ("download (3).jfif", "Ronaldo pose 3 (was 0.63)"),
    ("download (4).jfif", "Ronaldo pose 4 hardest (was 0.47)"),
    ("images.webp", "Ronaldo cheering (was 0.54)"),
    ("images (1).webp", "Ronaldo formal (was 0.58)"),
]
DIFFERENT_PERSON = [
    ("download (5).jfif", "Different person"),
    ("saudi-arabesque-saudi-men-traditional-dress.jpg", "Saudi traditional"),
    ("want-portrait-image-plain-dark-260nw-2521853183.webp", "Stock portrait"),
]


def _embed_largest(name: str):
    p = TEST_DIR / name
    if not p.exists():
        return None, 0.0, "missing"
    with open(p, "rb") as f:
        b = f.read()
    img = _pil_to_bgr(b)
    faces = _get_app().get(img)
    if not faces:
        return None, 0.0, "no face"
    best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return np.asarray(best.normed_embedding, dtype=np.float64), float(best.det_score), "ok"


def main() -> int:
    ref, ref_score, ref_state = _embed_largest(REF_NAME)
    if ref is None:
        print(f"FATAL: could not embed reference {REF_NAME}: {ref_state}")
        return 1
    print(f"Reference: {REF_NAME}  det_score={ref_score:.3f}")

    same_sims, diff_sims = [], []

    print()
    print("Same person (Ronaldo photos vs Aisha):")
    for fname, label in SAME_PERSON:
        e, score, state = _embed_largest(fname)
        if e is None:
            print(f"  {fname:30s}  --      [{state}]   ({label})")
            continue
        sim = float(np.dot(ref, e))
        same_sims.append(sim)
        flag = "" if score >= 0.80 else "  (det<0.80)"
        print(f"  {fname:30s}  {sim:+.4f}   det={score:.3f}{flag}   ({label})")

    print()
    print("Different people (should all be low):")
    for fname, label in DIFFERENT_PERSON:
        e, score, state = _embed_largest(fname)
        if e is None:
            print(f"  {fname:60s}  --      [{state}]   ({label})")
            continue
        sim = float(np.dot(ref, e))
        diff_sims.append(sim)
        flag = "" if score >= 0.80 else "  (det<0.80)"
        print(f"  {fname:60s}  {sim:+.4f}   det={score:.3f}{flag}   ({label})")

    print()
    print("=" * 70)
    if same_sims:
        print(f"Same-person  min={min(same_sims):+.4f}  median={np.median(same_sims):+.4f}  max={max(same_sims):+.4f}")
    if diff_sims:
        print(f"Different    min={min(diff_sims):+.4f}  median={np.median(diff_sims):+.4f}  max={max(diff_sims):+.4f}")
    if same_sims and diff_sims:
        gap = min(same_sims) - max(diff_sims)
        midpoint = (min(same_sims) + max(diff_sims)) / 2
        print(f"Gap (worst_same - worst_diff) = {gap:+.4f}")
        print(f"Suggested threshold (midpoint) = {midpoint:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
