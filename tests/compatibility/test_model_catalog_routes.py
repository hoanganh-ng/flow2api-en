"""Characterization tests for model catalog helpers and read-only model routes.

These tests exercise offline, deterministic model-catalog behavior without
constructing the FastAPI application, invoking HTTP transport, starting
lifespan, or contacting upstream services.

Only standard-library unittest is used. No pytest or extra dependencies.

Sprint 006C — Model Catalog and Read-Only Route Characterization.
"""

import asyncio
import unittest

from src.api.routes import (
    _build_gemini_model_resource,
    _build_model_description,
    _get_gemini_model_catalog,
    _get_openai_model_catalog,
    get_gemini_model,
    list_gemini_models,
    list_model_aliases,
    list_models,
)
from src.core.model_resolver import get_base_model_aliases
from src.services.generation_handler import MODEL_CONFIG


# ---------------------------------------------------------------------------
# _build_model_description
# ---------------------------------------------------------------------------
class BuildModelDescriptionTests(unittest.TestCase):
    """Tests for _build_model_description: human-readable model description."""

    def test_image_type_uses_model_name(self):
        cfg = {"type": "image", "model_name": "GEM_PIX_2", "model_key": "ignored"}
        desc = _build_model_description(cfg)
        self.assertIn("Image generation", desc)
        self.assertIn("GEM_PIX_2", desc)

    def test_video_type_uses_model_key(self):
        cfg = {"type": "video", "model_name": "ignored", "model_key": "veo_3_1_t2v_fast"}
        desc = _build_model_description(cfg)
        self.assertIn("Video generation", desc)
        self.assertIn("veo_3_1_t2v_fast", desc)

    def test_description_format_image(self):
        cfg = {"type": "image", "model_name": "NARWHAL", "model_key": "x"}
        desc = _build_model_description(cfg)
        self.assertEqual(desc, "Image generation - NARWHAL")

    def test_description_format_video(self):
        cfg = {"type": "video", "model_name": "x", "model_key": "veo_3_1_i2v_s"}
        desc = _build_model_description(cfg)
        self.assertEqual(desc, "Video generation - veo_3_1_i2v_s")

    def test_capitalizes_type(self):
        cfg = {"type": "image", "model_name": "X", "model_key": "x"}
        desc = _build_model_description(cfg)
        self.assertTrue(desc.startswith("Image"))

    def test_unknown_type_still_works(self):
        cfg = {"type": "audio", "model_name": "X", "model_key": "y"}
        desc = _build_model_description(cfg)
        self.assertIn("Audio generation", desc)
        self.assertIn("y", desc)


# ---------------------------------------------------------------------------
# _get_openai_model_catalog
# ---------------------------------------------------------------------------
class GetOpenAIModelCatalogTests(unittest.TestCase):
    """Tests for _get_openai_model_catalog: list of {id, description}."""

    def setUp(self):
        self.catalog = _get_openai_model_catalog()

    def test_returns_list(self):
        self.assertIsInstance(self.catalog, list)

    def test_non_empty(self):
        self.assertGreater(len(self.catalog), 0)

    def test_entry_has_id_and_description(self):
        for entry in self.catalog:
            self.assertIn("id", entry)
            self.assertIn("description", entry)

    def test_entry_has_exactly_two_keys(self):
        for entry in self.catalog:
            self.assertEqual(set(entry.keys()), {"id", "description"})

    def test_all_ids_are_strings(self):
        for entry in self.catalog:
            self.assertIsInstance(entry["id"], str)

    def test_all_descriptions_are_strings(self):
        for entry in self.catalog:
            self.assertIsInstance(entry["description"], str)

    def test_ids_match_model_config_keys(self):
        catalog_ids = [entry["id"] for entry in self.catalog]
        self.assertEqual(catalog_ids, list(MODEL_CONFIG.keys()))

    def test_unique_ids(self):
        ids = [entry["id"] for entry in self.catalog]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_secrets_in_descriptions(self):
        for entry in self.catalog:
            desc = entry["description"].lower()
            self.assertNotIn("password", desc)
            self.assertNotIn("secret", desc)
            self.assertNotIn("token", desc)
            self.assertNotIn("api_key", desc)

    def test_count_matches_model_config(self):
        self.assertEqual(len(self.catalog), len(MODEL_CONFIG))

    def test_image_model_description_contains_generation_label(self):
        for entry in self.catalog:
            model_cfg = MODEL_CONFIG[entry["id"]]
            if model_cfg["type"] == "image":
                self.assertIn("Image generation", entry["description"])

    def test_video_model_description_contains_generation_label(self):
        for entry in self.catalog:
            model_cfg = MODEL_CONFIG[entry["id"]]
            if model_cfg["type"] == "video":
                self.assertIn("Video generation", entry["description"])


