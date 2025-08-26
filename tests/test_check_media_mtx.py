import os
import socket
import sys
from pathlib import Path

import pytest


@pytest.fixture
def unused_tcp_port() -> int:
    """Return an unused TCP port for tests."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)

from utils import check_media_mtx


def test_check_media_mtx_reachable(unused_tcp_port: int):
    """Check that a listening socket is detected as reachable."""
    with socket.socket() as server:
        server.bind(("127.0.0.1", unused_tcp_port))
        server.listen()

        assert check_media_mtx("127.0.0.1", unused_tcp_port)

        conn, _ = server.accept()
        conn.close()


def test_check_media_mtx_unreachable(unused_tcp_port: int):
    """Check that an unused port is reported as unreachable."""
    assert not check_media_mtx("127.0.0.1", unused_tcp_port)
