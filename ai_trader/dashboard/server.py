import os

def create_app():
    try:
        from flask import Flask
        from flask_cors import CORS
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Dashboard indisponible : installe l'extra [dashboard]") from e

    flask_app = Flask(__name__)
    CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

    # API
    try:
        from .routes import api_bp
        flask_app.register_blueprint(api_bp, url_prefix="/api")
    except Exception as e:  # pragma: no cover
        print(f"[dashboard] API non montée (optionnel): {e}")

    # WS (optionnel)
    socketio = None
    try:
        from flask_socketio import SocketIO
        from . import stream as _stream
        socketio = SocketIO(flask_app, cors_allowed_origins="*")
        _stream.attach_socketio(socketio)
    except Exception:  # pragma: no cover
        socketio = None

    # Dash UI (optionnel)
    dash_app = None
    try:
        import dash, dash_bootstrap_components as dbc
        from .layout import build_layout, register_callbacks
        dash_app = dash.Dash(
            __name__, server=flask_app, routes_pathname_prefix="/dashboard/",
            external_stylesheets=[
                dbc.themes.CYBORG if os.getenv("DASHBOARD_THEME", "dark") == "dark" else dbc.themes.FLATLY
            ],
            suppress_callback_exceptions=True,
        )
        dash_app.layout = build_layout()
        register_callbacks(dash_app)
    except Exception as e:  # pragma: no cover
        print(f"[dashboard] Dash non monté (optionnel): {e}")

    return flask_app, dash_app, socketio