# ---------------------------------------------------------------------------
# _get_gemini_model_catalog
# ---------------------------------------------------------------------------
class GetGeminiModelCatalogTests(unittest.TestCase):
    """Tests for _get_gemini_model_catalog: dict of model_id -> description."""

    def setUp(self):
        self.catalog = _get_gemini_model_catalog()

    def test_returns_dict(self):
        self.assertIsInstance(self.catalog, dict)

    def test_non_empty(self):
        self.assertGreater(len(self.catalog), 0)

    def test_all_keys_are_strings(self):
        for key in self.catalog:
            self.assertIsInstance(key, str)

    def test_all_values_are_strings(self):
        for val in self.catalog.values():
            self.assertIsInstance(val, str)

    def test_contains_all_model_config_keys(self):
        for model_id in MODEL_CONFIG:
            self.assertIn(model_id, self.catalog)

    def test_contains_aliases(self):
        aliases = get_base_model_aliases()
        for alias_id in aliases:
            self.assertIn(alias_id, self.catalog)

    def test_alias_descriptions_contain_alias_marker(self):
        aliases = get_base_model_aliases()
        for alias_id in aliases:
            desc = self.catalog[alias_id]
            self.assertIn("alias", desc.lower())

    def test_gemini_catalog_size_gte_model_config(self):
        self.assertGreaterEqual(len(self.catalog), len(MODEL_CONFIG))

    def test_no_secrets_in_values(self):
        for desc in self.catalog.values():
            self.assertNotIn("password", desc.lower())
            self.assertNotIn("secret", desc.lower())


# ---------------------------------------------------------------------------
# _build_gemini_model_resource
# ---------------------------------------------------------------------------
class BuildGeminiModelResourceTests(unittest.TestCase):
    """Tests for _build_gemini_model_resource: Gemini model resource shape."""

    def setUp(self):
        self.resource = _build_gemini_model_resource("test-model", "A test description")

    def test_returns_dict(self):
        self.assertIsInstance(self.resource, dict)

    def test_name_field(self):
        self.assertEqual(self.resource["name"], "models/test-model")

    def test_display_name_field(self):
        self.assertEqual(self.resource["displayName"], "test-model")

    def test_description_field(self):
        self.assertEqual(self.resource["description"], "A test description")

    def test_version_field(self):
        self.assertEqual(self.resource["version"], "flow2api")

    def test_input_token_limit(self):
        self.assertEqual(self.resource["inputTokenLimit"], 0)

    def test_output_token_limit(self):
        self.assertEqual(self.resource["outputTokenLimit"], 0)

    def test_supported_generation_methods(self):
        methods = self.resource["supportedGenerationMethods"]
        self.assertIsInstance(methods, list)
        self.assertIn("generateContent", methods)
        self.assertIn("streamGenerateContent", methods)

    def test_required_keys_present(self):
        expected_keys = {
            "name", "displayName", "description", "version",
            "inputTokenLimit", "outputTokenLimit", "supportedGenerationMethods",
        }
        self.assertEqual(set(self.resource.keys()), expected_keys)

    def test_name_prefix_format(self):
        resource = _build_gemini_model_resource("my-model", "desc")
        self.assertTrue(resource["name"].startswith("models/"))

    def test_empty_model_id(self):
        resource = _build_gemini_model_resource("", "desc")
        self.assertEqual(resource["name"], "models/")
        self.assertEqual(resource["displayName"], "")


