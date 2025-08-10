import importlib
import pytest

OPTIONAL_MODULES = ["tensorflow", "keras", "openai", "optuna", "prometheus_client"]


@pytest.mark.optional
@pytest.mark.parametrize("module", OPTIONAL_MODULES)
def test_optional_imports(module):
    try:
        importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"{module} unavailable: {exc}")
