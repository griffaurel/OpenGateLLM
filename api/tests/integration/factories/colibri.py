import factory

# What `GET /v1/models` of a Colibrì server answers (`c/openai_server.py` @ bf24429, `model_entry()` and `jev_model_card()`):
# the OpenAI list in `data`, and Jev's model card in `models`. Not recorded from a running server.
COLIBRI_OWNED_BY = "colibri"


class ColibriModelsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model", "capabilities"]

    _status_code = 200

    # parameters
    model = "qwen36"
    capabilities = ["chat", "systemone"]

    # body
    object = "list"
    data = factory.LazyAttribute(
        lambda self: [
            {
                "id": self.model,
                "object": "model",
                "created": 1760000000,
                "owned_by": COLIBRI_OWNED_BY,
                "input_modalities": ["text"],
                "capabilities": self.capabilities,
            }
        ]
    )
    models = factory.LazyAttribute(
        lambda self: [
            {
                "name": self.model,
                "description": f"{self.model}, served by colibri; POST /v1/systemone answers typed questions.",
                "release_date": "2026-10-14",
            }
        ]
    )
