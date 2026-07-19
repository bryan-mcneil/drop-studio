import pytest

from studio.voice import ESTIMATE_CHARS_PER_SEC, models_present, synthesize_scenes


def test_backend_none_estimates_durations(demo_storyboard, tmp_path):
    manifest = synthesize_scenes(demo_storyboard, tmp_path, backend="none")
    assert manifest["backend"] == "none"
    hook = demo_storyboard["scenes"][0]
    expected = len(hook["vo"]) / ESTIMATE_CHARS_PER_SEC
    assert abs(manifest["scenes"][0]["duration"] - expected) < 0.1
    assert (tmp_path / "manifest.json").is_file()


@pytest.mark.voice
@pytest.mark.skipif(not models_present(), reason="Kokoro models not downloaded")
def test_kokoro_synthesizes_speech(tmp_path):
    sb = {
        "slug": "test", "voice": {"backend": "kokoro", "voice": "am_michael", "speed": 1.0},
        "scenes": [{"type": "hook", "duration": 3.0, "text": "t", "vo": "This is a test."}],
    }
    manifest = synthesize_scenes(sb, tmp_path, backend="kokoro")
    assert manifest["backend"] == "kokoro"
    assert manifest["sample_rate"] == 24000
    scene = manifest["scenes"][0]
    assert 0.5 < scene["duration"] < 4.0
    assert (tmp_path / scene["wav"]).is_file()