# ---------------------------------------------------------------------------
# get_base_model_aliases (from model_resolver)
# ---------------------------------------------------------------------------
class GetBaseModelAliasesTests(unittest.TestCase):
    """Tests for get_base_model_aliases: simplified alias map."""

    def setUp(self):
        self.aliases = get_base_model_aliases()

    def test_returns_dict(self):
        self.assertIsInstance(self.aliases, dict)

    def test_non_empty(self):
        self.assertGreater(len(self.aliases), 0)

    def test_image_aliases_present(self):
        self.assertIn("gemini-3.0-pro-image", self.aliases)
        self.assertIn("gemini-3.1-flash-image", self.aliases)
        self.assertIn("imagen-4.0-generate-preview", self.aliases)

    def test_video_aliases_present(self):
        self.assertIn("veo_3_1_t2v_fast", self.aliases)

    def test_all_values_are_strings(self):
        for val in self.aliases.values():
            self.assertIsInstance(val, str)

    def test_image_alias_descriptions_contain_aspects(self):
        desc = self.aliases["gemini-3.0-pro-image"]
        self.assertIn("aspects:", desc)

    def test_video_alias_descriptions_contain_landscape_portrait(self):
        desc = self.aliases["veo_3_1_t2v_fast"]
        self.assertIn("landscape", desc)
        self.assertIn("portrait", desc)


# ---------------------------------------------------------------------------
# list_models (OpenAI /v1/models route function — direct call)
# ---------------------------------------------------------------------------
class ListModelsRouteTests(unittest.IsolatedAsyncioTestCase):
    """Tests for list_models: OpenAI-compatible model list route.

    The route function is called directly as a Python function, supplying
    the already-resolved dependency parameter api_key. Authentication
    behavior is not exercised.
    """

    async def test_returns_dict(self):
        result = await list_models(api_key="test-key")
        self.assertIsInstance(result, dict)

    async def test_top_level_object_field(self):
        result = await list_models(api_key="test-key")
        self.assertEqual(result["object"], "list")

    async def test_data_is_list(self):
        result = await list_models(api_key="test-key")
        self.assertIsInstance(result["data"], list)

    async def test_data_count_matches_catalog(self):
        result = await list_models(api_key="test-key")
        catalog = _get_openai_model_catalog()
        self.assertEqual(len(result["data"]), len(catalog))

    async def test_entry_required_fields(self):
        result = await list_models(api_key="test-key")
        for entry in result["data"]:
            self.assertIn("id", entry)
            self.assertIn("object", entry)
            self.assertIn("owned_by", entry)
            self.assertIn("description", entry)

    async def test_object_field_is_model(self):
        result = await list_models(api_key="test-key")
        for entry in result["data"]:
            self.assertEqual(entry["object"], "model")

    async def test_owned_by_is_flow2api(self):
        result = await list_models(api_key="test-key")
        for entry in result["data"]:
            self.assertEqual(entry["owned_by"], "flow2api")

    async def test_ids_match_catalog(self):
        result = await list_models(api_key="test-key")
        catalog = _get_openai_model_catalog()
        result_ids = [e["id"] for e in result["data"]]
        catalog_ids = [e["id"] for e in catalog]
        self.assertEqual(result_ids, catalog_ids)

    async def test_unique_ids(self):
        result = await list_models(api_key="test-key")
        ids = [e["id"] for e in result["data"]]
        self.assertEqual(len(ids), len(set(ids)))

    async def test_no_sensitive_fields(self):
        result = await list_models(api_key="test-key")
        for entry in result["data"]:
            self.assertNotIn("api_key", entry)
            self.assertNotIn("token", entry)
            self.assertNotIn("secret", entry)

    async def test_entries_do_not_contain_created(self):
        """Current /v1/models route does not emit a 'created' field.

        FX-ML-001 includes 'created' as a synthetic placeholder, but the
        live route implementation has never emitted it. This assertion
        characterizes the current behavior; no runtime change is proposed.
        """
        result = await list_models(api_key="test-key")
        for entry in result["data"]:
            self.assertNotIn("created", entry)

    async def test_entry_has_exactly_four_keys(self):
        """Current route entries have exactly: id, object, owned_by, description."""
        result = await list_models(api_key="test-key")
        for entry in result["data"]:
            self.assertEqual(
                set(entry.keys()), {"id", "object", "owned_by", "description"}
            )

    async def test_top_level_has_exactly_two_keys(self):
        result = await list_models(api_key="test-key")
        self.assertEqual(set(result.keys()), {"object", "data"})

    async def test_structural_compatibility_with_fixture(self):
        """Structural compatibility with FX-ML-001 (openai-model-list.json).

        FX-ML-001 is a synthetic structural fixture that uses a subset of
        models and includes a 'created' field. The current /v1/models route
        does NOT emit 'created'. This test verifies the shared contract
        shape (object=list, data entries have id/object/owned_by) without
        requiring exact equality. The 'created' field is fixture-only
        relative to the current implementation and is not a required
        current-runtime field. No runtime change is proposed.
        """
        result = await list_models(api_key="test-key")
        self.assertEqual(result["object"], "list")
        self.assertIsInstance(result["data"], list)
        self.assertGreater(len(result["data"]), 0)
        for entry in result["data"]:
            self.assertIsInstance(entry.get("id"), str)
            self.assertEqual(entry.get("object"), "model")
            self.assertEqual(entry.get("owned_by"), "flow2api")


