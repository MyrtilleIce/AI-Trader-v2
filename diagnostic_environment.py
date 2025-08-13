REQUIRED = ["requests", "pandas", "numpy", "python-dotenv"]
DASHBOARD = ["flask", "flask_cors", "dash", "dash_bootstrap_components", "plotly"]

if __name__ == "__main__":
    import importlib

    def missing(pkgs):
        out = []
        for p in pkgs:
            try:
                importlib.import_module(p)
            except Exception:  # noqa: BLE001
                out.append(p)
        return out

    r = missing(REQUIRED)
    if r:
        print("[diag] Obligatoires manquants:", ", ".join(r))
    d = missing(DASHBOARD)
    if d:
        print("[diag] Dashboard manquants (installe l'extra [dashboard]):", ", ".join(d))
