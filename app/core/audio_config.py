"""Load / save audio visualizer settings as JSON (backup & restore)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from app.core.led_mapping import LayoutMode

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "audio_viz.json"


@dataclass(frozen=True)
class AudioPalette:
    """Strip colors (blue → purple → pink). Serialized in config/audio_viz.json."""

    hue_blue: float = 0.53
    hue_purple: float = 0.76
    hue_pink: float = 0.93
    dark_level_max: float = 0.16
    max_brightness: float = 0.78
    color_gamma: float = 1.4
    saturation: float = 0.94
    vocal_pink_mix_lo: float = 0.72
    vocal_sat: float = 0.72
    bass_sat: float = 0.96


DEFAULT_AUDIO_PALETTE = AudioPalette()


@dataclass
class AudioOptimizeConfig:
    rise_alpha: float = 0.13
    fall_alpha: float = 0.05
    step: int = 6
    dark_threshold: int = 6


@dataclass
class AudioPulseConfig:
    bass_attack: float = 0.28
    bass_release: float = 0.011
    vocal_attack: float = 0.38
    vocal_release: float = 0.02
    ripple_attack: float = 0.45
    ripple_release: float = 0.038


@dataclass
class AudioVizConfig:
    """All tunable audio-viz settings (serializable to JSON)."""

    fps: int = 60
    layout: LayoutMode = "dual_monitor"
    source: str = "loopback"
    block_size: int = 2048
    attack: float = 0.1
    decay: float = 0.018
    peak_attack: float = 0.08
    peak_decay: float = 0.02
    hue_steps: int = 20
    level_steps: int = 12
    palette: AudioPalette = field(default_factory=AudioPalette)
    pulses: AudioPulseConfig = field(default_factory=AudioPulseConfig)
    optimize: AudioOptimizeConfig = field(default_factory=AudioOptimizeConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioVizConfig:
        palette_data = data.get("palette", {})
        palette_fields = {f.name for f in fields(AudioPalette)}
        palette = AudioPalette(
            **{k: palette_data[k] for k in palette_data if k in palette_fields}
        )
        pulses = AudioPulseConfig(**_subset(data.get("pulses", {}), AudioPulseConfig))
        optimize = AudioOptimizeConfig(
            **_subset(data.get("optimize", {}), AudioOptimizeConfig)
        )
        top = _subset(data, cls)
        top.pop("palette", None)
        top.pop("pulses", None)
        top.pop("optimize", None)
        return cls(palette=palette, pulses=pulses, optimize=optimize, **top)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _subset(data: dict[str, Any], dc_type: type) -> dict[str, Any]:
    names = {f.name for f in fields(dc_type)}
    return {k: v for k, v in data.items() if k in names}


def load_audio_viz_config(path: Path | str | None = None) -> AudioVizConfig:
    """Load config from JSON; missing file → built-in defaults."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        return AudioVizConfig()
    with config_path.open(encoding="utf-8") as f:
        return AudioVizConfig.from_dict(json.load(f))


def save_audio_viz_config(
    config: AudioVizConfig, path: Path | str | None = None
) -> Path:
    """Write config to JSON (pretty) for backup."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)
        f.write("\n")
    return config_path


def write_default_config_file(path: Path | str | None = None) -> Path:
    """Create config/audio_viz.json with current defaults if you need a fresh copy."""
    return save_audio_viz_config(AudioVizConfig(), path)