# ---------------------------------------------------------------------------
# list_model_aliases (/v1/models/aliases route function — direct call)
# ---------------------------------------------------------------------------
class ListModelAliasesRouteTests(unittest.IsolatedAsyncioTestCase):
    """Tests for list_model_aliases: simplified alias list route.

    The route function is called directly as a Python function, supplying
    the already-resolved dependency parameter api_key. Authentication
    behavior is not exercised.
    """

    async def test_returns_dict(self):
        result = await list_model_aliases(api_key="test-key")
        self.assertIsInstance(result, dict)

    async def test_top_level_object_field(self):
        result = await list_model_aliases(api_key="test-key")
        self.assertEqual(result["object"], "list")

    async def test_data_is_list(self):
        result = await list_model_aliases(api_key="test-key")
        self.assertIsInstance(result["data"], list)

    async def test_entry_required_fields(self):
        result = await list_model_aliases(api_key="test-key")
        for entry in result["data"]:
            self.assertIn("id", entry)
            self.assertIn("object", entry)
            self.assertIn("owned_by", entry)
            self.assertIn("description", entry)
            self.assertIn("is_alias", entry)

    async def test_is_alias_is_true(self):
        result = await list_model_aliases(api_key="test-key")
        for entry in result["data"]:
            self.assertTrue(entry["is_alias"])

    async def test_object_field_is_model(self):
        result = await list_model_aliases(api_key="test-key")
        for entry in result["data"]:
            self.assertEqual(entry["object"], "model")

    async def test_owned_by_is_flow2api(self):
        result = await list_model_aliases(api_key="test-key")
        for entry in result["data"]:
            self.assertEqual(entry["owned_by"], "flow2api")

    async def test_count_matches_aliases(self):
        result = await list_model_aliases(api_key="test-key")
        aliases = get_base_model_aliases()
        self.assertEqual(len(result["data"]), len(aliases))

    async def test_ids_match_aliases(self):
        result = await list_model_aliases(api_key="test-key")
        aliases = get_base_model_aliases()
        result_ids = {e["id"] for e in result["data"]}
        self.assertEqual(result_ids, set(aliases.keys()))

    async def test_unique_ids(self):
        result = await list_model_aliases(api_key="test-key")
        ids = [e["id"] for e in result["data"]]
        self.assertEqual(len(ids), len(set(ids)))


