import logging  # for capturing warning logs in tests

from session_summary import load_tags


def test_load_tags_session_only(tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    (session / "events.csv").write_text(
        "\n".join(
            [
                "timestamp,type,tag,round,fighter",
                "2025-01-01 00:00:00,tag,Cross,round_1,Red",
            ]
        )
        + "\n"
    )

    assert load_tags(fighter_dir=session) == ["Cross"]


def test_load_tags_specific_round(tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    (session / "events.csv").write_text(
        "\n".join(
            [
                "timestamp,type,tag,round,fighter",
                "2025-01-01 00:00:00,tag,Jab,round_1,Red",
                "2025-01-01 00:00:01,tag,Hook,round_1,Red",
                "2025-01-01 00:00:02,tag,Uppercut,round_2,Red",
            ]
        )
        + "\n"
    )

    assert load_tags(session, "round_1") == ["Jab", "Hook"]


def test_load_tags_skips_bookmarks(tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    (session / "events.csv").write_text(
        "\n".join(
            [
                "timestamp,type,tag,round,fighter",
                "2025-01-01 00:00:00,tag,Cross,round_1,Red",
                "2025-01-01 00:00:01,bookmark,Pause,round_1,Red",
            ]
        )
        + "\n"
    )

    assert load_tags(session) == ["Cross"]


def test_load_tags_old_schema(tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    (session / "events.csv").write_text(
        "\n".join(
            [
                "timestamp,type,content,round_id,fighter_name",
                "2025-01-01 00:00:00,tag,Cross,round_1,Red",
            ]
        )
        + "\n"
    )

    assert load_tags(session) == ["Cross"]


def test_load_tags_missing_file_logs_warning(tmp_path, caplog):
    session = tmp_path / "session"
    session.mkdir()

    with caplog.at_level(logging.WARNING, logger="utils_checks"):
        assert load_tags(session) == []

    assert any("events.csv" in r.message for r in caplog.records)
