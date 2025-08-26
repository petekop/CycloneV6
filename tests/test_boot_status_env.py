from config.settings import settings
from routes import boot_status


def test_spawn_services_passes_env_and_cmd(monkeypatch):
    env_calls = []
    cmd_calls = []

    def fake_popen(cmd, *args, **kwargs):
        cmd_calls.append(cmd)
        env_calls.append(kwargs.get("env"))

        class Dummy:
            pass

        return Dummy()

    monkeypatch.setattr(boot_status.subprocess, "Popen", fake_popen)

    monkeypatch.setattr(
        boot_status,
        "load_boot_paths",
        lambda: {
            "hr_daemon": {"exe": "daemon_exe"},
            "mediamtx": {"exe": "mediamtx_exe"},
            "obs": {"script": "obs_script.sh"},
        },
    )

    token = "secret"
    monkeypatch.setenv("HR_DAEMON_TOKEN", token)
    services = {"hr_daemon": "WAIT", "mediamtx": "WAIT", "obs": "WAIT"}

    boot_status._spawn_services(services)

    env = env_calls[0]
    assert env["BASE_DIR"] == str(settings.BASE_DIR)
    assert env["HR_DAEMON_TOKEN"] == token

    assert cmd_calls == [["daemon_exe"], ["mediamtx_exe"], ["obs_script.sh"]]
