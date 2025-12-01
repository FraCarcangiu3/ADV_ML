import numpy as np

# Angle labels (4-way cardinal)
ANGLE_LABELS = ["n", "w", "s", "e"]
DEFAULT_DIST_LABELS = ["near", "medium", "far"]

# Map from standard order [N, E, S, W]
# to requested order [n, w, s, e].
STD_TO_ANGLE_CLASS = np.array([0, 3, 2, 1], dtype=np.int64)


def angle_deg_to_class(angles_deg):
    """
    Convert continuous angles (degrees) into 4 classes:
    n, w, s, e.
    """
    angles_deg = np.asarray(angles_deg, dtype=np.float32)
    shifted = np.mod(angles_deg + 45.0, 360.0)  # center sectors on cardinals
    sector = np.floor(shifted / 90.0).astype(int) % 4
    return STD_TO_ANGLE_CLASS[sector]


def get_distance_labels(num_bins: int):
    if num_bins == 2:
        return ["near", "far"]
    return DEFAULT_DIST_LABELS


def dist_to_class(dists, thresholds=None, num_bins=3):
    """
    Bucket distances into near/medium/far (or near/far if num_bins=2).

    thresholds: optional tuple (t1,) for 2 bins or (t1, t2) for 3 bins.
    If not provided uses median (2 bins) or 33/66 percentiles (3 bins).
    Returns (classes, thresholds_tuple).
    """
    dists = np.asarray(dists, dtype=np.float32)
    if thresholds is None:
        if num_bins == 2:
            t = np.median(dists)
            thresholds = (t,)
        else:
            q1, q2 = np.quantile(dists, [1 / 3, 2 / 3])
            thresholds = (q1, q2)
    else:
        thresholds = tuple(thresholds)
        if num_bins == 2 and len(thresholds) != 1:
            raise ValueError("For 2 bins provide one threshold (t1,).")
        if num_bins == 3 and len(thresholds) != 2:
            raise ValueError("For 3 bins provide two thresholds (t1, t2).")

    if num_bins == 2:
        classes = np.digitize(dists, thresholds, right=False).astype(int)
    else:
        q1, q2 = np.quantile(dists, [1 / 3, 2 / 3])
        classes = np.digitize(dists, thresholds, right=False).astype(int)
    return classes, thresholds
