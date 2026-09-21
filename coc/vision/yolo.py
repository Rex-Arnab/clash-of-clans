"""Fast local defence detector: a public YOLOv5s run through OpenCV's DNN module.

Why this exists: `locate.py` answers "where are the Air Defenses" with 7 + N VLM calls,
~21 s and ~$0.010 per frame. This answers the same question for three classes in
~84 ms on the CPU, for free, at the same measured accuracy.

The weights are BurntBaseTeam/clash-of-clans-object-detection-api `best.pt` (YOLOv5s,
26 classes, trained 2023-06), exported to ONNX at 800 px, opset 12. The source repo has
NO license: fine for this private account, never redistribute the file.

Measured 2026-09-17 at IMGSZ 800 on 9 real-phone frames (6 enemy bases incl. one lava
skin and one mid-battle, own village x3), every box cropped and graded by eye (the AD
sheet also re-graded blind by a second reader, identical verdicts):

    class          conf >= 0.80    found at >= 0.80        0.25 - 0.80 band
    air_defense    27/27 true      27/30 (eye-checked)     3 true, 11 false
    x_bow          23/23 true      23 of 27 known          4 true,  6 false
    inferno_tower  24/25 true      24/27 (3 per frame)     3 true,  3 false

So `ACCEPT_CONF` is load-bearing: above it a box is trustworthy on its own (74/75),
below it two thirds are banners on poles, hero cards, the countdown text and UI
buttons. The one false accept was a Bomb Tower burning mid-battle, called inferno at
0.82. Misses are mostly cosmetic skins: lava-skin ADs scored 0.73 / 0.59 and lava
X-Bows 0.63 / 0.42 -- skins postdate the training data.

Deliberately NOT exposed, though the network has the classes:
  - `th`: 6/9 precise at >= 0.80; it names builder huts and pet houses Town Hall and has
    never seen TH16+ art.
  - `scatter`, `eagle`, `air_sweeper`: precise in the sample, recall never measured. On
    the live own-village frame scatter fired on 0 real Scattershots and its sub-0.25
    boxes were an X-Bow, a cannon and an archer tower.
  - Monolith, Spell Tower, Multi-Archer Tower, Ricochet Cannon, Firespitter: no class.

OpenCV DNN, not onnxruntime+CoreML: CoreML ran 12 ms but moved confidences by up to
0.16 against the graded torch model, which is enough to flip boxes across the 0.80
line the whole grading rests on. `cv2.dnn` reproduced 610/611 torch boxes (same class,
IoU > 0.9, max |dconf| 0.000) and cv2 is already a dependency.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

from .. import config

WEIGHTS = config.MODELS / "burnt_yolov5s_26cls.onnx"
WEIGHTS_SHA256 = "4a7eb030189c72b0a2dc2ae6a404bf6c612d0dcc3ede5935bc65f1e3f4411868"
IMGSZ = 800   # exported fixed size; 800 beat 640 on AD precision (27/27 vs 28/29)

# Output column order of the network, read from the .pt checkpoint.
NAMES = (
    "100", "air_def", "air_sweeper", "archer_tower", "army", "bomb_tower", "cannon",
    "cc", "champ", "dark_mine", "dark_storage", "eagle", "elx_mine", "elx_storage",
    "gold_mine", "gold_storage", "inferno", "king", "mortar", "pet", "queen", "scatter",
    "th", "warden", "wiz_tower", "xbow",
)
# Network class -> `locate.CLASS_MARKS` label. Only graded classes appear here.
EXPOSED = {"air_def": "air_defense", "xbow": "x_bow", "inferno": "inferno_tower"}

ACCEPT_CONF = 0.80    # at or above: 74/75 graded boxes true across the three classes
REVIEW_CONF = 0.25    # the export's own default; below it the graded tiles were noise
NMS_IOU = 0.45

# One cv2.dnn.Net is shared by the process, and setInput/forward is NOT thread-safe.
# Reproduced 2026-09-17 while diagnosing a9: 5 threads started together on 5 different
# views all got the SAME boxes back (37x5, then 115x5, then 27x5); calling the raw net
# the same way, 0/5 outputs matched sequential in 5 repeats, 5/5 with this lock. In a9
# itself the scan threads started >= 1.3 s apart (a pan between views) against a
# 0.17-0.30 s pass, so it most likely did not fire live -- a latent bug in any threaded
# caller, not a9's cause. Serialising the ~80 ms forward costs callers nothing visible.
_NET_LOCK = threading.Lock()


class YoloError(RuntimeError):
    """The detector cannot run as measured -- missing or altered weights."""


@dataclass(frozen=True)
class Box:
    """One detection in native 2392x1080 pixels, already mapped to a locate label."""

    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


@lru_cache(maxsize=1)
def _net() -> cv2.dnn.Net:
    """Load once per process. A file that is not the graded export is refused: every
    number in the module docstring belongs to that exact file."""
    if not WEIGHTS.exists():
        raise YoloError(f"missing detector weights: {WEIGHTS}")
    digest = hashlib.sha256(WEIGHTS.read_bytes()).hexdigest()
    if digest != WEIGHTS_SHA256:
        raise YoloError(f"{WEIGHTS.name} sha256 {digest[:12]}... is not the graded export")
    return cv2.dnn.readNetFromONNX(str(WEIGHTS))


def _letterbox(frame: np.ndarray) -> tuple[np.ndarray, float, int, int]:
    """YOLOv5's own letterbox (grey 114 padding, centred). A plain resize stretches the
    2.2:1 frame and was never graded."""
    h, w = frame.shape[:2]
    r = min(IMGSZ / h, IMGSZ / w)
    nw, nh = round(w * r), round(h * r)
    dw, dh = (IMGSZ - nw) / 2, (IMGSZ - nh) / 2
    img = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    top, bottom = round(dh - 0.1), round(dh + 0.1)
    left, right = round(dw - 0.1), round(dw + 0.1)
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT,
                             value=(114, 114, 114))
    return img, r, left, top


def detect(frame: np.ndarray, min_conf: float = REVIEW_CONF) -> list[Box]:
    """Exposed-class boxes at or above `min_conf`, best first.

    The default returns the review band too; callers that act on a box without a second
    look must filter to `ACCEPT_CONF` (see `accepted`).
    """
    img, r, left, top = _letterbox(frame)
    blob = np.ascontiguousarray(img[:, :, ::-1].transpose(2, 0, 1))[None]
    with _NET_LOCK:
        net = _net()
        net.setInput(blob.astype(np.float32) / 255.0)
        pred = net.forward()[0].copy()            # (N, 5 + 26): cx, cy, w, h, obj, cls...

    pred = pred[pred[:, 4] > min_conf]
    scores = pred[:, 5:] * pred[:, 4:5]
    cls = scores.argmax(1)
    conf = scores[np.arange(len(pred)), cls]
    keep = conf > min_conf
    pred, cls, conf = pred[keep], cls[keep], conf[keep]
    if not len(pred):
        return []
    xyxy = np.stack([pred[:, 0] - pred[:, 2] / 2, pred[:, 1] - pred[:, 3] / 2,
                     pred[:, 0] + pred[:, 2] / 2, pred[:, 1] + pred[:, 3] / 2], 1)
    # Per-class NMS via a class offset, as YOLOv5 does; the NMS runs over ALL 26 classes
    # before filtering so a banner that is more "cc" than "air_def" is suppressed exactly
    # as it was in the graded run.
    shifted = xyxy + cls[:, None] * 4096.0
    idx = cv2.dnn.NMSBoxes([[float(a), float(b), float(c - a), float(d - b)]
                            for a, b, c, d in shifted], conf.tolist(), min_conf, NMS_IOU)
    idx = np.array(idx, dtype=int).reshape(-1)

    fh, fw = frame.shape[:2]
    out = []
    for i in idx:
        label = EXPOSED.get(NAMES[int(cls[i])])
        if label is None:
            continue
        x1, y1, x2, y2 = xyxy[i]
        x1, x2 = (x1 - left) / r, (x2 - left) / r
        y1, y2 = (y1 - top) / r, (y2 - top) / r
        out.append(Box(label, float(conf[i]),
                       max(0, int(round(x1))), max(0, int(round(y1))),
                       min(fw, int(round(x2))), min(fh, int(round(y2)))))
    return sorted(out, key=lambda b: -b.confidence)


def accepted(boxes: list[Box]) -> list[Box]:
    return [b for b in boxes if b.confidence >= ACCEPT_CONF]
