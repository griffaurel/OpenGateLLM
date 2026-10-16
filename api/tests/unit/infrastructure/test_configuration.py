import os
from pathlib import Path
import subprocess
import sys

REPOSITORY_ROOT = Path(__file__).parents[4]


def test_should_import_the_app_modules_without_a_configuration_file(tmp_path):
    # Arrange
    # A fresh interpreter: in the pytest process these modules are already imported, so importing them again would prove nothing.
    environment = {**os.environ, "CONFIG_FILE": str(tmp_path / "missing.yml")}

    # Act
    result = subprocess.run(
        [sys.executable, "-c", "import api.infrastructure.configuration, api.dependencies, api.app"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )

    # Assert
    assert result.returncode == 0, result.stderr


def _model(router_type: str, provider_type: str) -> dict:
    return {
        "name": "my-model",
        "type": router_type,
        "providers": [{"type": provider_type, "url": "http://provider.test", "model_name": "provider-model"}],
    }


def test_should_accept_a_colibri_provider_for_a_decision_model_in_the_configuration_file():
    from api.infrastructure.configuration import Model

    model = Model.model_validate(_model(router_type="decision", provider_type="colibri"))

    assert [provider.type.value for provider in model.providers] == ["colibri"]


def test_should_refuse_a_provider_type_that_does_not_fit_the_model_type_in_the_configuration_file():
    import pytest

    from api.infrastructure.configuration import Model

    for router_type, provider_type in [
        ("decision", "openai"),
        ("decision", "vllm"),
        ("text-generation", "colibri"),
        ("text-embeddings-inference", "colibri"),
    ]:
        with pytest.raises(Exception, match="not compatible"):
            Model.model_validate(_model(router_type=router_type, provider_type=provider_type))
