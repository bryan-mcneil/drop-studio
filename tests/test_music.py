import numpy as np

from studio.config import MIX_SAMPLE_RATE
from studio.music import pick_track, synth_bed


def test_synth_bed_shape_and_level():
    bed = synth_bed(5.0, seed=42)
    assert bed.shape == (5 * MIX_SAMPLE_RATE, 2)
    assert bed.dtype == np.float32
    peak = np.max(np.abs(bed))
    assert 0.05 < peak <= 0.6  # audible but headroomy
    assert np.max(np.abs(bed[: MIX_SAMPLE_RATE // 100])) < 0.05  # fade-in


def test_synth_bed_deterministic():
    a = synth_bed(2.0, seed=7)
    b = synth_bed(2.0, seed=7)
    assert np.array_equal(a, b)
    c = synth_bed(2.0, seed=8)
    assert not np.array_equal(a, c)


def test_pick_track_falls_back_to_synth():
    audio, provenance = pick_track(3.0, "some-slug")
    assert audio.shape[0] == 3 * MIX_SAMPLE_RATE
    assert "synth-bed" in provenance
