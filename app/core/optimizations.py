def smooth_color(prev, new, alpha=0.25):
    return (
        int(prev[0] + (new[0] - prev[0]) * alpha),
        int(prev[1] + (new[1] - prev[1]) * alpha),
        int(prev[2] + (new[2] - prev[2]) * alpha),
    )

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