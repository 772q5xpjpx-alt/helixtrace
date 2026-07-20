from types import SimpleNamespace

import pytest

from dna_trace_reconstruction.ai_analyst import (
    DEFAULT_MODEL,
    analyze_experiment,
    has_openai_api_key,
    interpret_experiment_locally,
)
from dna_trace_reconstruction.pipeline import run_experiment


def test_api_key_detection_does_not_require_environment(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert not has_openai_api_key()
    assert has_openai_api_key("test-key")


def test_analyze_experiment_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_experiment("ACGTACGT", cluster_size=1, seed=1)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        analyze_experiment(result)


def test_analyze_experiment_calls_gpt_56_responses_api(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="### Verdict\nThe experiment is interpretable.")

    class FakeOpenAI:
        def __init__(self, *, api_key):
            captured["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    result = run_experiment("ACGTACGT", cluster_size=1, seed=1)

    analysis = analyze_experiment(result, api_key="secret-test-key")

    assert analysis.startswith("### Verdict")
    assert captured["model"] == DEFAULT_MODEL == "gpt-5.6"
    assert captured["reasoning"] == {"effort": "low"}
    assert captured["store"] is False
    assert captured["safety_identifier"] == "helixtrace-local-demo"
    assert "post-hoc local search" in captured["input"]


def test_local_interpretation_is_complete_and_free(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_experiment("ACGTACGT", cluster_size=3, seed=1)

    analysis = interpret_experiment_locally(result)

    assert "### Verdict" in analysis
    assert "### Evidence" in analysis
    assert "### Reliability warning" in analysis
    assert "### Next experiment" in analysis
