def smooth_color(prev, new, alpha=0.25):
    return (
        int(prev[0] + (new[0] - prev[0]) * alpha),
        int(prev[1] + (new[1] - prev[1]) * alpha),
        int(prev[2] + (new[2] - prev[2]) * alpha),
    )


def smooth_color_asymmetric(
    prev: tuple[int, int, int],
    new: tuple[int, int, int],
    *,
    rise_alpha: float = 0.14,
    fall_alpha: float = 0.055,
) -> tuple[int, int, int]:
    """Slower blend when fading out than when lighting up."""
    alpha = rise_alpha if max(new) >= max(prev) else fall_alpha
    return smooth_color(prev, new, alpha=alpha)

def quantize_color(c, step=4):
    return tuple((channel // step) * step for channel in c)


def cut_dark_pixels(color: tuple[int, int, int], threshold: int = 10) -> tuple[int, int, int]:
    r, g, b = color
    if max(r, g, b) < threshold:
        return (0, 0, 0)
    return color

def normalize_color(c: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = c

    def fix(v: int) -> int:
        if v <= 2:
            return 0
        if v < 8:
            return 8
        return v

    return (fix(r), fix(g), fix(b))

def optimize_colors(old, new, alpha=0.25, step=4):
    filtered = []
    for prev, cur in zip(old, new):
        smoothed = smooth_color(prev, cur, alpha=alpha)
        quantized = quantize_color(smoothed, step=8)
        normalized = normalize_color(quantized)
        cut = cut_dark_pixels(normalized, threshold=60)
        filtered.append(cut)
    return filtered


def optimize_colors_audio_from_config(
    old: list[tuple[int, int, int]],
    new: list[tuple[int, int, int]],
    config: object,
) -> list[tuple[int, int, int]]:
    from app.core.audio_config import AudioOptimizeConfig

    if isinstance(config, AudioOptimizeConfig):
        return optimize_colors_audio(
            old,
            new,
            rise_alpha=config.rise_alpha,
            fall_alpha=config.fall_alpha,
            step=config.step,
            dark_threshold=config.dark_threshold,
        )
    return optimize_colors_audio(old, new)


def optimize_colors_audio(
    old: list[tuple[int, int, int]],
    new: list[tuple[int, int, int]],
    *,
    rise_alpha: float = 0.13,
    fall_alpha: float = 0.05,
    step: int = 6,
    dark_threshold: int = 6,
) -> list[tuple[int, int, int]]:
    """Smooth rise; slower fall so colors glide down to black."""
    filtered = []
    for prev, cur in zip(old, new):
        blended = smooth_color_asymmetric(
            prev, cur, rise_alpha=rise_alpha, fall_alpha=fall_alpha
        )
        blended = smooth_color_asymmetric(
            prev, blended, rise_alpha=rise_alpha, fall_alpha=fall_alpha
        )
        quantized = quantize_color(blended, step=step)
        filtered.append(cut_dark_pixels(quantized, threshold=dark_threshold))
    return filtered