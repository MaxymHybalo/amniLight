"""System audio (loopback) FFT → RGB LED array (same shape/order as ImageAnalysator)."""

from __future__ import annotations

import colorsys
import sys
from typing import Literal, overload

import numpy as np

from app.core.audio_config import (
    AudioPalette,
    AudioPulseConfig,
    AudioVizConfig,
    DEFAULT_AUDIO_PALETTE,
)
from app.core.image_analysator import (
    PERIM_BOTTOM,
    PERIM_LEFT,
    PERIM_RIGHT,
    PERIM_TOP,
)
from app.core.led_mapping import (
    LayoutMode,
    band_level_hue_for_position,
    band_level_hue_linear,
    norm_distance_from_centers,
    segment_centers,
)
from app.core.server import NUM_LEDS

DEFAULT_BLOCK_SIZE = 2048
AudioSource = Literal["loopback", "mic"]
DEFAULT_LAYOUT: LayoutMode = "dual_monitor"

# Log-band slices (0..71): bass kicks vs rap/vocal presence (hip-hop heavy low end).
_BASS_BANDS = slice(0, 14)
_VOCAL_BANDS = slice(14, 50)
_N_VOCAL_BANDS = _VOCAL_BANDS.stop - _VOCAL_BANDS.start

EdgeKind = Literal["side", "top", "bottom"]


def _palette_hue(mix: float, palette: AudioPalette = DEFAULT_AUDIO_PALETTE) -> float:
    """Map 0..1 into blue → purple → warm pink (HSV)."""
    mix = max(0.0, min(1.0, mix))
    if mix < 0.55:
        t = mix / 0.55
        return palette.hue_blue + t * (palette.hue_purple - palette.hue_blue)
    t = (mix - 0.55) / 0.45
    return palette.hue_purple + t * (palette.hue_pink - palette.hue_purple)


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return int(r * 255), int(g * 255), int(b * 255)


def _find_wasapi_loopback_index(pa: object, output_device_index: int | None) -> int:
    """Loopback input device that mirrors audio sent to the given (or default) output."""
    import pyaudiowpatch as pyaudio

    wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    if output_device_index is None:
        output_device_index = wasapi["defaultOutputDevice"]
    output = pa.get_device_info_by_index(output_device_index)
    output_name = output["name"]

    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if (
            info.get("isLoopbackDevice")
            and info["hostApi"] == wasapi["index"]
            and output_name in info["name"]
        ):
            return i

    raise RuntimeError(
        f"No WASAPI loopback device for output {output_name!r}. "
        "On Windows, install pyaudiowpatch; set Windows default playback device "
        "to the headphones/speakers you use."
    )


def _find_wasapi_mic_index(pa: object, device_index: int | None) -> int:
    import pyaudiowpatch as pyaudio

    if device_index is not None:
        return device_index
    wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    return wasapi["defaultInputDevice"]