# ---------------------------------------------------------------------------
# list_gemini_models (/v1beta/models and /models route — direct call)
# ---------------------------------------------------------------------------
class ListGeminiModelsRouteTests(unittest.IsolatedAsyncioTestCase):
    """Tests for list_gemini_models: Gemini-compatible model list route.

    The route function is called directly as a Python function, supplying
    the already-resolved dependency parameter api_key. Authentication
    behavior is not exercised.
    """

    async def test_returns_dict(self):
        result = await list_gemini_models(api_key="test-key")
        self.assertIsInstance(result, dict)

    async def test_top_level_models_key(self):
        result = await list_gemini_models(api_key="test-key")
        self.assertIn("models", result)

    async def test_models_is_list(self):
        result = await list_gemini_models(api_key="test-key")
        self.assertIsInstance(result["models"], list)

    async def test_model_resource_shape(self):
        result = await list_gemini_models(api_key="test-key")
        for model in result["models"]:
            self.assertIn("name", model)
            self.assertIn("displayName", model)
            self.assertIn("description", model)
            self.assertIn("version", model)
            self.assertIn("supportedGenerationMethods", model)

    async def test_name_prefix(self):
        result = await list_gemini_models(api_key="test-key")
        for model in result["models"]:
            self.assertTrue(model["name"].startswith("models/"))

    async def test_version_is_flow2api(self):
        result = await list_gemini_models(api_key="test-key")
        for model in result["models"]:
            self.assertEqual(model["version"], "flow2api")

    async def test_supported_generation_methods(self):
        result = await list_gemini_models(api_key="test-key")
        for model in result["models"]:
            methods = model["supportedGenerationMethods"]
            self.assertIn("generateContent", methods)
            self.assertIn("streamGenerateContent", methods)

    async def test_count_matches_gemini_catalog(self):
        result = await list_gemini_models(api_key="test-key")
        catalog = _get_gemini_model_catalog()
        self.assertEqual(len(result["models"]), len(catalog))

    async def test_display_names_match_catalog_keys(self):
        result = await list_gemini_models(api_key="test-key")
        catalog = _get_gemini_model_catalog()
        display_names = {m["displayName"] for m in result["models"]}
        self.assertEqual(display_names, set(catalog.keys()))

    async def test_token_limits_are_zero(self):
        result = await list_gemini_models(api_key="test-key")
        for model in result["models"]:
            self.assertEqual(model["inputTokenLimit"], 0)
            self.assertEqual(model["outputTokenLimit"], 0)


