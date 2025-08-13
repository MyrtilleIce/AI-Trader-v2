import importlib.util
import pytest

need_flask = importlib.util.find_spec("flask") is not None
need_dash = importlib.util.find_spec("dash") is not None

pytestmark = pytest.mark.skipif(not (need_flask and need_dash), reason="dashboard extras non installés")

def test_create_app():
    from ai_trader.dashboard.server import create_app
    app, dash_app, socketio = create_app()
    assert app is not None
