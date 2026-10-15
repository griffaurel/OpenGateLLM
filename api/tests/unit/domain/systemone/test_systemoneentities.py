from pydantic import ValidationError
import pytest

from api.domain.systemone.entities import CreateSystemOneBody, SystemOne
from api.tests.integration.factories.systemone import SYSTEMONE_QUESTIONS, SYSTEMONE_STATE, SystemOneResponseFactory


def _body(**overrides) -> dict:
    body = {"model": "decision-router", "state": SYSTEMONE_STATE, "questions": SYSTEMONE_QUESTIONS}
    body.update(overrides)
    return body


class TestCreateSystemOneBody:
    def test_should_accept_the_three_question_types(self):
        body = CreateSystemOneBody.model_validate(_body())

        assert [question.type for question in body.questions.values()] == ["noul", "choice", "score"]

    @pytest.mark.parametrize("state", ["a text", "", {"ticket": {"id": 1}}, ["a", {"b": 2}]], ids=["text", "empty-text", "object", "array"])
    def test_should_accept_a_text_an_object_or_an_array_as_state(self, state):
        assert CreateSystemOneBody.model_validate(_body(state=state)).state == state

    def test_should_keep_the_options_it_does_not_know_so_that_they_reach_the_provider(self):
        body = CreateSystemOneBody.model_validate(_body(normalize="mean", cache_slot=2))

        dumped = body.model_dump(exclude_none=True)
        assert dumped["normalize"] == "mean"
        assert dumped["cache_slot"] == 2

    def test_should_keep_a_label_without_description_when_dropping_unset_fields(self):
        questions = {"queue": {"type": "choice", "criteria": {"billing": None, "bugs": "outages"}}}

        dumped = CreateSystemOneBody.model_validate(_body(questions=questions)).model_dump(exclude_none=True)

        assert dumped["questions"]["queue"] == {"type": "choice", "criteria": {"billing": None, "bugs": "outages"}}

    @pytest.mark.parametrize(
        "overrides",
        [
            {"state": None},
            {"questions": {}},
            {"questions": {f"q{i}": {"type": "noul"} for i in range(65)}},
            {"questions": {" ": {"type": "noul"}}},
            {"questions": {"q": {"type": "unknown"}}},
            {"questions": {"q": {"type": "choice"}}},
            {"questions": {"q": {"type": "choice", "criteria": {}}}},
            {"questions": {"q": {"type": "choice", "criteria": {" ": None}}}},
            {"questions": {"q": {"type": "choice", "criteria": {f"label{i}": None for i in range(256)}}}},
            {"questions": {"q": {"type": "choice", "criteria": ["a", "b"]}}},
            {"questions": {"q": {"type": "score"}}},
            {"questions": {"q": {"type": "score", "criteria": []}}},
            {"questions": {"q": {"type": "score", "criteria": {"a": "b"}}}},
            {"questions": {"q": {"type": "noul", "criteria": ["yes"]}}},
        ],
        ids=[
            "no-state",
            "no-question",
            "65-questions",
            "blank-question-id",
            "unknown-type",
            "choice-without-criteria",
            "choice-with-empty-criteria",
            "blank-label",
            "256-labels",
            "choice-with-a-list",
            "score-without-criteria",
            "score-with-empty-criteria",
            "score-with-an-object",
            "noul-with-a-list",
        ],
    )
    def test_should_reject_an_invalid_request(self, overrides):
        with pytest.raises(ValidationError):
            CreateSystemOneBody.model_validate(_body(**overrides))

    def test_should_accept_the_limits(self):
        questions = {f"q{i}": {"type": "choice", "criteria": {f"label{j}": None for j in range(255)}} for i in range(64)}

        assert len(CreateSystemOneBody.model_validate(_body(questions=questions)).questions) == 64

    def test_should_list_what_the_provider_reads_as_prompts(self):
        body = CreateSystemOneBody.model_validate(
            _body(
                state={"ticket": 1},
                questions={
                    "urgent": {"type": "noul", "instructions": "Is it urgent?", "criteria": {"true": "money lost", "false": "can wait"}},
                    "queue": {"type": "choice", "instructions": "Which queue?", "criteria": {"billing": "invoices", "bugs": None}},
                    "severity": {"type": "score", "criteria": ["none", {"level": "high"}]},
                },
            )
        )

        assert body.get_prompts() == [
            '{"ticket": 1}',
            "Is it urgent?",
            "money lost",
            "can wait",
            "Which queue?",
            "billing",
            "invoices",
            "bugs",
            "none",
            '{"level": "high"}',
        ]

    def test_should_not_list_empty_texts(self):
        body = CreateSystemOneBody.model_validate(_body(state="", questions={"q": {"type": "noul"}}))

        assert body.get_prompts() == []


class TestSystemOne:
    def test_should_parse_the_answers_of_the_three_question_types(self):
        result = SystemOne.model_validate(SystemOneResponseFactory())

        assert result.answers["urgency"].noul == 0.847606
        assert result.answers["department"].choice == "technical"
        assert result.answers["department"].confidence == 0.909974
        assert result.answers["severity"].score == 2.831772
        assert result.answers["severity"].legend["3"] == "losing money"

    def test_should_not_require_a_confidence(self):
        answers = SystemOneResponseFactory()["answers"]
        del answers["department"]["confidence"]

        result = SystemOne.model_validate(SystemOneResponseFactory(answers=answers))

        assert result.answers["department"].confidence is None

    def test_should_not_read_the_provider_usage_as_the_gateway_usage(self):
        result = SystemOne.model_validate(SystemOneResponseFactory())

        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0

    def test_should_generate_no_completion(self):
        assert SystemOne.model_validate(SystemOneResponseFactory()).get_completions() == []

    @pytest.mark.parametrize(
        "answer",
        [{"type": "noul"}, {"type": "choice", "choice": "a"}, {"type": "score", "score": 1.0}, {"type": "other", "noul": 1.0}],
        ids=["noul-without-probability", "choice-without-probabilities", "score-without-legend", "unknown-type"],
    )
    def test_should_reject_an_incomplete_answer(self, answer):
        with pytest.raises(ValidationError):
            SystemOne.model_validate(SystemOneResponseFactory(answers={"q": answer}))