# ---------------------------------------------------------------------------
# get_gemini_model (/v1beta/models/{model} and /models/{model} — direct call)
# ---------------------------------------------------------------------------
class GetGeminiModelRouteTests(unittest.IsolatedAsyncioTestCase):
    """Tests for get_gemini_model: single Gemini model lookup route.

    The route function is called directly as a Python function, supplying
    the already-resolved dependency parameter api_key. Authentication
    behavior is not exercised.
    """

    async def test_known_model_returns_resource(self):
        first_key = next(iter(MODEL_CONFIG))
        result = await get_gemini_model(model=first_key, api_key="test-key")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["displayName"], first_key)

    async def test_known_model_has_name_prefix(self):
        first_key = next(iter(MODEL_CONFIG))
        result = await get_gemini_model(model=first_key, api_key="test-key")
        self.assertEqual(result["name"], f"models/{first_key}")

    async def test_known_model_has_required_fields(self):
        first_key = next(iter(MODEL_CONFIG))
        result = await get_gemini_model(model=first_key, api_key="test-key")
        expected_keys = {
            "name", "displayName", "description", "version",
            "inputTokenLimit", "outputTokenLimit", "supportedGenerationMethods",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    async def test_alias_model_returns_resource(self):
        aliases = get_base_model_aliases()
        if aliases:
            alias_key = next(iter(aliases))
            result = await get_gemini_model(model=alias_key, api_key="test-key")
            self.assertIsInstance(result, dict)
            self.assertEqual(result["displayName"], alias_key)

    async def test_unknown_model_returns_404_json_response(self):
        from fastapi.responses import JSONResponse
        result = await get_gemini_model(model="nonexistent-model-xyz", api_key="test-key")
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 404)

    async def test_unknown_model_error_payload(self):
        import json
        result = await get_gemini_model(model="nonexistent-model-xyz", api_key="test-key")
        body = json.loads(result.body)
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], 404)
        self.assertEqual(body["error"]["status"], "NOT_FOUND")
        self.assertIn("nonexistent-model-xyz", body["error"]["message"])

    async def test_known_model_version(self):
        first_key = next(iter(MODEL_CONFIG))
        result = await get_gemini_model(model=first_key, api_key="test-key")
        self.assertEqual(result["version"], "flow2api")

    async def test_known_model_generation_methods(self):
        first_key = next(iter(MODEL_CONFIG))
        result = await get_gemini_model(model=first_key, api_key="test-key")
        methods = result["supportedGenerationMethods"]
        self.assertIn("generateContent", methods)
        self.assertIn("streamGenerateContent", methods)


# ---------------------------------------------------------------------------
# Model catalog integration: relationship between helpers
# ---------------------------------------------------------------------------
class ModelCatalogIntegrationTests(unittest.TestCase):
    """Cross-helper consistency checks for model catalog behavior."""

    def test_openai_catalog_ids_are_subset_of_gemini_catalog(self):
        openai_catalog = _get_openai_model_catalog()
        gemini_catalog = _get_gemini_model_catalog()
        openai_ids = {e["id"] for e in openai_catalog}
        gemini_ids = set(gemini_catalog.keys())
        self.assertTrue(openai_ids.issubset(gemini_ids))

    def test_aliases_are_subset_of_gemini_catalog(self):
        aliases = get_base_model_aliases()
        gemini_catalog = _get_gemini_model_catalog()
        alias_ids = set(aliases.keys())
        gemini_ids = set(gemini_catalog.keys())
        self.assertTrue(alias_ids.issubset(gemini_ids))

    def test_model_config_keys_are_subset_of_gemini_catalog(self):
        gemini_catalog = _get_gemini_model_catalog()
        gemini_ids = set(gemini_catalog.keys())
        config_ids = set(MODEL_CONFIG.keys())
        self.assertTrue(config_ids.issubset(gemini_ids))

    def test_gemini_catalog_is_union_of_aliases_and_config(self):
        aliases = set(get_base_model_aliases().keys())
        config_ids = set(MODEL_CONFIG.keys())
        gemini_catalog = set(_get_gemini_model_catalog().keys())
        self.assertEqual(gemini_catalog, aliases | config_ids)

    def test_model_config_types_are_image_or_video(self):
        for model_id, cfg in MODEL_CONFIG.items():
            self.assertIn(cfg["type"], ("image", "video"), f"{model_id} has unexpected type")

    def test_image_models_have_model_name(self):
        for model_id, cfg in MODEL_CONFIG.items():
            if cfg["type"] == "image":
                self.assertIn("model_name", cfg, f"{model_id} missing model_name")

    def test_video_models_have_model_key(self):
        for model_id, cfg in MODEL_CONFIG.items():
            if cfg["type"] == "video":
                self.assertIn("model_key", cfg, f"{model_id} missing model_key")

    def test_video_models_have_video_type(self):
        for model_id, cfg in MODEL_CONFIG.items():
            if cfg["type"] == "video":
                self.assertIn("video_type", cfg, f"{model_id} missing video_type")


if __name__ == "__main__":
    unittest.main()
