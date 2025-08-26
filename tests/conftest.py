import sys
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib  # noqa: E402
import os  # noqa: E402
import types  # noqa: E402

import pytest  # noqa: E402

from boot_state import set_boot_state  # noqa: E402

os.environ.setdefault("BASE_DIR", str(ROOT))
os.environ.setdefault("OBS_WS_URL", "ws://127.0.0.1:4455")
os.environ.setdefault("OBS_WS_PASSWORD", "changeme")
os.environ.setdefault("CYCLONE_DEFER_OBS_INIT", "1")
os.environ.setdefault("MEDIAMTX_PATH", str(ROOT / "mediamtx.yml"))


@pytest.fixture(autouse=True, scope="session")
def _disable_autostart_for_tests():
    os.environ.setdefault("CYCLONE_AUTOSTART", "0")


FightControl = types.ModuleType("FightControl")
# Provide the real package path so ``importlib`` can resolve submodules like
# ``FightControl.round_manager``.  The test-suite originally stubbed the
# module, however a number of tests expect the actual ``RoundManager``
# implementation to be importable via ``from FightControl.round_manager import
# RoundManager``.  Import the real module here and expose the public classes on
# the lightweight ``FightControl`` namespace so downstream imports succeed.
FightControl.__path__ = [str(ROOT / "FightControl")]
sys.modules.setdefault("FightControl", FightControl)

rm_module = importlib.import_module("FightControl.round_manager")
FightControl.RoundManager = rm_module.RoundManager
FightControl.RoundState = rm_module.RoundState
FightControl.round_status = rm_module.round_status
sys.modules["FightControl.round_manager"] = rm_module

from pathlib import Path  # noqa: E402

fighter_paths_stub = types.ModuleType("FightControl.fighter_paths")
fighter_paths_stub.BASE_DIR = Path(".")
fighter_paths_stub.bout_dir = lambda *a, **k: Path(".")
fighter_paths_stub.round_dir = lambda *a, **k: Path(".")
fighter_paths_stub.summary_dir = lambda *a, **k: Path(".")
fighter_paths_stub.fight_bout_dir = lambda *a, **k: Path(".")
fighter_paths_stub.fight_round_dir = lambda *a, **k: Path(".")
fighter_paths_stub.refresh_base_dir = lambda: None
sys.modules.setdefault("FightControl.fighter_paths", fighter_paths_stub)

fight_utils_stub = types.ModuleType("FightControl.fight_utils")
fight_utils_stub.safe_filename = lambda *a, **k: ""
fight_utils_stub.parse_round_format = lambda *a, **k: None
sys.modules.setdefault("FightControl.fight_utils", fight_utils_stub)

create_fighter_round_folders_stub = types.ModuleType("FightControl.create_fighter_round_folders")
create_fighter_round_folders_stub.create_round_folder_for_fighter = lambda *a, **k: None
sys.modules.setdefault("FightControl.create_fighter_round_folders", create_fighter_round_folders_stub)

play_sound_stub = types.ModuleType("FightControl.play_sound")
play_sound_stub.play_audio = lambda *a, **k: None
sys.modules.setdefault("FightControl.play_sound", play_sound_stub)

# Minimal websockets stub so imports succeed without dependency
sys.modules.setdefault("websockets", types.SimpleNamespace(connect=None, WebSocketClientProtocol=object))

# Minimal psutil stub so imports succeed without dependency
psutil_stub = types.ModuleType("psutil")
psutil_stub.process_iter = lambda *a, **k: []
psutil_stub.cpu_percent = lambda interval=None: 0.0
psutil_stub.virtual_memory = lambda: types.SimpleNamespace(percent=0.0)
psutil_stub.disk_usage = lambda path: types.SimpleNamespace(free=0)
psutil_stub.NoSuchProcess = Exception
psutil_stub.AccessDenied = Exception
psutil_stub.TimeoutExpired = Exception
psutil_stub.ZombieProcess = Exception
sys.modules.setdefault("psutil", psutil_stub)

# Minimal utils_checks stub available via fixture


@pytest.fixture
def stub_utils_checks(monkeypatch):
    utils_stub = types.ModuleType("utils_checks")
    utils_stub.load_tags = lambda *a, **k: []
    utils_stub.check_obs_sync = lambda *a, **k: True
    utils_stub.check_media_mtx = lambda *a, **k: True
    utils_stub.check_backend_ready = lambda: True
    utils_stub.next_bout_number = lambda *a, **k: 1
    utils_stub.get_session_dir = lambda *a, **k: importlib.import_module("fight_state").get_session_dir(*a, **k)
    monkeypatch.setitem(sys.modules, "utils_checks", utils_stub)
    return utils_stub


# Ensure required environment variables for settings
os.environ.setdefault("HR_RED_MAC", "AA:BB:CC:DD:EE:FF")
os.environ.setdefault("HR_BLUE_MAC", "11:22:33:44:55:66")

from config.settings import reset_settings  # noqa: E402
from utils.template_loader import load_template  # noqa: E402


@pytest.fixture()
def stub_optional_dependencies(monkeypatch):
    """Stub heavy optional third-party modules.

    The real project can optionally depend on libraries like ``pandas`` or
    ``matplotlib``.  Tests that exercise the lightweight ``RoundManager`` avoid
    pulling in those heavy dependencies by providing minimal module stubs.
    """

    modules = {
        "matplotlib": types.ModuleType("matplotlib"),
        "matplotlib.pyplot": types.ModuleType("pyplot"),
        "pandas": types.ModuleType("pandas"),
        "psutil": psutil_stub,
    }
    modules["matplotlib"].use = lambda *a, **k: None
    modules["matplotlib"].pyplot = modules["matplotlib.pyplot"]

    for name, mod in modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    # Ensure the real RoundManager implementation is available for tests
    sys.modules.pop("FightControl.round_manager", None)
    rm_module = importlib.import_module("FightControl.round_manager")
    monkeypatch.setitem(sys.modules, "FightControl.round_manager", rm_module)
    monkeypatch.setattr(FightControl, "RoundManager", rm_module.RoundManager, raising=False)
    monkeypatch.setattr(FightControl, "RoundState", rm_module.RoundState, raising=False)


@pytest.fixture()
def boot_template(tmp_path):
    """Write boot.html template into temporary test directory."""
    dest_dir = tmp_path / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "boot.html"
    dest.write_text(load_template("boot.html"))
    return dest


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Reset settings between tests to avoid env leakage."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture(autouse=True)
def clear_boot_state():
    set_boot_state({})
    yield
    set_boot_state({})