class AudioAnalysator:
    """
    Capture audio and map spectrum to perimeter LED colors (RGB tuples).

    Default source is **loopback**: whatever is playing on your default playback
    device (headphones/speakers), not the microphone.
    """

    def __init__(
        self,
        *,
        num_leds: int = NUM_LEDS,
        source: AudioSource = "loopback",
        block_size: int = DEFAULT_BLOCK_SIZE,
        device: int | None = None,
        output_device: int | None = None,
        hue_span: float = 0.72,  # kept for API; palette uses _palette_hue() blue→pink
        attack: float = 0.1,
        decay: float = 0.018,
        peak_attack: float = 0.08,
        peak_decay: float = 0.02,
        hue_steps: int = 20,
        level_steps: int = 12,
        layout: LayoutMode = DEFAULT_LAYOUT,
        palette: AudioPalette = DEFAULT_AUDIO_PALETTE,
        pulses: AudioPulseConfig | None = None,
    ) -> None:
        if sys.platform != "win32":
            raise OSError(
                "System audio loopback is implemented for Windows (WASAPI). "
                "Use source='mic' on other platforms or add a loopback backend."
            )

        if num_leds != PERIM_LEFT + PERIM_TOP + PERIM_RIGHT + PERIM_BOTTOM:
            raise ValueError(f"Expected {NUM_LEDS} LEDs, got {num_leds}")

        import pyaudiowpatch as pyaudio

        self._num_leds = num_leds
        self._block_size = block_size
        self._hue_span = hue_span
        self._attack = attack
        self._decay = decay
        self._peak_attack = peak_attack
        self._peak_decay = peak_decay
        self._hue_steps = max(1, hue_steps)
        self._level_steps = max(1, level_steps)
        self._layout = layout
        self._palette = palette
        if pulses is None:
            pulses = AudioPulseConfig()
        self._pulses = pulses
        self._source = source
        self._peak_envelope = 1e-3
        self._bass_envelope = 0.0
        self._vocal_envelope = 0.0
        self._bass_pulse = 0.0
        self._vocal_pulse = 0.0
        self._vocal_ripple = 0.0
        self._vocal_peak_env = 1e-3
        self._vocal_display = np.zeros(_N_VOCAL_BANDS, dtype=np.float32)
        self._vocal_display_prev = np.zeros(_N_VOCAL_BANDS, dtype=np.float32)

        self._pa = pyaudio.PyAudio()
        if source == "loopback":
            input_index = _find_wasapi_loopback_index(self._pa, output_device or device)
        else:
            input_index = _find_wasapi_mic_index(self._pa, device)

        dev = self._pa.get_device_info_by_index(input_index)
        self._channels = min(2, int(dev["maxInputChannels"]))
        self._sample_rate = int(dev["defaultSampleRate"])

        self._samples = np.zeros(block_size, dtype=np.float32)
        self._window = np.hanning(block_size).astype(np.float32)
        self._band_levels = np.zeros(PERIM_TOP, dtype=np.float32)

        self._stream = self._pa.open(
            format=pyaudio.paFloat32,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            input_device_index=input_index,
            frames_per_buffer=block_size,
            stream_callback=self._on_audio,
        )
        self._stream.start_stream()

    @classmethod
    def from_config(cls, config: AudioVizConfig) -> AudioAnalysator:
        """Build analysator from ``config/audio_viz.json`` settings."""
        return cls(
            source=config.source,  # type: ignore[arg-type]
            block_size=config.block_size,
            attack=config.attack,
            decay=config.decay,
            peak_attack=config.peak_attack,
            peak_decay=config.peak_decay,
            hue_steps=config.hue_steps,
            level_steps=config.level_steps,
            layout=config.layout,
            palette=config.palette,
            pulses=config.pulses,
        )

    def _on_audio(
        self,
        in_data: bytes,
        _frame_count: int,
        _time_info: object,
        _status: int,
    ) -> tuple[None, int]:
        import pyaudiowpatch as pyaudio

        block = np.frombuffer(in_data, dtype=np.float32)
        if self._channels > 1:
            block = block.reshape(-1, self._channels).mean(axis=1)
        n = min(len(block), self._block_size)
        self._samples[:n] = block[:n]
        if n < self._block_size:
            self._samples[n:] = 0.0
        return None, pyaudio.paContinue

    def close(self) -> None:
        if self._stream.is_active():
            self._stream.stop_stream()
        self._stream.close()
        self._pa.terminate()

    def __enter__(self) -> AudioAnalysator:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @overload
    def analyse(self) -> list[tuple[int, int, int]]: ...

    @overload
    def analyse(self, _frame: np.ndarray) -> list[tuple[int, int, int]]: ...

    def analyse(self, _frame: np.ndarray | None = None) -> list[tuple[int, int, int]]:
        """
        Return one RGB tuple per LED in perimeter order (left → top → right → bottom).

        ``_frame`` is accepted but ignored so this can replace ``ImageAnalysator`` in main.
        """
        bands = self._update_spectrum_bands()
        return self._bands_to_perimeter_colors(bands)

    def _update_spectrum_bands(self) -> np.ndarray:
        windowed = self._samples * self._window
        spectrum = np.abs(np.fft.rfft(windowed))
        n_bins = len(spectrum)
        if n_bins < 2:
            return self._band_levels

        lo, hi = 1, n_bins - 1
        indices = np.unique(
            np.clip(
                np.logspace(np.log10(lo), np.log10(hi), PERIM_TOP).astype(int),
                lo,
                hi,
            )
        )
        if len(indices) != PERIM_TOP:
            positions = np.linspace(lo, hi, PERIM_TOP)
            raw = np.interp(positions, np.arange(n_bins), spectrum)
        else:
            raw = spectrum[indices]

        frame_peak = float(raw.max()) or 1e-6
        if frame_peak > self._peak_envelope:
            self._peak_envelope += self._peak_attack * (frame_peak - self._peak_envelope)
        else:
            self._peak_envelope += self._peak_decay * (frame_peak - self._peak_envelope)
        target = np.clip(raw / max(self._peak_envelope, 1e-6), 0.0, 1.0)

        rising = target > self._band_levels
        self._band_levels = np.where(
            rising,
            self._attack * target + (1.0 - self._attack) * self._band_levels,
            self._decay * target + (1.0 - self._decay) * self._band_levels,
        )
        self._update_energy_pulses(self._band_levels, raw)
        return self._band_levels

    def _update_energy_pulses(self, bands: np.ndarray, raw: np.ndarray) -> None:
        """Bass from normalized bands; vocals from raw mids (not drowned by 808/kick)."""
        bass_raw = float(np.max(bands[_BASS_BANDS]))

        self._bass_envelope = self._follow_envelope(
            bass_raw, self._bass_envelope, follow_up=0.22, follow_down=0.04
        )
        bass_spike = max(0.0, bass_raw - self._bass_envelope * 1.06)
        p = self._pulses
        self._bass_pulse = self._smooth_pulse(
            self._bass_pulse,
            bass_spike,
            attack=p.bass_attack,
            release=p.bass_release,
        )

        vocal_target, ripple_target = self._update_vocal_state(raw)
        self._vocal_pulse = self._smooth_pulse(
            self._vocal_pulse,
            vocal_target,
            attack=p.vocal_attack,
            release=p.vocal_release,
        )
        self._vocal_ripple = self._smooth_pulse(
            self._vocal_ripple,
            ripple_target,
            attack=p.ripple_attack,
            release=p.ripple_release,
        )

    def _update_vocal_state(self, raw: np.ndarray) -> tuple[float, float]:
        """Syllable hits only (no always-on glow); ripple for top-edge dance."""
        vocal_raw = raw[_VOCAL_BANDS]
        peak = float(np.max(vocal_raw)) or 1e-6
        if peak > self._vocal_peak_env:
            self._vocal_peak_env += 0.14 * (peak - self._vocal_peak_env)
        else:
            self._vocal_peak_env += 0.05 * (peak - self._vocal_peak_env)

        norm = np.clip(vocal_raw / max(self._vocal_peak_env, 1e-6), 0.0, 1.0)
        flux = np.maximum(0.0, norm - self._vocal_display_prev)
        self._vocal_display_prev = norm.copy()

        rising = norm > self._vocal_display
        self._vocal_display = np.where(
            rising,
            0.28 * norm + 0.72 * self._vocal_display,
            0.04 * norm + 0.86 * self._vocal_display,
        )

        energy = float(np.max(self._vocal_display))
        flux_hit = float(np.mean(flux))
        ripple_target = min(1.0, flux_hit * 5.5)
        if ripple_target < 0.06:
            ripple_target = 0.0

        self._vocal_envelope = self._follow_envelope(
            energy, self._vocal_envelope, follow_up=0.3, follow_down=0.07
        )
        spike = max(0.0, energy - self._vocal_envelope * 1.02)
        syllable = max(spike, flux_hit * 2.8)
        if syllable < 0.14:
            syllable = 0.0
        return min(1.0, syllable), ripple_target

    @staticmethod
    def _follow_envelope(
        raw: float, envelope: float, *, follow_up: float, follow_down: float
    ) -> float:
        rate = follow_up if raw > envelope else follow_down
        return envelope + rate * (raw - envelope)

    @staticmethod
    def _smooth_pulse(
        current: float, target: float, *, attack: float, release: float
    ) -> float:
        rate = attack if target > current else release
        return current + rate * (target - current)

    def _quantize(self, value: float, steps: int) -> float:
        if steps <= 1:
            return value
        return round(value * (steps - 1)) / (steps - 1)

    def _level_to_rgb(
        self, level: float, hue: float, *, saturation: float | None = None
    ) -> tuple[int, int, int]:
        p = self._palette
        level = max(0.0, float(level)) ** p.color_gamma
        level = self._quantize(level, self._level_steps)
        hue = self._quantize(hue, self._hue_steps)

        if level < p.dark_level_max:
            return (0, 0, 0)

        brightness = min(p.max_brightness, level * p.max_brightness)
        h = _palette_hue(hue, p)
        sat = p.saturation if saturation is None else saturation

        if self._vocal_pulse > 0.1:
            h_v = _palette_hue(p.vocal_pink_mix_lo + hue * 0.28, p)
            w = min(0.5, self._vocal_pulse * 0.55)
            h = h * (1.0 - w) + h_v * w
            sat = sat * (1.0 - w) + (p.vocal_sat + 0.15) * w
            brightness = min(p.max_brightness + 0.08, brightness + self._vocal_pulse * 0.1)
        elif self._bass_pulse > 0.1:
            h_b = _palette_hue(hue * 0.35, p)
            w = min(0.45, self._bass_pulse * 0.5)
            h = h * (1.0 - w) + h_b * w
            sat = sat * (1.0 - w) + p.bass_sat * w
            brightness = min(p.max_brightness + 0.06, brightness + self._bass_pulse * 0.08)

        return _hsv_to_rgb(h, sat, brightness)

    def _color_at(
        self,
        position: int,
        length: int,
        bands: np.ndarray,
        *,
        edge_gain: float = 1.0,
        band_index: int | None = None,
        edge: EdgeKind = "side",
    ) -> tuple[int, int, int]:
        centers = segment_centers(length, self._layout)
        if centers:
            level, hue = band_level_hue_for_position(
                position, length, bands, centers, edge_gain=edge_gain
            )
            inv = 1.0 - norm_distance_from_centers(position, length, centers)
            level = self._apply_energy_pulses(level, inv, position, length, edge)
        else:
            level, hue = band_level_hue_linear(
                position, length, bands, band_index=band_index, edge_gain=edge_gain
            )
            level = self._apply_energy_pulses(level, 0.5, position, length, edge)
        hue = self._hue_for_pulse(hue, edge)
        return self._level_to_rgb(level, hue, saturation=self._saturation_for_pulse())

    def _apply_energy_pulses(
        self,
        level: float,
        center_weight: float,
        position: int,
        length: int,
        edge: EdgeKind,
    ) -> float:
        cw = max(0.0, min(1.0, center_weight))
        side = 1.0 - cw
        bass = self._bass_pulse**0.92
        duck = 1.0 - min(0.8, bass * 1.25)
        vocal = max(0.0, self._vocal_pulse - 0.12) * duck

        level += bass * (0.5 + 1.35 * cw)
        level += vocal * (0.2 + 0.35 * cw + 0.25 * side)

        if edge == "top" and self._vocal_ripple > 0.1 and length > 1:
            vi = int(position * (_N_VOCAL_BANDS - 1) / (length - 1))
            ripple = float(self._vocal_display[vi])
            gate = (self._vocal_ripple - 0.08) * duck
            level += ripple * gate * (0.65 + 0.5 * side)

        return level

    def _saturation_for_pulse(self) -> float:
        return self._palette.saturation

    def _hue_for_pulse(self, hue: float, edge: EdgeKind) -> float:
        """Nudge hue toward blue (bass) or pink (vocals), keep spectrum variation."""
        bias = hue
        weight = 0.0
        if self._vocal_pulse > 0.12 and self._bass_pulse < 0.35:
            bias = 0.88 if edge == "top" else 0.72
            weight = min(0.35, self._vocal_pulse * 0.4)
        elif self._bass_pulse > 0.12:
            bias = 0.12
            weight = min(0.3, self._bass_pulse * 0.35)
        return hue * (1.0 - weight) + bias * weight

    def _bands_to_perimeter_colors(self, bands: np.ndarray) -> list[tuple[int, int, int]]:
        colors: list[tuple[int, int, int]] = []

        left_centers = segment_centers(PERIM_LEFT, self._layout)
        for i in range(PERIM_LEFT):
            if left_centers:
                colors.append(self._color_at(i, PERIM_LEFT, bands))
            else:
                idx = int(i * (len(bands) - 1) / max(1, PERIM_LEFT - 1))
                colors.append(self._color_at(i, PERIM_LEFT, bands, band_index=idx))

        for i in range(PERIM_TOP):
            colors.append(self._color_at(i, PERIM_TOP, bands, edge="top"))

        right_centers = segment_centers(PERIM_RIGHT, self._layout)
        for i in range(PERIM_RIGHT):
            if right_centers:
                colors.append(self._color_at(i, PERIM_RIGHT, bands))
            else:
                idx = len(bands) - 1 - int(i * (len(bands) - 1) / max(1, PERIM_RIGHT - 1))
                colors.append(self._color_at(i, PERIM_RIGHT, bands, band_index=idx))

        for i in range(PERIM_BOTTOM):
            colors.append(
                self._color_at(i, PERIM_BOTTOM, bands, edge_gain=0.65, edge="bottom")
            )

        if len(colors) != self._num_leds:
            raise RuntimeError(f"Expected {self._num_leds} colors, got {len(colors)}")
        return colors
