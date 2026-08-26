from src.config import load_action_config


def test_load_action_config_defaults(monkeypatch):
    monkeypatch.setenv("INPUT_GITHUB-TOKEN", "gh-token")
    monkeypatch.setenv("INPUT_OPENAI-API-KEY", "sk-test")
    monkeypatch.delenv("INPUT_MODEL", raising=False)
    monkeypatch.delenv("INPUT_MIN-CONFIDENCE", raising=False)
    monkeypatch.delenv("INPUT_MIN-SEVERITY", raising=False)
    monkeypatch.delenv("INPUT_MAX-COMMENTS", raising=False)

    config = load_action_config()

    assert config.github_token == "gh-token"
    assert config.openai_api_key == "sk-test"
    assert config.model == "gpt-5-mini"
    assert config.min_confidence == 0.75
    assert config.min_severity == "medium"
    assert config.max_comments == 10


def test_load_action_config_custom_values(monkeypatch):
    monkeypatch.setenv("INPUT_GITHUB-TOKEN", "gh-token")
    monkeypatch.setenv("INPUT_OPENAI-API-KEY", "sk-test")
    monkeypatch.setenv("INPUT_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("INPUT_MIN-CONFIDENCE", "0.80")
    monkeypatch.setenv("INPUT_MIN-SEVERITY", "high")
    monkeypatch.setenv("INPUT_MAX-COMMENTS", "8")

    config = load_action_config()

    assert config.model == "gpt-4.1-mini"
    assert config.min_confidence == 0.80
    assert config.min_severity == "high"
    assert config.max_comments == 8


def test_load_action_config_rejects_bad_confidence(monkeypatch):
    monkeypatch.setenv("INPUT_GITHUB-TOKEN", "gh-token")
    monkeypatch.setenv("INPUT_OPENAI-API-KEY", "sk-test")
    monkeypatch.setenv("INPUT_MIN-CONFIDENCE", "2.5")

    try:
        load_action_config()
        assert False, "expected RuntimeError"
    except RuntimeError as error:
        assert "min-confidence" in str(error)


def test_load_action_config_rejects_bad_severity(monkeypatch):
    monkeypatch.setenv("INPUT_GITHUB-TOKEN", "gh-token")
    monkeypatch.setenv("INPUT_OPENAI-API-KEY", "sk-test")
    monkeypatch.setenv("INPUT_MIN-SEVERITY", "critical")

    try:
        load_action_config()
        assert False, "expected RuntimeError"
    except RuntimeError as error:
        assert "min-severity" in str(error)
