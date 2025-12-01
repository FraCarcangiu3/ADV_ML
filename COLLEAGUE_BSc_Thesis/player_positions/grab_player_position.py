#!/usr/bin/env python3

import os
import sys
import math
import csv
import shutil
from collections import deque
from pathlib import Path
import Quartz
import argparse
import time
from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
from datetime import datetime
from PIL import ImageGrab
from Quartz import (
    CGWindowListCreateImage,
    kCGWindowListOptionIncludingWindow,
    kCGWindowImageBoundsIgnoreFraming,
    CGRectInfinite,
)

# ANSI color helpers for console output
YELLOW = "\033[93m"
MAGENTA_BOLD = "\033[95;1m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Optional dependencies for image processing
try:
    import cv2
    import numpy as np
except Exception as e:
    cv2 = None
    np = None
    _IMPORT_ERR = e
    _IMPORT_INFO_PRINTED = False


# === Paths & constants ===

# Directory to save minimap screenshots (window-cropped exports)
path = 'Data/screenshots'
probe_path = os.path.join(path, "probe")
for _p in (path, probe_path):
    if not os.path.exists(_p):
        os.makedirs(_p)

WINDOW_SUBSTR = "assaultcube"
LABEL_CSV_DIR = Path("Data") / "csv" / "labels_csv"
MERGED_POLAR_CSV_DIR = Path("Data") / "csv" / "merged_samples_csv"
ALL_LABELS_CSV = MERGED_POLAR_CSV_DIR / "all_labels.csv"
TEMPLATE_PATH = Path("templates") / "red_arrow_32.png"
TEMPLATE_ROT_STEP = 5
TEMPLATE_SIZE = 64
TEMPLATE_SCORE_THRESHOLD = 0.30  # drop matches below this, altrimenti frame scartato
# Offset per allineare l'angolo del template al Nord=0° (template punta su = 0°)
TEMPLATE_HEADING_OFFSET = 0.0

# Broader HSV ranges to accommodate anti-aliased UI colors
RED_RANGES   = [((0,  80,  80), (10, 255, 255)), ((170, 80, 80), (179, 255, 255))]  # red wraps hue (tighter S/V to cut noise)
GREEN_RANGES = [((35, 60, 60), (90, 255, 255))]   # green

# Distance bands (absolute pixels)
MIN_DISTANCE_ABS = 5.0   # distanza minima attesa (px)
MAX_DISTANCE_ABS = 75.0  # distanza massima attesa (px)
POLAR_DISTANCE_BINS = max(1, int(os.environ.get("POLAR_DISTANCE_BINS", "5")))

# Polar transform controls (can be overridden via env)
POLAR_ROT_OFFSET_DEG = float(os.environ.get("POLAR_ROT_OFFSET_DEG", "0"))
POLAR_RADIUS_SCALE = float(os.environ.get("POLAR_RADIUS_SCALE", "1.0"))
MIN_COMPONENT_AREA_RATIO = 0.0050   # drop tiny blobs relative to minimap circle area
MIN_COMPONENT_AREA_ABS = 40         # absolute floor on blob area

try:
    MINIMAP_UPSCALE = max(1.0, float(os.environ.get("MINIMAP_UPSCALE", "5.0")))
except ValueError:
    MINIMAP_UPSCALE = 1.0

try:
    PLAYER_ANGLE_OFFSET = float(os.environ.get("PLAYER_ANGLE_OFFSET", "90.0"))
except ValueError:
    PLAYER_ANGLE_OFFSET = 90.0

try:
    ANGLE_CLASSIFY_OFFSET = float(os.environ.get("ANGLE_CLASSIFY_OFFSET", "0.0"))
except ValueError:
    ANGLE_CLASSIFY_OFFSET = 0.0

try:
    TIP_REFINE_WINDOW = int(os.environ.get("TIP_REFINE_WINDOW", "7"))
    if TIP_REFINE_WINDOW < 3:
        TIP_REFINE_WINDOW = 3
    if TIP_REFINE_WINDOW % 2 == 0:
        TIP_REFINE_WINDOW += 1
except ValueError:
    TIP_REFINE_WINDOW = 7

# Contour heuristics for arrow/triangle detection
ARROW_AREA_MIN_RATIO = 0.0012
ARROW_AREA_MAX_RATIO = 0.06
ARROW_MIN_SOLIDITY = 0.45
ARROW_APPROX_EPS_FACTOR = 0.08
MIN_CONTOUR_PIXELS = 30  # drop tiny blobs early

# Debug: save intermediate masks alongside the PNG when True
DEBUG_SAVE = True

# Minimap capture geometry (fractions of the game window)
# Crop leggermente più stretto per evitare testo in alto e bordi laterali
MINIMAP_WIDTH_RATIO = 0.11
MINIMAP_HEIGHT_RATIO = 0.16
MINIMAP_Y_OFFSET_RATIO = 0.08
MINIMAP_RIGHT_MARGIN_RATIO = 0.02
CIRCLE_RADIUS_FRAC = 0.52
CENTROID_OUTSIDE_TOL = 1.20
BLOB_CENTER_TOL = 0.90

# Arrow detection helpers
def _mask_hsv(img_hsv, ranges):
    """
    Create a mask for the given HSV image based on specified HSV color ranges.
    Combines multiple ranges using bitwise OR.
    """
    mask = None
    for (lo, hi) in ranges:
        lo_np = np.array(lo, dtype=np.uint8)
        hi_np = np.array(hi, dtype=np.uint8)
        cur = cv2.inRange(img_hsv, lo_np, hi_np)
        mask = cur if mask is None else (mask | cur)
    return mask


def _largest_centroid(mask):
    """
    Find the centroid of the largest contour in the binary mask.
    Returns None if no contours are found or if the centroid cannot be computed.
    """
    if cv2.countNonZero(mask) == 0:
        return None
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    cnt = max(cnts, key=cv2.contourArea)
    M = cv2.moments(cnt)
    if M["m00"] == 0:
        return None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return (cx, cy)


def _prepare_arrow_mask(hsv_img, ranges, circle_mask, kernel_open, kernel_close, kernel_dilate):
    """Isolate a HUD arrow by color and apply morphology to stabilise contours."""
    mask = _mask_hsv(hsv_img, ranges)
    mask = cv2.bitwise_and(mask, circle_mask)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    mask = cv2.dilate(mask, kernel_dilate, iterations=1)
    return mask


def _suppress_small_components(mask, min_area_px, keep_top=2):
    """Keep only the largest connected components above min_area_px to reduce speckle noise."""
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    order = np.argsort(areas)[::-1]
    out = np.zeros_like(mask)
    kept = 0
    for idx in order:
        area = areas[idx]
        if area < min_area_px:
            break
        label_id = idx + 1  # skip background
        out[labels == label_id] = 255
        kept += 1
        if kept >= keep_top:
            break
    return out if kept > 0 else mask


def _keep_primary_blob(mask, center_xy, radius, min_area_px):
    """
    Keep the largest contour above min_area_px and reasonably close to the center.
    """
    if cv2.countNonZero(mask) == 0:
        return mask
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return mask
    best = None
    cx, cy = center_xy
    max_offset = radius * BLOB_CENTER_TOL
    fallback = None
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area_px:
            continue
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        ccx = M["m10"] / M["m00"]
        ccy = M["m01"] / M["m00"]
        dist = math.hypot(ccx - cx, ccy - cy)
        if dist <= max_offset:
            if best is None or area > best[0]:
                best = (area, c)
        if fallback is None or area > fallback[0]:
            fallback = (area, c)
    chosen = best if best is not None else fallback
    if chosen is None:
        return np.zeros_like(mask)
    clean = np.zeros_like(mask)
    cv2.drawContours(clean, [chosen[1]], -1, 255, thickness=cv2.FILLED)
    return clean


