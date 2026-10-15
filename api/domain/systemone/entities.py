import json
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from api.domain import BaseModel, ForwardablePayload
from api.domain.provider.entities import ProviderJsonResponse
from api.domain.usage.entities import Usage

# Free content the provider reads as text: a string, or JSON given as an object or an array.
SystemOneContent = str | dict[str, Any] | list[Any]

MAX_QUESTIONS = 64
MAX_OPTIONS = 255


def _to_text(content: SystemOneContent | None) -> str:
    match content:
        case None:
            return ""
        case str():
            return content
        case _:
            return json.dumps(content, ensure_ascii=False)


class NoulCriteria(BaseModel):
    true: SystemOneContent | None = None
    false: SystemOneContent | None = None


class NoulQuestion(BaseModel):
    type: Literal["noul"]
    instructions: SystemOneContent | None = None
    criteria: NoulCriteria | None = None

    def get_prompts(self) -> list[str]:
        criteria = [self.criteria.true, self.criteria.false] if self.criteria else []
        return [_to_text(content) for content in [self.instructions, *criteria]]


class ChoiceQuestion(BaseModel):
    type: Literal["choice"]
    instructions: SystemOneContent | None = None
    criteria: Annotated[dict[str, SystemOneContent | None], Field(min_length=1, max_length=MAX_OPTIONS)]

    @field_validator("criteria")
    @classmethod
    def labels_must_not_be_blank(cls, criteria: dict[str, SystemOneContent | None]) -> dict[str, SystemOneContent | None]:
        if any(not label.strip() for label in criteria):
            raise ValueError("Every label must be a non-empty string.")
        return criteria

    def get_prompts(self) -> list[str]:
        contents = [self.instructions]
        for label, description in self.criteria.items():
            contents.extend([label, description])
        return [_to_text(content) for content in contents]


class ScoreQuestion(BaseModel):
    type: Literal["score"]
    instructions: SystemOneContent | None = None
    criteria: Annotated[list[SystemOneContent | None], Field(min_length=1, max_length=MAX_OPTIONS)]

    def get_prompts(self) -> list[str]:
        return [_to_text(content) for content in [self.instructions, *self.criteria]]


SystemOneQuestion = Annotated[NoulQuestion | ChoiceQuestion | ScoreQuestion, Field(discriminator="type")]


class CreateSystemOneBody(ForwardablePayload):
    model: str
    state: SystemOneContent
    questions: Annotated[dict[str, SystemOneQuestion], Field(min_length=1, max_length=MAX_QUESTIONS)]

    @field_validator("questions")
    @classmethod
    def ids_must_not_be_blank(cls, questions: dict[str, SystemOneQuestion]) -> dict[str, SystemOneQuestion]:
        if any(not question_id.strip() for question_id in questions):
            raise ValueError("Every question id must be a non-empty string.")
        return questions

    def get_prompts(self) -> list[str]:
        """The text the provider reads: the state, then each question's instructions and criteria."""
        prompts = [_to_text(self.state)]
        for question in self.questions.values():
            prompts.extend(question.get_prompts())
        return [prompt for prompt in prompts if prompt]


class NoulAnswer(BaseModel):
    type: Literal["noul"]
    noul: float


class ChoiceAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, float]
    confidence: float | None = None


class ScoreAnswer(BaseModel):
    type: Literal["score"]
    score: float
    legend: dict[str, SystemOneContent | None]
    probabilities: dict[str, float]
    confidence: float | None = None


SystemOneAnswer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class SystemOne(ProviderJsonResponse):
    id: str
    model: str
    answers: dict[str, SystemOneAnswer]
    usage: Annotated[Usage, Field(default_factory=Usage)]

    def get_completions(self) -> list[str]:
        # The provider scores the options, it generates nothing: no output tokens are counted.
        return []
