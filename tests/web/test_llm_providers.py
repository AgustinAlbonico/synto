"""Tests for LLM provider management API endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from synto.web import WebConfig, create_app

try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi.testclient not available", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "AGENT-REGISTRY.yaml"


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    config = WebConfig.from_env(
        workspace_dir=tmp_path,
        projects_root=tmp_path / "projects",
        memory_db_path=tmp_path / "memory.db",
        registry_path=REGISTRY_PATH,
    )
    app = create_app(config)
    return TestClient(app)


class TestLLMProvidersEndpoint:
    def test_list_providers(self, client: TestClient):
        r = client.get("/api/llm/providers")
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        # Should have at least some providers from catalog
        providers = data["providers"]
        assert len(providers) >= 1
        # Check structure
        p = providers[0]
        assert "id" in p
        assert "name" in p
        assert "configured" in p
        assert "models" in p

    def test_list_providers_keys_masked(self, client: TestClient):
        """API keys must be masked in responses."""
        r = client.get("/api/llm/providers")
        data = r.json()
        for provider in data["providers"]:
            if provider.get("api_key"):
                assert "***" in provider["api_key"]


class TestLLMModelsEndpoint:
    def test_list_all_models(self, client: TestClient):
        r = client.get("/api/llm/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        # Should have models from catalog
        assert len(data["models"]) >= 1

    def test_models_have_required_fields(self, client: TestClient):
        r = client.get("/api/llm/models")
        data = r.json()
        for model in data["models"]:
            assert "id" in model
            assert "provider_name" in model
            assert "context_window" in model
            assert "tier" in model


class TestLLMProfilesEndpoint:
    def test_get_profiles_empty(self, client: TestClient):
        """Fresh config has no models.yaml, returns empty profiles."""
        r = client.get("/api/llm/profiles")
        assert r.status_code == 200
        data = r.json()
        assert "profiles" in data

    def test_update_and_get_profiles(self, client: TestClient):
        payload = {
            "agents": {"planner": "premium", "builder": "economy"},
            "profiles": {"default": "gpt-4o", "premium": "opus"},
        }
        r = client.put("/api/llm/profiles", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

        # Verify persistence
        r2 = client.get("/api/llm/profiles")
        result = r2.json()
        saved = result.get("profiles", {})
        assert saved.get("agents", {}).get("planner") == "premium"
        assert saved.get("profiles", {}).get("default") == "gpt-4o"


class TestLLMProviderTestEndpoint:
    def test_test_provider_returns_status(self, client: TestClient):
        r = client.post("/api/llm/providers/zen/test")
        assert r.status_code == 200
        data = r.json()
        assert "available" in data
        assert "models_count" in data


class TestLLMProviderUpdate:
    def test_update_provider_404_for_unknown(self, client: TestClient):
        r = client.put("/api/llm/providers/nonexistent_provider_xyz", json={"api_key": "sk-test"})
        assert r.status_code == 404
