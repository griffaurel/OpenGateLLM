from typing import Annotated

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.domain.systemone.entities import MAX_QUESTIONS, SystemOneAnswer, SystemOneContent, SystemOneQuestion
from api.domain.usage.entities import Usage


class CreateSystemOneBody(BaseModel):
    model: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True), Field(default=..., description="The model to use for the decision, call `/v1/models` endpoint to get the list of available models, only `decision` model type is supported.")]  # fmt: off
    state: Annotated[SystemOneContent, Field(description="What the questions are about: a text, or JSON given as an object or an array.")]  # fmt: off
    questions: Annotated[dict[str, SystemOneQuestion], Field(min_length=1, max_length=MAX_QUESTIONS, description="The questions to answer, by id (1 to 64). Each has a `type` (`noul` for yes/no, `choice` or `score`), optional `instructions` and its `criteria`. The answers use the same ids.")]  # fmt: off


class SystemOneResponse(BaseModel):
    id: Annotated[str, Field(default=..., description="A unique identifier for the request.")]
    model: Annotated[str, Field(default=..., description="The model used to make the decision.")]
    answers: Annotated[dict[str, SystemOneAnswer], Field(default=..., description="The answers by question id, with a probability for each option.")]  # fmt: off
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]
