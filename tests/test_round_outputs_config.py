import logging

import round_outputs


def test_load_config_missing_file(tmp_path, monkeypatch, caplog):
    missing = tmp_path / "obs_outputs.json"
    monkeypatch.setattr(round_outputs, "CONFIG_PATH", missing)
    with caplog.at_level(logging.WARNING):
        cfg = round_outputs._load_config()
    assert cfg == {}
    assert caplog.records[0].message == f"OBS outputs config file not found at {missing}"


def test_load_config_invalid_json(tmp_path, monkeypatch, caplog):
    invalid = tmp_path / "obs_outputs.json"
    invalid.write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr(round_outputs, "CONFIG_PATH", invalid)
    with caplog.at_level(logging.WARNING):
        cfg = round_outputs._load_config()
    assert cfg == {}
    assert caplog.records[0].message.startswith(
        f"Invalid JSON in OBS outputs config at {invalid}:"
    )