def _make_template_base(size=TEMPLATE_SIZE):
    """Generate a synthetic triangular arrow template (tip up) to match HUD style."""
    size = int(size)
    size = max(16, size)
    canvas = np.zeros((size, size), dtype=np.uint8)
    w = size
    h = size
    tip = (w // 2, int(h * 0.08))
    left = (int(w * 0.18), int(h * 0.88))
    right = (int(w * 0.82), int(h * 0.88))
    pts = np.array([tip, right, left], dtype=np.int32)
    cv2.fillConvexPoly(canvas, pts, 255)
    canvas = cv2.GaussianBlur(canvas, (3, 3), 0)
    return canvas


def _normalize_template(tmpl, target_size=TEMPLATE_SIZE):
    """Crop to non-zero content, pad to square, and resize for consistent matching."""
    if tmpl is None or tmpl.size == 0:
        return None
    if tmpl.ndim == 3:
        tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(tmpl, 1, 255, cv2.THRESH_BINARY)
    nz = cv2.findNonZero(mask)
    if nz is None:
        return None
    x, y, w, h = cv2.boundingRect(nz)
    crop = tmpl[y:y + h, x:x + w]
    side = max(w, h)
    pad_x = (side - w) // 2
    pad_y = (side - h) // 2
    padded = cv2.copyMakeBorder(crop, pad_y, side - h - pad_y, pad_x, side - w - pad_x, cv2.BORDER_CONSTANT, value=0)
    resized = cv2.resize(padded, (target_size, target_size), interpolation=cv2.INTER_AREA)
    resized = cv2.GaussianBlur(resized, (3, 3), 0)
    return resized


def _ensure_templates():
    """Load and rotate the red arrow template once."""
    global _ROT_TEMPLATES
    if _ROT_TEMPLATES is not None:
        return
    tmpl = None
    if TEMPLATE_PATH.exists():
        tmpl = cv2.imread(str(TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        tmpl = _make_template_base()
    tmpl = _normalize_template(tmpl)
    if tmpl is None:
        tmpl = _make_template_base()
    h, w = tmpl.shape[:2]
    center = (w / 2.0, h / 2.0)
    rotations = []
    for ang in range(0, 360, TEMPLATE_ROT_STEP):
        M = cv2.getRotationMatrix2D(center, ang, 1.0)
        rot = cv2.warpAffine(tmpl, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
        rotations.append((ang, rot))
    _ROT_TEMPLATES = rotations


def _match_template_angle(patch_gray):
    """Return (best_angle, best_score) from template matching on the given patch."""
    _ensure_templates()
    if not _ROT_TEMPLATES:
        return None, None
    best_ang, best_score = None, -1.0
    for ang, tmpl in _ROT_TEMPLATES:
        if patch_gray.shape[0] < tmpl.shape[0] or patch_gray.shape[1] < tmpl.shape[1]:
            continue
        res = cv2.matchTemplate(patch_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(res)
        if score > best_score:
            best_score = score
            best_ang = ang
    return best_ang, best_score


def _refine_tip_subpixel(mask, tip_xy, window=None):
    """Refine the tip coordinate by averaging mask pixels in a local window (sub-pixel centroid)."""
    if window is None:
        window = TIP_REFINE_WINDOW
    if tip_xy is None or mask is None:
        return tip_xy
    x, y = int(tip_xy[0]), int(tip_xy[1])
    h, w = mask.shape[:2]
    if h == 0 or w == 0:
        return tip_xy
    half = max(1, window // 2)
    x0, x1 = max(0, x - half), min(w, x + half + 1)
    y0, y1 = max(0, y - half), min(h, y + half + 1)
    patch = mask[y0:y1, x0:x1]
    if patch.size == 0:
        return tip_xy
    ys_rel, xs_rel = np.nonzero(patch)
    if len(xs_rel) == 0:
        return tip_xy
    xs_abs = xs_rel + x0
    ys_abs = ys_rel + y0
    weights = patch[ys_rel, xs_rel].astype(float)
    denom = float(weights.sum())
    if denom <= 0.0:
        return tip_xy
    ref_x = float(np.dot(xs_abs, weights) / denom)
    ref_y = float(np.dot(ys_abs, weights) / denom)
    return (ref_x, ref_y)


def _extract_arrow_centroid(mask, radius, center_xy, area_scale=1.0):
    """Find a triangle-like contour and return its centroid, tip point, and debug metrics."""
    if cv2.countNonZero(mask) == 0:
        return None, None, None

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, None, None

    circle_area = math.pi * (radius ** 2) * max(0.01, float(area_scale))
    min_area = circle_area * ARROW_AREA_MIN_RATIO
    max_area = circle_area * ARROW_AREA_MAX_RATIO
    cx0, cy0 = center_xy

    best = None  # (score, centroid, meta, contour)
    for cnt in cnts:
        area = cv2.contourArea(cnt)
        if area <= 0 or area < min_area or area > max_area or area < MIN_CONTOUR_PIXELS:
            continue

        peri = cv2.arcLength(cnt, True)
        if peri == 0:
            continue

        approx = cv2.approxPolyDP(cnt, ARROW_APPROX_EPS_FACTOR * peri, True)
        vertex_count = len(approx)
        if vertex_count < 3 or vertex_count > 7:
            continue

        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull) or 1.0
        solidity = area / hull_area
        if solidity < ARROW_MIN_SOLIDITY:
            continue

        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        # Prefer contours closer to the minimap centre and with fewer vertices (triangles)
        dist_score = math.hypot(cx - cx0, cy - cy0)
        vertex_penalty = abs(vertex_count - 3) * 2.0
        score = dist_score + vertex_penalty

        if best is None or score < best[0]:
            best = (
                score,
                (float(cx), float(cy)),
                {
                    "area": round(area, 2),
                    "vertex_count": vertex_count,
                    "solidity": round(solidity, 3),
                    "perimeter": round(peri, 2),
                    "method": "triangle",
                },
                cnt,
            )

    if best is not None:
        centroid = best[1]
        cnt = best[3]
        pts = cnt.reshape(-1, 2)
        # Prefer tip with largest distance and acute corner (small internal angle)
        try:
            approx = cv2.approxPolyDP(cnt, ARROW_APPROX_EPS_FACTOR * cv2.arcLength(cnt, True), True).reshape(-1, 2)
        except Exception:
            approx = pts

        def _angle_score(p_prev, p, p_next):
            v1 = p_prev - p
            v2 = p_next - p
            dot = np.dot(v1, v2)
            denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) or 1.0
            ang = math.degrees(math.acos(max(-1.0, min(1.0, dot / denom))))
            return ang

        best_tip = None
        centroid_np = np.array(centroid, dtype=float)
        for i, p in enumerate(approx):
            p_prev = approx[i - 1]
            p_next = approx[(i + 1) % len(approx)]
            dist = np.linalg.norm(p - centroid_np)
            ang = _angle_score(p_prev, p, p_next)
            # Smaller angle + larger distance is better; strengthen angle penalty
            if ang <= 100.0:
                score = dist * 2.0 - ang
            else:
                score = dist - 0.5 * ang
            if best_tip is None or score > best_tip[0]:
                best_tip = (score, p)

        if best_tip is None:
            tip_idx = np.argmax(np.linalg.norm(pts - centroid_np, axis=1))
            tip = tuple(int(v) for v in pts[tip_idx])
        else:
            tip = tuple(int(v) for v in best_tip[1])
        tip = _refine_tip_subpixel(mask, tip)
        return centroid, best[2], tip

    # Fallback: return centroid of the largest contour if triangle heuristics failed
    fallback_centroid = _largest_centroid(mask)
    if fallback_centroid is None:
        return None, None, None

    largest_cnt = max(cnts, key=cv2.contourArea)
    fallback_area = cv2.contourArea(largest_cnt)
    fallback_perimeter = cv2.arcLength(largest_cnt, True)
    epsilon = ARROW_APPROX_EPS_FACTOR * fallback_perimeter if fallback_perimeter > 0 else ARROW_APPROX_EPS_FACTOR
    fallback_vertices = len(cv2.approxPolyDP(largest_cnt, epsilon, True))
    fallback_hull = cv2.contourArea(cv2.convexHull(largest_cnt)) or 1.0
    fallback_meta = {
        "area": round(fallback_area, 2),
        "vertex_count": fallback_vertices,
        "solidity": round(fallback_area / fallback_hull, 3),
        "perimeter": round(fallback_perimeter, 2),
        "method": "largest",
    }
    centroid = (float(fallback_centroid[0]), float(fallback_centroid[1]))
    tip_idx = np.argmax(np.linalg.norm(largest_cnt.reshape(-1, 2) - np.array(centroid), axis=1))
    tip = tuple(int(v) for v in largest_cnt.reshape(-1, 2)[tip_idx])
    tip = _refine_tip_subpixel(mask, tip)
    return centroid, fallback_meta, tip


ANGLE_MACRO_LABELS = ["north", "west", "south", "east"]
ANGLE_MICRO_LABELS = {
    "north": ["nne", "nn", "nnw"],  # swapped nne <-> nnw
    "west": ["wnw", "ww", "wsw"],
    "south": ["ssw", "ss", "sse"],
    "east": ["ese", "ee", "ene"],   # swapped ene <-> ese
}

ANGLE_MICRO_LIST = [lab for labs in ANGLE_MICRO_LABELS.values() for lab in labs]
DIST_MACRO_LABELS = ["near", "medium", "far"]
DIST_MICRO_PER_MACRO = 3
DIST_MICRO_LIST = [
    f"{macro}_{i + 1}"
    for macro in DIST_MACRO_LABELS
    for i in range(DIST_MICRO_PER_MACRO)
]
# Map every distance micro label back to its macro parent
DIST_MICRO_TO_MACRO = {micro: macro for macro in DIST_MACRO_LABELS for micro in DIST_MICRO_LIST if micro.startswith(macro)}
# Capture goals (defaults aim ~972 samples: 9 per angle×distance micro combo)
GOAL_PER_PAIR = int(os.environ.get("POSITION_GOAL_PER_PAIR", "9"))
_DEFAULT_GOAL_PER_ANGLE_MICRO = GOAL_PER_PAIR * len(DIST_MICRO_LIST)  # 9 * 9 = 81
_DEFAULT_GOAL_PER_DIST_MICRO = GOAL_PER_PAIR * len(ANGLE_MICRO_LIST)  # 9 * 12 = 108
GOAL_PER_MICRO = int(os.environ.get("POSITION_GOAL_PER_MICRO", str(_DEFAULT_GOAL_PER_ANGLE_MICRO)))
GOAL_PER_DIST_MICRO = int(os.environ.get("POSITION_GOAL_PER_DIST_MICRO", str(_DEFAULT_GOAL_PER_DIST_MICRO)))
GOAL_PER_DIST_MACRO = int(os.environ.get("POSITION_GOAL_PER_DIST", str(GOAL_PER_DIST_MICRO * DIST_MICRO_PER_MACRO)))  # 108*3=324
TOTAL_SAMPLE_GOAL = int(os.environ.get("POSITION_TOTAL_GOAL", str(GOAL_PER_PAIR * len(ANGLE_MICRO_LIST) * len(DIST_MICRO_LIST))))  # 972
# Central angles (degrees) for each micro sector, used to stabilize labels against jitter
ANGLE_MICRO_CENTERS = {
    "nnw": 120.0,  # swapped with nne
    "nn": 90.0,
    "nne": 60.0,
    "wnw": 150.0,
    "ww": 180.0,
    "wsw": 210.0,
    "ssw": 240.0,
    "ss": 270.0,
    "sse": 300.0,
    "ene": 30.0,   # swapped with ese
    "ee": 0.0,
    "ese": 330.0,
}
ANGLE_MICRO_TO_MACRO = {micro: macro for macro, micros in ANGLE_MICRO_LABELS.items() for micro in micros}
_LAST_ANGLE_DEG = None
_LAST_DIST_PX = None
_LAST_CB = None
_LAST_CG = None
_LAST_MICRO = None
_LAST_MACRO = None
_SMOOTH_CB = None
_SMOOTH_CG = None
_ANGLE_HISTORY = deque(maxlen=7)
_LAST_ARROW_DIR_DEG = None
_SMOOTH_DIST = None
_SMOOTH_ANGLE_VEC = None
_ROT_TEMPLATES = None
_IMPORT_INFO_PRINTED = False


def classify_angle(angle_deg):
    """
    Classify an angle into 4 macro directions (N, W, S, E) and 3 micro bins inside each macro.
    Uses nearest micro-sector center (every 30°) to reduce jitter near boundaries.
    """
    ang = angle_deg % 360.0

    def _circ_dist(a, b):
        d = abs(a - b) % 360.0
        return min(d, 360.0 - d)

    micro = min(ANGLE_MICRO_CENTERS.items(), key=lambda kv: _circ_dist(ang, kv[1]))[0]
    macro = ANGLE_MICRO_TO_MACRO[micro]
    return macro, micro


def classify_distance(dist_px, radius_px=None, max_distance_px=None, min_distance_px=None):
    """
    Classify pixel distance into 3 macro bands (near/medium/far) and 3 micro bins inside each macro (9 total).
    Thresholds split [MIN_DISTANCE_ABS, MAX_DISTANCE_ABS] uniformly into 9 slices to reduce class imbalance.
    """
    min_d = float(MIN_DISTANCE_ABS if min_distance_px is None else min_distance_px)
    max_d = float(MAX_DISTANCE_ABS if max_distance_px is None else max_distance_px)
    if max_d <= min_d:
        max_d = min_d + 1.0
    span = max_d - min_d
    t_near = min_d + span / 3.0
    t_mid = min_d + 2.0 * span / 3.0

    d_clamped = max(min_d, min(dist_px, max_d))
    total_bins = len(DIST_MACRO_LABELS) * DIST_MICRO_PER_MACRO
    bin_width = span / float(total_bins)
    # Bin index across the 9 uniform slices
    micro_idx = min(total_bins - 1, int((d_clamped - min_d) / max(bin_width, 1e-6)))
    macro_idx = micro_idx // DIST_MICRO_PER_MACRO
    macro = DIST_MACRO_LABELS[macro_idx]
    micro = DIST_MICRO_LIST[micro_idx]

    # Precompute macro and micro bin ranges for debugging/inspection
    macro_ranges = {
        "near": (min_d, t_near),
        "medium": (t_near, t_mid),
        "far": (t_mid, max_d),
    }
    micro_bins = {}
    for idx, micro_label in enumerate(DIST_MICRO_LIST):
        lo = min_d + idx * bin_width
        hi = min_d + (idx + 1) * bin_width
        micro_bins[micro_label] = (lo, hi if idx < total_bins - 1 else max_d)

    return macro, micro, {
        **macro_ranges,
        "micro_bins": micro_bins,
        "thresholds": {
            "near_max": t_near,
            "mid_max": t_mid,
            "max_dist": max_d,
        },
    }


def compute_centroid_distance(red_xy, green_xy):
    """
    Compute the vector and distance from the red centroid (reference) to the green centroid.
    Examples (dx, dy are green minus red):
      - red=(120,140), green=(160,110)  -> dx=40,  dy=-30, distance=50.00 px
      - red=(200,200), green=(170,260)  -> dx=-30, dy=60,  distance=67.08 px
      - red=(320,180), green=(355,180)  -> dx=35,  dy=0,   distance=35.00 px
    """
    bx, by = red_xy
    gx, gy = green_xy
    dx = float(gx) - float(bx)
    dy = float(gy) - float(by)
    return dx, dy, math.hypot(dx, dy)


def player_local_polar(red_center, red_tip, green_center, heading_dir_deg=None, angle_offset=PLAYER_ANGLE_OFFSET):
    """
    Compute player-local distance and angle from the red centroid to the green centroid.
    heading_dir_deg overrides the heading derived from the red tip when provided.
    angle_offset keeps the historical +90° convention used for sector labels.
    """
    rx, ry = red_center
    gx, gy = green_center
    dx = float(gx) - float(rx)
    dy = float(gy) - float(ry)
    dist = math.hypot(dx, dy)

    if heading_dir_deg is None:
        hx = float(red_tip[0]) - float(rx)
        hy = float(red_tip[1]) - float(ry)
        if math.hypot(hx, hy) < 1e-6:
            heading_dir_deg = 0.0
        else:
            heading_dir_deg = (math.degrees(math.atan2(-hy, hx)) + 360.0) % 360.0
    else:
        heading_dir_deg = heading_dir_deg % 360.0

    if dist > 0.0:
        target_dir_deg = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
    else:
        target_dir_deg = heading_dir_deg

    angle_deg = (target_dir_deg - heading_dir_deg + angle_offset) % 360.0
    return dist, angle_deg, {
        "heading_dir_deg": heading_dir_deg,
        "target_dir_deg": target_dir_deg,
    }


def print_distance_examples():
    """Print worked examples of centroid distance using the red centroid as origin."""
    samples = [
        {"red": (120, 140), "green": (160, 110)},
        {"red": (200, 200), "green": (170, 260)},
        {"red": (320, 180), "green": (355, 180)},
    ]
    print("Distance examples (origin = red centroid):")
    for sample in samples:
        dx, dy, dist = compute_centroid_distance(sample["red"], sample["green"])
        print(
            f"  red={sample['red']} -> green={sample['green']} | "
            f"dx={dx:.1f}, dy={dy:.1f}, distance={dist:.2f}px"
        )
    print("")


def _count_angle_distance_pair(labels_dir: Path, angle_micro: str, dist_micro: str) -> int:
    """
    Count how many samples already exist for the given (angle_micro, dist_micro) pair
    in the combined labels_{uuid}.csv files.
    """
    if not labels_dir.exists():
        return 0

    def _read_labels(csv_path: Path) -> tuple[str | None, str | None]:
        try:
            with open(csv_path, newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) < 2:
                    return (None, None)
                header = rows[0]
                data = rows[1]
                try:
                    a_idx = header.index("angle_micro")
                    d_idx = header.index("distance_micro")
                except ValueError:
                    # Fallback to positional columns if header missing
                    a_idx, d_idx = 0, 2 if len(data) > 2 else 0
                a_val = data[a_idx].strip() if a_idx < len(data) else None
                d_val = data[d_idx].strip() if d_idx < len(data) else None
                return (a_val, d_val)
        except Exception:
            return (None, None)

    count = 0
    for csv_path in labels_dir.glob("labels_*.csv"):
        a_val, d_val = _read_labels(csv_path)
        if a_val == angle_micro and d_val == dist_micro:
            count += 1
    return count


def _count_distance_macro(labels_dir: Path, dist_macro: str) -> int:
    """
    Count how many samples already exist for the given distance_macro
    in the labels_{uuid}.csv files.
    """
    if not labels_dir.exists():
        return 0

    def _read_label(csv_path: Path) -> str | None:
        try:
            with open(csv_path, newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) < 2:
                    return None
                header = rows[0]
                data = rows[1]
                try:
                    idx = header.index("distance_macro")
                except ValueError:
                    idx = 0
                return data[idx].strip() if idx < len(data) else None
        except Exception:
            return None

    count = 0
    for csv_path in labels_dir.glob("labels_*.csv"):
        if _read_label(csv_path) == dist_macro:
            count += 1
    return count


def _count_distance_micro(labels_dir: Path, dist_micro: str) -> int:
    """
    Count how many samples already exist for the given distance_micro
    in the labels_{uuid}.csv files.
    """
    if not labels_dir.exists():
        return 0

    def _read_label(csv_path: Path) -> str | None:
        try:
            with open(csv_path, newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) < 2:
                    return None
                header = rows[0]
                data = rows[1]
                try:
                    idx = header.index("distance_micro")
                except ValueError:
                    idx = 0
                return data[idx].strip() if idx < len(data) else None
        except Exception:
            return None

    count = 0
    for csv_path in labels_dir.glob("labels_*.csv"):
        if _read_label(csv_path) == dist_micro:
            count += 1
    return count


def _count_angle_micro(labels_dir: Path, angle_micro: str) -> int:
    """
    Count how many samples already exist for the given angle_micro
    in the labels_{uuid}.csv files.
    """
    if not labels_dir.exists():
        return 0

    def _read_label(csv_path: Path) -> str | None:
        try:
            with open(csv_path, newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) < 2:
                    return None
                header = rows[0]
                data = rows[1]
                try:
                    idx = header.index("angle_micro")
                except ValueError:
                    idx = 0
                return data[idx].strip() if idx < len(data) else None
        except Exception:
            return None

    count = 0
    for csv_path in labels_dir.glob("labels_*.csv"):
        if _read_label(csv_path) == angle_micro:
            count += 1
    return count


def _count_total_samples(labels_dir: Path) -> int:
    """Return how many labels_*.csv entries exist (one per UUID)."""
    if not labels_dir.exists():
        return 0
    return len(list(labels_dir.glob("labels_*.csv")))


def _warn_import_issue():
    """Print import diagnostics once when cv2/np are missing."""
    global _IMPORT_INFO_PRINTED
    if _IMPORT_INFO_PRINTED:
        return
    _IMPORT_INFO_PRINTED = True
    msg = f"cv2/np import failed under {sys.executable}"
    if '_IMPORT_ERR' in globals():
        msg += f" — error: {_IMPORT_ERR}"
    print(f"{YELLOW}[!] {msg}{RESET}")


def _parse_uuid_from_label(csv_path: Path) -> str | None:
    stem = csv_path.stem
    if stem.startswith("labels_"):
        return stem[len("labels_") :]
    return None


def _rewrite_all_labels_csv(labels_dir: Path, aggregate_csv: Path) -> None:
    """Rewrite aggregate all_labels.csv from current labels_*.csv files."""
    files = sorted(labels_dir.glob("labels_*.csv"))
    if not files:
        try:
            if aggregate_csv.exists():
                aggregate_csv.unlink()
        except Exception:
            pass
        return

    rows = []
    for csv_path in files:
        try:
            with open(csv_path, newline="") as f:
                data = list(csv.reader(f))
            if len(data) < 2:
                continue
            header, row = data[0], data[1]
            uuid = _parse_uuid_from_label(csv_path) or csv_path.stem
            def _get(name, default=None):
                try:
                    idx = header.index(name)
                    return row[idx]
                except ValueError:
                    return default
            rows.append([
                uuid,
                _get("distance_px"),
                _get("distance_macro"),
                _get("distance_micro"),
                _get("angle_deg"),
                _get("angle_macro"),
                _get("angle_micro"),
            ])
        except Exception:
            continue

    aggregate_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(aggregate_csv, "w", newline="") as f_all:
        writer = csv.writer(f_all)
        writer.writerow([
            "uuid",
            "distance_px",
            "distance_macro",
            "distance_micro",
            "angle_deg",
            "angle_macro",
            "angle_micro",
        ])
        writer.writerows(rows)


def prune_over_cap(labels_dir: Path, aggregate_csv: Path, screenshots_root: Path | None = None) -> list[str]:
    """
    Remove oldest labels_*.csv files that exceed caps (pair, micro angle, micro distance,
    macro distance, total). Keeps newest files. Rewrites aggregate CSV after pruning.
    Returns list of UUIDs removed.
    """
    if not labels_dir.exists():
        return []

    files = sorted(labels_dir.glob("labels_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    pair_cap = GOAL_PER_PAIR
    angle_cap = GOAL_PER_MICRO
    dist_micro_cap = GOAL_PER_DIST_MICRO
    dist_macro_cap = GOAL_PER_DIST_MACRO
    total_cap = TOTAL_SAMPLE_GOAL if TOTAL_SAMPLE_GOAL else None

    counts_pair = {}
    counts_angle = {}
    counts_dist_micro = {}
    counts_dist_macro = {}
    total = 0
    to_delete: list[tuple[Path, str | None]] = []

    for csv_path in files:
        try:
            with open(csv_path, newline="") as f:
                data = list(csv.reader(f))
            if len(data) < 2:
                to_delete.append((csv_path, _parse_uuid_from_label(csv_path)))
                continue
            header, row = data[0], data[1]
            def _get(name, default=None):
                try:
                    idx = header.index(name)
                    return row[idx]
                except ValueError:
                    return default
            angle_micro = _get("angle_micro")
            dist_micro = _get("distance_micro")
            dist_macro = _get("distance_macro")
            uuid = _parse_uuid_from_label(csv_path)
            if angle_micro is None or dist_micro is None or dist_macro is None:
                to_delete.append((csv_path, uuid))
                continue
        except Exception:
            to_delete.append((csv_path, _parse_uuid_from_label(csv_path)))
            continue

        pair = (angle_micro, dist_micro)
        keep = True
        if total_cap is not None and total >= total_cap:
            keep = False
        if counts_pair.get(pair, 0) >= pair_cap:
            keep = False
        if counts_angle.get(angle_micro, 0) >= angle_cap:
            keep = False
        if counts_dist_micro.get(dist_micro, 0) >= dist_micro_cap:
            keep = False
        if counts_dist_macro.get(dist_macro, 0) >= dist_macro_cap:
            keep = False

        if keep:
            counts_pair[pair] = counts_pair.get(pair, 0) + 1
            counts_angle[angle_micro] = counts_angle.get(angle_micro, 0) + 1
            counts_dist_micro[dist_micro] = counts_dist_micro.get(dist_micro, 0) + 1
            counts_dist_macro[dist_macro] = counts_dist_macro.get(dist_macro, 0) + 1
            total += 1
        else:
            to_delete.append((csv_path, uuid))

    removed_uuids: list[str] = []
    for csv_path, uid in to_delete:
        try:
            csv_path.unlink()
            removed_uuids.append(uid or csv_path.stem)
            print(f"{YELLOW}[~] Removed over-cap sample: {csv_path.name}{RESET}")
        except Exception:
            pass
        if uid and screenshots_root is not None:
            shot_dir = screenshots_root / f"minimap_{uid}"
            if shot_dir.exists():
                try:
                    shutil.rmtree(shot_dir)
                except Exception:
                    pass

    if removed_uuids:
        _rewrite_all_labels_csv(labels_dir, aggregate_csv)
    return removed_uuids


def analyze_minimap_pil(image_pil, debug_dir=None, debug_save=True):
    """
    Analyze a PIL image of the cropped minimap to detect red (reference) and green arrows.
    Returns macro/micro classes for angle (N/W/S/E) and distance (near/medium/far),
    plus centroids, vectors, and polar coordinates. Requires OpenCV and NumPy.
    """
    global _SMOOTH_CB, _SMOOTH_CG, _LAST_CB, _LAST_CG, _LAST_ANGLE_DEG, _LAST_DIST_PX, _LAST_MICRO, _LAST_MACRO, _ANGLE_HISTORY, _SMOOTH_DIST, _SMOOTH_ANGLE_VEC, _LAST_ARROW_DIR_DEG
    if cv2 is None or np is None:
        _warn_import_issue()
        return {
            "error": f"OpenCV/NumPy not available: {_IMPORT_ERR}",
        }

    out_dir = debug_dir if debug_dir is not None else path

    # Convert PIL (RGB) image to OpenCV BGR format
    img = np.array(image_pil)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    scale = MINIMAP_UPSCALE
    scale = 1.0 if scale < 1.0 else scale
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    scale_inv = 1.0 / scale

    # Light blur reduces aliasing/noise from UI edges before thresholding
    img = cv2.GaussianBlur(img, (3, 3), 0)

    # Convert BGR image to HSV color space
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    h, w = img.shape[:2]
    circle_mask = np.zeros((h, w), dtype=np.uint8)
    cx, cy = w // 2, h // 2
    radius = int(min(w, h) * CIRCLE_RADIUS_FRAC)
    cv2.circle(circle_mask, (cx, cy), radius, 255, -1)

    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    red_mask = _prepare_arrow_mask(hsv, RED_RANGES, circle_mask, k_open, k_close, k_dilate)
    area_scale = scale_inv * scale_inv
    min_comp_area = max(MIN_COMPONENT_AREA_ABS, int(math.pi * (radius ** 2) * MIN_COMPONENT_AREA_RATIO * area_scale))
    red_mask = _suppress_small_components(red_mask, min_comp_area, keep_top=1)
    red_mask = _keep_primary_blob(red_mask, (cx, cy), radius, min_comp_area)
    red_mask = cv2.medianBlur(red_mask, 3)
    cr, red_meta, red_tip = _extract_arrow_centroid(red_mask, radius, (cx, cy), area_scale=area_scale)
    if cr is None:
        red_mask_relaxed = _prepare_arrow_mask(
            hsv,
            [((0, 50, 50), (15, 255, 255)), ((160, 50, 50), (179, 255, 255))],
            circle_mask,
            k_open,
            k_close,
            k_dilate,
        )
        red_mask_relaxed = _suppress_small_components(red_mask_relaxed, min_comp_area, keep_top=1)
        red_mask_relaxed = _keep_primary_blob(red_mask_relaxed, (cx, cy), radius, min_comp_area)
        red_mask_relaxed = cv2.medianBlur(red_mask_relaxed, 3)
        cr, red_meta, red_tip = _extract_arrow_centroid(red_mask_relaxed, radius, (cx, cy), area_scale=area_scale)
        if cr is not None:
            red_mask = red_mask_relaxed

    green_mask = _prepare_arrow_mask(hsv, GREEN_RANGES, circle_mask, k_open, k_close, k_dilate)
    green_mask = _suppress_small_components(green_mask, min_comp_area, keep_top=2)
    green_mask = _keep_primary_blob(green_mask, (cx, cy), radius, min_comp_area)
    green_mask = cv2.medianBlur(green_mask, 3)
    cg, green_meta, green_tip = _extract_arrow_centroid(green_mask, radius, (cx, cy), area_scale=area_scale)
    if cg is None:
        green_mask_relaxed = _prepare_arrow_mask(
            hsv,
            [((25, 25, 25), (95, 255, 255))],
            circle_mask,
            k_open,
            k_close,
            k_dilate,
        )
        green_mask_relaxed = _suppress_small_components(green_mask_relaxed, min_comp_area, keep_top=2)
        green_mask_relaxed = _keep_primary_blob(green_mask_relaxed, (cx, cy), radius, min_comp_area)
        green_mask_relaxed = cv2.medianBlur(green_mask_relaxed, 3)
        cg, green_meta, green_tip = _extract_arrow_centroid(green_mask_relaxed, radius, (cx, cy), area_scale=area_scale)
        if cg is not None:
            green_mask = green_mask_relaxed

    if cr is None or cg is None:
        if DEBUG_SAVE:
            try:
                ts_fail = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
                cv2.imwrite(os.path.join(out_dir, f"debug_red_fail_{ts_fail}.png"), red_mask)
                cv2.imwrite(os.path.join(out_dir, f"debug_green_fail_{ts_fail}.png"), green_mask)
            except Exception:
                pass
        return {
            "error": "Coordinates not found"
        }

    # Fallback tips if missing
    if red_tip is None:
        red_tip = cr
    if green_tip is None:
        green_tip = cg

    # Use red centroid as reference for downstream computations
    cb = cr

    # Enforce shooter (green) stays near minimap center; otherwise fall back to last good
    # Shooter (green) can roam across the minimap; only clamp extreme outliers
    shooter_offset = math.hypot(cg[0] - cx, cg[1] - cy)
    max_shooter_offset = radius * 0.7  # allow up to near the edge
    if shooter_offset > max_shooter_offset and _LAST_CB and _LAST_CG:
        cr, cg = _LAST_CB, _LAST_CG
        shooter_offset = math.hypot(cg[0] - cx, cg[1] - cy)

    # Smooth centroids to reduce jitter
    alpha = 0.5
    if _SMOOTH_CB is not None and _SMOOTH_CG is not None:
        cr = (
            alpha * cr[0] + (1 - alpha) * _SMOOTH_CB[0],
            alpha * cr[1] + (1 - alpha) * _SMOOTH_CB[1],
        )
        cg = (
            alpha * cg[0] + (1 - alpha) * _SMOOTH_CG[0],
            alpha * cg[1] + (1 - alpha) * _SMOOTH_CG[1],
        )
    _SMOOTH_CB = cr
    _SMOOTH_CG = cg

    # If both centroids are essentially still, reuse last stable positions to avoid angle jitter
    if _LAST_CB and _LAST_CG:
        red_drift = math.hypot(cr[0] - _LAST_CB[0], cr[1] - _LAST_CB[1])
        green_drift = math.hypot(cg[0] - _LAST_CG[0], cg[1] - _LAST_CG[1])
        if red_drift < 1.5 and green_drift < 1.5:
            cr, cg = _LAST_CB, _LAST_CG

    # Drop if centroids wander outside the minimap circle
    if math.hypot(cb[0] - cx, cb[1] - cy) > radius * CENTROID_OUTSIDE_TOL:
        return {"error": "Red centroid outside minimap"}
    if math.hypot(cg[0] - cx, cg[1] - cy) > radius * CENTROID_OUTSIDE_TOL:
        return {"error": "Green centroid outside minimap"}

    # Reject large red jumps when green is stable (likely bad detection)
    red_center_offset = math.hypot(cb[0] - cx, cb[1] - cy)
    green_center_offset = math.hypot(cg[0] - cx, cg[1] - cy)
    if _LAST_CB and _LAST_CG:
        red_jump = math.hypot(cb[0] - _LAST_CB[0], cb[1] - _LAST_CB[1])
        green_jump = math.hypot(cg[0] - _LAST_CG[0], cg[1] - _LAST_CG[1])
        if red_jump > radius * 0.45 and green_jump < radius * 0.15:
            cb, cg = _LAST_CB, _LAST_CG
            red_center_offset = math.hypot(cb[0] - cx, cb[1] - cy)
            green_center_offset = math.hypot(cg[0] - cx, cg[1] - cy)
        # If both centroids jumped a lot, drop this frame
        if red_jump > radius * 0.6 and green_jump > radius * 0.4:
            return {"error": "Centroid jump too large"}

    # Compute distance from centroids (for distance classification)
    dx_bg, dy_bg, raw_dist = compute_centroid_distance(cb, cg)
    min_dist_px = MIN_DISTANCE_ABS * scale
    max_dist_px = MAX_DISTANCE_ABS * scale
    hard_cap = max_dist_px * 1.3  # beyond this is likely a bad detection
    if raw_dist > hard_cap:
        return {"error": f"Distance exceeds hard cap ({raw_dist:.1f} > {hard_cap:.1f})"}
    dist = max(min_dist_px, min(raw_dist, max_dist_px))
    clamped = not (abs(dist - raw_dist) < 1e-3)

    # Template-based angle (0° = punta verso l'alto) with tip fallback
    heading_from_tip_deg = (math.degrees(math.atan2(-(red_tip[1] - cb[1]), (red_tip[0] - cb[0]))) + 360) % 360
    arrow_dir_deg = heading_from_tip_deg
    template_score = None
    pad = 32  # patch half-size
    x0 = max(0, int(cb[0] - pad))
    y0 = max(0, int(cb[1] - pad))
    x1 = min(w, int(cb[0] + pad))
    y1 = min(h, int(cb[1] + pad))
    patch = red_mask[y0:y1, x0:x1]
    if patch.size > 0:
        best_ang, best_score = _match_template_angle(patch)
        if best_ang is not None and best_score is not None and best_score >= TEMPLATE_SCORE_THRESHOLD:
            arrow_dir_deg = (float(best_ang) + TEMPLATE_HEADING_OFFSET) % 360.0
            template_score = float(best_score)

    # Player-local polar angle without compass yaw (arrow defines heading)
    _, angle_deg, polar_meta = player_local_polar(cb, red_tip, cg, heading_dir_deg=arrow_dir_deg, angle_offset=PLAYER_ANGLE_OFFSET)
    target_dir_deg = polar_meta["target_dir_deg"]
    arrow_dir_deg = polar_meta["heading_dir_deg"]
    map_yaw = 0.0
    angle_macro = None
    angle_micro = None

    # Stabilise angle against sudden flips when the player stays still
    if _LAST_ANGLE_DEG is not None and _LAST_DIST_PX is not None and _LAST_CB and _LAST_CG:
        dist_delta = abs(dist - _LAST_DIST_PX)
        circ_diff = min(abs(angle_deg - _LAST_ANGLE_DEG) % 360.0, 360.0 - (abs(angle_deg - _LAST_ANGLE_DEG) % 360.0))
        centroid_shift = max(
            abs(cb[0] - _LAST_CB[0]),
            abs(cb[1] - _LAST_CB[1]),
            abs(cg[0] - _LAST_CG[0]),
            abs(cg[1] - _LAST_CG[1]),
        )
        # If positions barely moved but angle flipped hard, reuse last positions/angle/micro
        if dist_delta < 40.0 and centroid_shift < 20.0 and circ_diff > 60.0:
            cb, cg = _LAST_CB, _LAST_CG
            dx_bg, dy_bg, dist = compute_centroid_distance(cb, cg)
            target_dir_deg = (math.degrees(math.atan2(-dy_bg, dx_bg)) + 360) % 360
            if _LAST_ARROW_DIR_DEG is not None:
                arrow_dir_deg = _LAST_ARROW_DIR_DEG
            angle_deg = _LAST_ANGLE_DEG

    # Reject sudden large-distance drops (likely wrong blob) by reusing last labels/dist
    if _LAST_DIST_PX is not None and _LAST_MICRO is not None:
        dist_ratio = dist / max(1.0, _LAST_DIST_PX)
        centroid_shift = max(
            abs(cb[0] - (_LAST_CB[0] if _LAST_CB else cb[0])),
            abs(cb[1] - (_LAST_CB[1] if _LAST_CB else cb[1])),
            abs(cg[0] - (_LAST_CG[0] if _LAST_CG else cg[0])),
            abs(cg[1] - (_LAST_CG[1] if _LAST_CG else cg[1])),
        )
        if dist_ratio < 0.6 and centroid_shift > radius * 0.3:
            dist = _LAST_DIST_PX
            angle_deg = _LAST_ANGLE_DEG if _LAST_ANGLE_DEG is not None else angle_deg
            angle_micro = _LAST_MICRO
            angle_macro = _LAST_MACRO if _LAST_MACRO is not None else angle_macro
        # Reject very close red when previously far (shooter stays center)
        if red_center_offset < radius * 0.2 and _LAST_DIST_PX > radius * 0.7:
            dist = _LAST_DIST_PX
            angle_deg = _LAST_ANGLE_DEG if _LAST_ANGLE_DEG is not None else angle_deg
            angle_micro = _LAST_MICRO
            angle_macro = _LAST_MACRO if _LAST_MACRO is not None else angle_macro

    # Smooth distance and player-oriented angle to reduce jitter before final labels
    dist_smooth_alpha = 0.35
    angle_smooth_alpha = 0.30
    if _SMOOTH_DIST is not None:
        dist = dist_smooth_alpha * dist + (1.0 - dist_smooth_alpha) * _SMOOTH_DIST
    _SMOOTH_DIST = dist

    angle_rad = math.radians(angle_deg)
    angle_vec = (math.cos(angle_rad), math.sin(angle_rad))
    if _SMOOTH_ANGLE_VEC is not None:
        angle_vec = (
            angle_smooth_alpha * angle_vec[0] + (1.0 - angle_smooth_alpha) * _SMOOTH_ANGLE_VEC[0],
            angle_smooth_alpha * angle_vec[1] + (1.0 - angle_smooth_alpha) * _SMOOTH_ANGLE_VEC[1],
        )
    norm = math.hypot(angle_vec[0], angle_vec[1]) or 1.0
    angle_vec = (angle_vec[0] / norm, angle_vec[1] / norm)
    _SMOOTH_ANGLE_VEC = angle_vec
    angle_deg = (math.degrees(math.atan2(angle_vec[1], angle_vec[0])) + 360.0) % 360.0

    # Determine macro/micro labels for angle and distance after smoothing
    angle_deg = (angle_deg + ANGLE_CLASSIFY_OFFSET) % 360.0
    angle_macro, angle_micro = classify_angle(angle_deg)
    if _LAST_MICRO is not None and _LAST_MACRO is not None:
        centroid_shift = max(
            abs(cb[0] - _LAST_CB[0]) if _LAST_CB else 999,
            abs(cb[1] - _LAST_CB[1]) if _LAST_CB else 999,
            abs(cg[0] - _LAST_CG[0]) if _LAST_CG else 999,
            abs(cg[1] - _LAST_CG[1]) if _LAST_CG else 999,
        )
        if centroid_shift < 15.0:
            angle_micro = _LAST_MICRO
            angle_macro = _LAST_MACRO

    # Majority hysteresis over recent labels; if inconsistent and deltas small, drop frame
    _ANGLE_HISTORY.append(angle_micro)
    if _LAST_MICRO is not None and angle_micro != _LAST_MICRO:
        dist_delta = abs(dist - (_LAST_DIST_PX or dist))
        red_jump = math.hypot(cb[0] - (_LAST_CB[0] if _LAST_CB else cb[0]), cb[1] - (_LAST_CB[1] if _LAST_CB else cb[1]))
        green_jump = math.hypot(cg[0] - (_LAST_CG[0] if _LAST_CG else cg[0]), cg[1] - (_LAST_CG[1] if _LAST_CG else cg[1]))
        if dist_delta < radius * 0.2 and max(red_jump, green_jump) < radius * 0.2:
            return {"error": "Inconsistent angle with tiny movement; dropped"}
        if _ANGLE_HISTORY.count(angle_micro) < 4:
            angle_micro = _LAST_MICRO
            angle_macro = _LAST_MACRO

    _LAST_MICRO = angle_micro
    _LAST_MACRO = angle_macro
    radius_px = radius
    distance_macro, distance_micro, distance_bins = classify_distance(dist, radius_px, max_dist_px, min_dist_px)
    distance_bins_out = {}
    for key, val in distance_bins.items():
        if isinstance(val, tuple):
            distance_bins_out[key] = (val[0] * scale_inv, val[1] * scale_inv)
        elif isinstance(val, dict):
            scaled_dict = {}
            for k, v in val.items():
                if isinstance(v, tuple):
                    scaled_dict[k] = (v[0] * scale_inv, v[1] * scale_inv)
                elif isinstance(v, (int, float)):
                    scaled_dict[k] = v * scale_inv
                else:
                    scaled_dict[k] = v
            distance_bins_out[key] = scaled_dict
        else:
            distance_bins_out[key] = val
    raw_dx, raw_dy, raw_distance = compute_centroid_distance(cb, cg)

    _LAST_ANGLE_DEG = angle_deg
    _LAST_DIST_PX = dist
    _LAST_CB = cb
    _LAST_CG = cg
    _LAST_ARROW_DIR_DEG = arrow_dir_deg

    # Rescale metrics back to the original minimap resolution for reporting
    radius_out = radius_px * scale_inv
    cb_out = (cb[0] * scale_inv, cb[1] * scale_inv)
    cg_out = (cg[0] * scale_inv, cg[1] * scale_inv)
    red_tip_out = (red_tip[0] * scale_inv, red_tip[1] * scale_inv)
    dist_out = dist * scale_inv
    raw_distance_out = raw_distance * scale_inv
    raw_dx_out = raw_dx * scale_inv
    raw_dy_out = raw_dy * scale_inv
    span_abs = max(1.0, float(MAX_DISTANCE_ABS - MIN_DISTANCE_ABS))
    distance_rel = max(0.0, min(1.0, (dist_out - MIN_DISTANCE_ABS) / span_abs))

    # Polar coordinates (screen-based target angle) with optional rotation/scale applied
    polar_angle_deg = (target_dir_deg + POLAR_ROT_OFFSET_DEG) % 360.0
    polar_distance_px = raw_distance_out * POLAR_RADIUS_SCALE
    polar_norm = max(
        0.0,
        min(1.0, (polar_distance_px - MIN_DISTANCE_ABS) / max(1.0, (MAX_DISTANCE_ABS - MIN_DISTANCE_ABS) * POLAR_RADIUS_SCALE)),
    )

    # Player-oriented polar (red tip defines 0°, rotated +90° in our convention)
    player_polar_angle_deg = angle_deg
    player_polar_angle_norm = (player_polar_angle_deg % 360.0) / 360.0
    player_polar_distance_norm = max(0.0, min(1.0, (dist_out - MIN_DISTANCE_ABS) / max(1.0, (MAX_DISTANCE_ABS - MIN_DISTANCE_ABS))))
    # Uniform distance binning on normalized [0,1] for polar coordinates
    bin_count = POLAR_DISTANCE_BINS
    bin_width = 1.0 / bin_count
    distance_bin = min(bin_count - 1, int(player_polar_distance_norm / bin_width)) if bin_count > 0 else 0
    bin_lo = bin_width * distance_bin
    bin_hi = bin_lo + bin_width

    result_payload = {
        "distance": {
            "macro": distance_macro,
            "micro": distance_micro,
            "distance_px": round(dist_out, 2),
            "raw_distance_px": round(raw_distance_out, 2),
            "clamped": clamped,
            "normalized": round(distance_rel, 3),
            "bins_px": distance_bins_out,
        },
        "angle": {
            "macro": angle_macro,
            "micro": angle_micro,
            "angle_deg": round(angle_deg, 2),
            "arrow_dir_deg": round(arrow_dir_deg, 2),
            "template_score": round(template_score, 3) if template_score is not None else None,
            "target_dir_deg": round(target_dir_deg, 2),
            "relative_angle_deg": round((target_dir_deg - arrow_dir_deg) % 360.0, 2),
            "map_yaw_deg": round(map_yaw, 2),
            "classify_offset_deg": ANGLE_CLASSIFY_OFFSET,
        },
        "polar_coordinates": {
            "angle_deg_screen": round(target_dir_deg, 2),
            "angle_deg_transformed": round(polar_angle_deg, 2),
            "distance_px": round(polar_distance_px, 2),
            "distance_normalized": round(polar_norm, 3),
            "rotation_offset_deg": POLAR_ROT_OFFSET_DEG,
            "radius_scale": POLAR_RADIUS_SCALE,
        },
        "polar_player": {
            "angle_deg": round(player_polar_angle_deg, 2),
            "angle_normalized": round(player_polar_angle_norm, 3),
            "distance_px": round(dist_out, 2),
            "distance_normalized": round(player_polar_distance_norm, 3),
            "distance_bin": int(distance_bin),
            "distance_bin_range": [round(bin_lo, 3), round(bin_hi, 3)],
            "distance_bins_total": int(bin_count),
        },
        "relative_vector": {
            "dx": int(round(raw_dx_out)),
            "dy": int(round(raw_dy_out)),
            "dx_px": round(raw_dx_out, 2),
            "dy_px": round(raw_dy_out, 2),
            "distance_px": round(dist_out, 2),
            "raw_distance_px": round(raw_distance_out, 2),
        },
        "centroids": {
            "red": {"x": int(round(cb_out[0])), "y": int(round(cb_out[1]))},
            "green": {"x": int(round(cg_out[0])), "y": int(round(cg_out[1]))},
            "red_tip": {"x": int(round(red_tip_out[0])), "y": int(round(red_tip_out[1]))},
        },
        "centroids_raw": {
            "red": {"x": round(cb_out[0], 2), "y": round(cb_out[1], 2)},
            "green": {"x": round(cg_out[0], 2), "y": round(cg_out[1], 2)},
        },
        "contour_metrics": {
            "red": red_meta,
            "green": green_meta,
            "radius_px": int(round(radius_out)),
        },
    }

    if DEBUG_SAVE and debug_save:
        try:
            ts = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
            cv2.imwrite(os.path.join(out_dir, f"debug_red_{ts}.png"), red_mask)
            cv2.imwrite(os.path.join(out_dir, f"debug_green_{ts}.png"), green_mask)
        except Exception:
            pass

    return result_payload


# Helper to list all windows, limited to current Space only
def _all_windows():
    option = Quartz.kCGWindowListOptionOnScreenOnly
    return Quartz.CGWindowListCopyWindowInfo(option, Quartz.kCGNullWindowID)

def _front_to_back_window_ids():
    """Return window IDs ordered front-to-back for the current Space."""
    try:
        arr = Quartz.CGWindowListCreate(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
        return list(arr) if arr is not None else []
    except Exception:
        return []

def list_matching_windows(substr=WINDOW_SUBSTR):
    """
    List all windows whose title or owner name contains the given substring.
    Returns a list of matching window info dictionaries.
    """
    window_list = _all_windows()
    matches = []
    substr_lower = substr.lower()
    for window in window_list:
        name = window.get('kCGWindowName', '') or ''
        owner = window.get('kCGWindowOwnerName', '') or ''
        if substr_lower in name.lower() or substr_lower in owner.lower():
            bounds = window.get('kCGWindowBounds', None)
            matches.append({
                'kCGWindowNumber': window.get('kCGWindowNumber'),
                'pid': window.get('kCGWindowOwnerPID'),
                'layer': window.get('kCGWindowLayer'),
                'name': name,
                'owner': owner,
                'bounds': bounds,
                'window_info': window,
            })
    if not matches:
        return matches

    # Reorder matches by z-order (frontmost first) to prefer the active window on the current Space
    id_to_match = {m['kCGWindowNumber']: m for m in matches}
    ordered = [id_to_match[wid] for wid in _front_to_back_window_ids() if wid in id_to_match]
    seen = {m['kCGWindowNumber'] for m in ordered}
    for m in matches:
        if m['kCGWindowNumber'] not in seen:
            ordered.append(m)
    return ordered


def _cgimage_to_pil(cg_img):
    """Convert Quartz CGImageRef to PIL.Image (RGB)."""
    width = Quartz.CGImageGetWidth(cg_img)
    height = Quartz.CGImageGetHeight(cg_img)
    bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_img)
    data_provider = Quartz.CGImageGetDataProvider(cg_img)
    data = Quartz.CGDataProviderCopyData(data_provider)
    buf = bytes(data)
    from PIL import Image
    # macOS CGImage is typically premultiplied BGRA (little-endian)
    img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", bytes_per_row, 1)
    return img.convert("RGB")


def _capture_window_pil(window_number):
    """Return a PIL.Image of the window contents (not the screen), even if occluded."""
    cg_img = CGWindowListCreateImage(
        CGRectInfinite,
        kCGWindowListOptionIncludingWindow,
        window_number,
        kCGWindowImageBoundsIgnoreFraming,
    )
    if cg_img is None:
        return None
    return _cgimage_to_pil(cg_img)


def capture_minimap(index=None, match_substr=WINDOW_SUBSTR, activate=False, uuid=None, probe=False):
    """
    Capture a screenshot of the minimap region from a selected AssaultCube window.
    Saves the image and performs arrow analysis if OpenCV is available.
    Returns a dictionary with paths and analysis results.
    """
    matches = list_matching_windows(match_substr)
    if not matches:
        print(f"No windows matching '{match_substr}'.")
        return None

    target_window = None

    if index is not None:
        if 0 <= index < len(matches):
            target_window = matches[index]['window_info']
        else:
            print(f"Invalid index {index}.")
            return None
    else:
        # Default to first matching window if no index specified
        target_window = matches[0]['window_info']

    # Optionally activate the owning application and bring window to front
    if activate:
        pid = target_window.get('kCGWindowOwnerPID')
        try:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app:
                app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                time.sleep(0.5)
        except Exception:
            pass

    # Refresh bounds after potential activation/Space switch
    try:
        refreshed = [w for w in _all_windows() if w.get('kCGWindowOwnerPID') == target_window.get('kCGWindowOwnerPID')]
        if refreshed:
            target_window = refreshed[0]
    except Exception:
        pass

    # Capture the selected window independent of z-order
    win_id = target_window['kCGWindowNumber']
    window_img = _capture_window_pil(win_id)

    # Get window bounds (position on screen)
    bounds = target_window['kCGWindowBounds']
    window_x = bounds['X']
    window_y = bounds['Y']
    window_width = bounds['Width']
    window_height = bounds['Height']

    # Use the passed UUID or generate a new one if none is provided
    import uuid as _uuid_mod
    unique_id = uuid or str(_uuid_mod.uuid4())

    if not probe:
        shot_dir = os.path.join(path, f"minimap_{unique_id}")
        if not os.path.exists(shot_dir):
            os.makedirs(shot_dir)
        file_path = os.path.join(shot_dir, f"minimap_{unique_id}.png")
    else:
        shot_dir = probe_path
        file_path = os.path.join(probe_path, f"probe_{unique_id}.png")

    # Optionally dump full window for debugging
    if DEBUG_SAVE and window_img is not None and not probe:
        try:
            tsw = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
            window_img.save(os.path.join(shot_dir, f"_debug_window_{tsw}.png"))
        except Exception:
            pass

    # Increase the area to search for the minimap, expanding the capture region and anchoring to window bounds
    # The minimap is usually in the top-right; search a broader region anchored to the window's bounds.
    minimap_width = int(window_width * MINIMAP_WIDTH_RATIO)
    minimap_height = int(window_height * MINIMAP_HEIGHT_RATIO)
    minimap_y = int(window_y + window_height * MINIMAP_Y_OFFSET_RATIO)
    minimap_right = int(window_x + window_width - window_width * MINIMAP_RIGHT_MARGIN_RATIO)
    minimap_left = minimap_right - minimap_width

    # Clamp region within the window bounds to avoid grabbing outside pixels
    region_left = max(window_x, minimap_left)
    region_right = min(window_x + window_width, minimap_right)
    if region_right - region_left < minimap_width:
        region_left = max(window_x, region_right - minimap_width)
    region_top = max(window_y, minimap_y)
    region_bottom = min(window_y + window_height, region_top + minimap_height)
    if region_bottom - region_top < minimap_height:
        region_top = max(window_y, region_bottom - minimap_height)
    region = (region_left, region_top, region_right, region_bottom)
    image_pil = ImageGrab.grab(bbox=region)

    # Save the image
    image_pil.save(file_path)
    if probe:
        print(f"[PROBE] Minimap saved to {file_path}\n")
    else:
        print(f"Minimap saved to {file_path}  [mode: window-image]\n")

    # Perform analysis if OpenCV and NumPy are available
    if cv2 is not None and np is not None:
        # Prune older samples beyond caps before counting/saving
        pruned = prune_over_cap(LABEL_CSV_DIR, ALL_LABELS_CSV, screenshots_root=Path(path))
        if pruned:
            removed_list = ", ".join(pruned)
            print(f"{YELLOW}[~] Pruned {len(pruned)} old sample(s) to respect caps: {removed_list}{RESET}")

        result = analyze_minimap_pil(image_pil, debug_dir=shot_dir, debug_save=not probe)
        if "error" in result:
            err = result.get("error", "Coordinates not found")
            print(f"Analysis failed: {err}\n")
            return {"image": file_path, "error": err}

        if probe:
            bins = result.get("distance", {}).get("bins_px", {})
            micro_bins = bins.get("micro_bins", {})
            micro_str = " | ".join([f"{k}:{v[0]:.1f}-{v[1]:.1f}px" for k, v in micro_bins.items()]) if micro_bins else "n/a"
            print(
                f"[PROBE] angle macro={result['angle']['macro']} micro={result['angle']['micro']} | "
                f"distance macro={result['distance']['macro']} micro={result['distance']['micro']} | "
                f"polar angle={result.get('polar_player', {}).get('angle_deg')} "
                f"dist_norm={result.get('polar_player', {}).get('distance_normalized')} | "
                f"dist micro bins: {micro_str}"
            )
            return {
                "analysis": result,
                "image": file_path,
            }

        # Directory for combined CSV outputs
        for _dir in (LABEL_CSV_DIR, MERGED_POLAR_CSV_DIR):
            _dir.mkdir(parents=True, exist_ok=True)

        # Save centroids and player-local angle/distance with label bins
        angle_deg = result["angle"]["angle_deg"]
        angle_macro = result["angle"]["macro"]
        angle_micro = result["angle"]["micro"]
        dist_px = result["distance"]["distance_px"]
        dist_macro = result["distance"]["macro"]
        dist_micro = result["distance"]["micro"]
        c_red = result["centroids"]["red"]
        c_green = result["centroids"]["green"]
        c_tip = result["centroids"]["red_tip"]
        dist_micro_bins = result.get("distance", {}).get("bins_px", {}).get("micro_bins", {})

        # Enforce dataset balance caps
        dist_cap = GOAL_PER_DIST_MACRO
        dist_count = _count_distance_macro(LABEL_CSV_DIR, dist_macro)
        dist_micro_cap = GOAL_PER_DIST_MICRO
        dist_micro_count = _count_distance_micro(LABEL_CSV_DIR, dist_micro)
        angle_cap = GOAL_PER_MICRO
        angle_count = _count_angle_micro(LABEL_CSV_DIR, angle_micro)
        pair_cap = GOAL_PER_PAIR
        pair_count = _count_angle_distance_pair(LABEL_CSV_DIR, angle_micro, dist_micro)
        total_count = _count_total_samples(LABEL_CSV_DIR)

        reasons = []
        if pair_count >= pair_cap:
            reasons.append(f"pair cap reached: {angle_micro}/{dist_micro} = {pair_count}/{pair_cap}")
        if dist_count >= dist_cap:
            reasons.append(f"distance macro cap reached: {dist_macro} = {dist_count}/{dist_cap}")
        if dist_micro_count >= dist_micro_cap:
            reasons.append(f"distance micro cap reached: {dist_micro} = {dist_micro_count}/{dist_micro_cap}")
        if angle_count >= angle_cap:
            reasons.append(f"angle micro cap reached: {angle_micro} = {angle_count}/{angle_cap}")
        if TOTAL_SAMPLE_GOAL and total_count >= TOTAL_SAMPLE_GOAL:
            reasons.append(f"total samples cap reached: {total_count}/{TOTAL_SAMPLE_GOAL}")

        if reasons:
            print(f"{YELLOW}[!] Skipping save for UUID {unique_id} (pruned because cap reached): " + " | ".join(reasons) + RESET)
            try:
                os.remove(file_path)
            except Exception:
                pass
            return {"image": None, "skipped": True, "reason": reasons}
        else:
            # Print progress toward goals for this pair/micro/macro
            remaining_pair = max(0, pair_cap - pair_count - 1)  # include current save
            remaining_angle = max(0, angle_cap - angle_count - 1)
            remaining_dist_micro = max(0, dist_micro_cap - dist_micro_count - 1)
            remaining_dist_macro = max(0, dist_cap - dist_count - 1)
            remaining_total = max(0, TOTAL_SAMPLE_GOAL - total_count - 1) if TOTAL_SAMPLE_GOAL else None
            msg = (
                f"{BLUE}[→] Progress: pair {angle_micro}/{dist_micro} = {pair_count + 1}/{pair_cap} "
                f"(remaining {remaining_pair}); angle_micro {angle_micro} = {angle_count + 1}/{angle_cap} "
                f"(remaining {remaining_angle}); distance_micro {dist_micro} = {dist_micro_count + 1}/{dist_micro_cap} "
                f"(remaining {remaining_dist_micro}); distance_macro {dist_macro} = {dist_count + 1}/{dist_cap} "
                f"(remaining {remaining_dist_macro})"
            )
            if remaining_total is not None:
                msg += f"; total = {total_count + 1}/{TOTAL_SAMPLE_GOAL} (remaining {remaining_total})"
            print(msg + RESET)
            # If we just hit or exceeded caps, warn explicitly
            warn = []
            if pair_count + 1 > pair_cap:
                warn.append(f"pair {angle_micro}/{dist_micro} exceeded cap ({pair_count + 1}>{pair_cap}) and will be pruned")
            if dist_micro_count + 1 > dist_micro_cap:
                warn.append(f"distance micro {dist_micro} exceeded cap ({dist_micro_count + 1}>{dist_micro_cap})")
            if angle_count + 1 > angle_cap:
                warn.append(f"angle micro {angle_micro} exceeded cap ({angle_count + 1}>{angle_cap})")
            if dist_count + 1 > dist_cap:
                warn.append(f"distance macro {dist_macro} exceeded cap ({dist_count + 1}>{dist_cap})")
            if remaining_total is not None and total_count + 1 > TOTAL_SAMPLE_GOAL:
                warn.append(f"total samples exceeded cap ({total_count + 1}>{TOTAL_SAMPLE_GOAL})")
            if warn:
                print(f"{YELLOW}[!] New sample over cap, will be removed during pruning: " + " | ".join(warn) + RESET)

        # Write single CSV with centroids and numeric targets
        labels_csv_path = LABEL_CSV_DIR / f"labels_{unique_id}.csv"
        with open(labels_csv_path, "w", newline="") as f_labels:
            writer = csv.writer(f_labels)
            writer.writerow([
                "green_x", "green_y",
                "red_x", "red_y",
                "red_tip_x", "red_tip_y",
                "distance_px",
                "angle_deg",
                "angle_micro", "angle_macro",
                "distance_micro", "distance_macro",
            ])
            writer.writerow([
                c_green["x"], c_green["y"],
                c_red["x"], c_red["y"],
                c_tip["x"], c_tip["y"],
                dist_px,
                angle_deg,
                angle_micro, angle_macro,
                dist_micro, dist_macro,
            ])

        # Append to global CSV (one row per sample) so everything finisce in un unico CSV di default
        write_header = not ALL_LABELS_CSV.exists()
        with open(ALL_LABELS_CSV, "a", newline="") as f_all:
            writer = csv.writer(f_all)
            if write_header:
                writer.writerow([
                    "uuid",
                    "distance_px",
                    "distance_macro",
                    "distance_micro",
                    "angle_deg",
                    "angle_macro",
                    "angle_micro",
                ])
            writer.writerow([
                unique_id,
                dist_px,
                dist_macro,
                dist_micro,
                angle_deg,
                angle_macro,
                angle_micro,
            ])

        print(f"CSV labels saved to {labels_csv_path}")
        print(
            "Relative position (classified):\n"
            f"  angle_deg={angle_deg:.2f} ({angle_macro}/{angle_micro})  dist_px={dist_px:.2f} ({dist_macro}/{dist_micro})\n"
            f"  red=({c_red['x']},{c_red['y']}) tip=({c_tip['x']},{c_tip['y']}) green=({c_green['x']},{c_green['y']})\n"
        )
        if dist_micro_bins:
            micro_ranges = " | ".join([f"{k}:{v[0]:.1f}-{v[1]:.1f}px" for k, v in dist_micro_bins.items()])
            print(f"  distance micro bins: {micro_ranges}\n")
        if "centroids" in result:
            print(f"  centroids:        {result.get('centroids')}")
        if "relative_vector" in result:
            print(f"  relative_vector:  {result.get('relative_vector')}\n")
        if "polar_player" in result:
            pp = result["polar_player"]
            print(
                "  polar_player: "
                f"angle_deg={pp.get('angle_deg')} (norm={pp.get('angle_normalized')}) | "
                f"dist_px={pp.get('distance_px')} (norm={pp.get('distance_normalized')}, "
                f"bin={pp.get('distance_bin')}/{pp.get('distance_bins_total')} range={pp.get('distance_bin_range')})\n"
            )

        return {
            "image": file_path,
            "labels_csv": str(labels_csv_path),
            "analysis": result,
        }

    print("OpenCV/NumPy not installed. Skipping analysis.\n")
    _warn_import_issue()
    return {
        "image": file_path,
        "analysis": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture AssaultCube minimap and analyze arrow positions.")
    parser.add_argument("--list", action="store_true", help="List matching windows and exit")
    parser.add_argument("--index", type=int, default=None, help="Select window by index from the list")
    parser.add_argument("--match", type=str, default=WINDOW_SUBSTR, help="Substring to match in window title/owner")
    parser.add_argument("--activate", action="store_true", help="Bring selected window/app to front before capture")
    parser.add_argument("--timestamp", type=str, default=None, help="Use this timestamp (DD-MM-YYYY_HH-MM-SS) in output filenames (deprecated if --uuid is set)")
    parser.add_argument("--uuid", type=str, default=None, help="Use this UUID for output filenames (recommended)")
    parser.add_argument("--probe", action="store_true", help="Probe current angle/distance macro/micro without saving files")
    parser.add_argument("--distance-examples", action="store_true", help="Print distance examples using the red centroid as origin")
    args = parser.parse_args()

    if args.distance_examples:
        print_distance_examples()

    matches = list_matching_windows(substr=args.match)
    if not matches:
        print(f"No windows matching '{args.match}'.")
        raise SystemExit(1)

    # Display all matching windows with their index and details
    print("Matching windows:")
    for i, w in enumerate(matches):
        b = w['bounds'] or {}
        print(f"  [{i}] pid={w['pid']} layer={w['layer']}  #{w['kCGWindowNumber']} — {w['owner']} :: {w['name']}  "
              f"({b.get('Width','?')}x{b.get('Height','?')} at {b.get('X','?')},{b.get('Y','?')})")

    if args.list:
        raise SystemExit(0)

    sel_index = args.index
    uuid_arg = args.uuid
    ts_override = args.timestamp

    # If no UUID is provided, use timestamp as fallback for compatibility, but UUID is preferred
    if uuid_arg is None:
        if ts_override is not None:
            uuid_arg = ts_override
        else:
            import uuid as _uuid_mod
            uuid_arg = str(_uuid_mod.uuid4())

    # Auto-select if exactly one matching window is found and no --index provided
    if sel_index is None and len(matches) == 1:
        sel_index = 0
        b = matches[0]['bounds'] or {}
        print(
            "Auto-selected the only matching window:\n"
            f"  [0] #{matches[0]['kCGWindowNumber']} — {matches[0]['owner']} :: {matches[0]['name']}  "
            f"({b.get('Width','?')}x{b.get('Height','?')} at {b.get('X','?')},{b.get('Y','?')})\n"
        )

    # If multiple windows or no auto-selection, prompt the user
    if sel_index is None:
        try:
            sel_index = int(input("Index> ").strip())
        except Exception:
            print("Invalid selection.")
            raise SystemExit(2)

    capture_minimap(
        index=sel_index,
        match_substr=args.match,
        activate=args.activate,
        uuid=uuid_arg,
        probe=args.probe,
    )
