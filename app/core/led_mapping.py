"""Map spectrum bands onto perimeter LED indices (linear vs center-out)."""

from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

LayoutMode = Literal["linear", "center", "dual_monitor"]


def segment_centers(length: int, layout: LayoutMode) -> list[float]:
    """
    Peak positions along one edge (LED index, 0 = first LED on that edge).

    dual_monitor: two peaks on long edges (72) — one per screen; one peak on short edges (18).
    center: single peak in the middle of each edge.
    linear: empty (use left-to-right spectrum mapping).
    """
    if layout == "linear":
        return []
    if layout == "dual_monitor" and length >= 72:
        half = length // 2
        return [(half - 1) / 2.0, half + (half - 1) / 2.0]
    return [(length - 1) / 2.0]


def norm_distance_from_centers(position: int, length: int, centers: Sequence[float]) -> float:
    """0 at nearest center, 1 at the farthest LED on this edge."""
    dist = min(abs(position - c) for c in centers)
    max_dist = 0.0
    for j in range(length):
        max_dist = max(max_dist, min(abs(j - c) for c in centers))
    return dist / max(max_dist, 1e-6)


def band_level_hue_for_position(
    position: int,
    length: int,
    bands: np.ndarray,
    centers: Sequence[float],
    *,
    edge_gain: float = 1.0,
) -> tuple[float, float]:
    """
    Center-out mapping: bass/energy at centers, treble toward ends, brightness fades outward.
    """
    norm = norm_distance_from_centers(position, length, centers)
    inv = 1.0 - norm
    n_bands = len(bands)
    if n_bands <= 1:
        return float(bands[0]) * edge_gain, 0.0
    # Level from center (kicks) + local band (so edges still light up with their hue).
    band_level = int(inv * (n_bands - 1))
    band_hue = int(position * (n_bands - 1) / max(1, length - 1))
    center = float(bands[band_level]) * (0.12 + 0.7 * inv)
    local = float(bands[band_hue]) * 0.38
    level = max(center, local) * edge_gain
    hue = band_hue / (n_bands - 1)
    return level, hue


def band_level_hue_linear(
    position: int,
    length: int,
    bands: np.ndarray,
    *,
    band_index: int | None = None,
    edge_gain: float = 1.0,
) -> tuple[float, float]:
    """Legacy left-to-right (or indexed) mapping along the edge."""
    n_bands = len(bands)
    if band_index is None:
        band_index = int(position * (n_bands - 1) / max(1, length - 1))
    band_index = max(0, min(n_bands - 1, band_index))
    return float(bands[band_index]) * edge_gain, band_index / max(n_bands - 1, 1)
