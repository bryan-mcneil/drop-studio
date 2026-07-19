from studio.captions import active_caption, chunk_text, scene_captions


def test_chunks_respect_word_cap():
    chunks = chunk_text("The dock swallows seven to nine weeks of dirt before you touch a bag.")
    # normal chunks stay at <=4 words; a merged trailing orphan may reach 6
    assert all(len(c.split()) <= 6 for c in chunks)
    assert " ".join(chunks).replace("  ", " ").startswith("The dock swallows")


def test_no_orphan_trailing_chunk():
    chunks = chunk_text("The Roborock Q7 M5 Plus is a lesson in why.")
    assert len(chunks[-1].split()) >= 3


def test_chunks_split_on_punctuation():
    chunks = chunk_text("Stop paying list price. The Q7 is a lesson.")
    assert chunks[0] == "Stop paying list price."
    assert any(c.startswith("The Q7") for c in chunks)


def test_timeline_spans_vo_exactly():
    caps = scene_captions("one two three four five six seven eight", 10.0, 0.35, 4.0)
    assert abs(caps[0].start - 10.35) < 1e-6
    assert abs(caps[-1].end - 14.35) < 0.02
    for a, b in zip(caps, caps[1:]):
        assert abs(a.end - b.start) < 1e-6


def test_active_caption_lookup():
    caps = scene_captions("alpha beta gamma delta epsilon zeta", 0.0, 0.0, 3.0)
    assert active_caption(caps, 0.1) == caps[0].text
    assert active_caption(caps, 99.0) is None


def test_empty_vo_no_captions():
    assert scene_captions("", 0.0, 0.0, 3.0) == []
    assert scene_captions("hello there", 0.0, 0.0, 0.0) == []
