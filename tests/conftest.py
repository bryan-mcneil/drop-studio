import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

FIXTURES = REPO / "tests" / "fixtures"


@pytest.fixture(scope="session")
def sample_post():
    return json.loads((FIXTURES / "sample_post.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sample_price():
    return json.loads((FIXTURES / "sample_price.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sample_creative():
    return json.loads((FIXTURES / "sample_creative.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def demo_storyboard(sample_post, sample_price, sample_creative):
    from studio.storyboard import build

    return build(sample_post, images=[], price=sample_price, creative=sample_creative)


@pytest.fixture(scope="session")
def reference_context():
    from studio.golden import build_reference_context

    return build_reference_context()
