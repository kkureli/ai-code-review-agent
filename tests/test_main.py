import src.main as main


def test_get_pull_request_info():
    event = {
        "number": 42,
        "pull_request": {
            "base": {"sha": "base123"},
            "head": {"sha": "head456"},
        },
    }

    info = main.get_pull_request_info(event)

    assert info == {
        "pr_number": 42,
        "base_sha": "base123",
        "head_sha": "head456",
    }
