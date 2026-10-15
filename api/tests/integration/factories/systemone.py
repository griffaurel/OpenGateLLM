import factory

# The documented example of a System One server (Colibrì, `docs/systemone.md` @ bf24429), which copies the API of Jev (TypeSafe).
# Not recorded from a running server: keep it faithful to the documentation when it changes.
SYSTEMONE_QUESTIONS = {
    "urgency": {"type": "noul", "instructions": "Does this message express urgency?"},
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {
            "billing": "payments, invoices, Stripe payouts",
            "technical": "bugs, outages, integration errors",
            "sales": "pricing, plans, upgrades",
        },
    },
    "severity": {
        "type": "score",
        "instructions": "How severe is the customer impact?",
        "criteria": ["no impact", "minor inconvenience", "blocked on one task", "losing money", "business down"],
    },
}
SYSTEMONE_STATE = (
    "Hi, I have been trying to connect my Stripe account for 3 days and the integration keeps failing. I am losing sales. Please help ASAP."  # noqa: E501
)


class SystemOneResponseFactory(factory.DictFactory):
    _status_code = 200

    id = "req_5f0c0a8c2d9e4b7f8a1b"
    model = "qwen36"
    provider = "colibri"
    answers = factory.LazyFunction(
        lambda: {
            "urgency": {"type": "noul", "noul": 0.847606},
            "department": {
                "type": "choice",
                "choice": "technical",
                "probabilities": {"billing": 0.059806, "technical": 0.939983, "sales": 0.000211},
                "confidence": 0.909974,
            },
            "severity": {
                "type": "score",
                "score": 2.831772,
                "legend": {"0": "no impact", "1": "minor inconvenience", "2": "blocked on one task", "3": "losing money", "4": "business down"},
                "probabilities": {"0": 0.044403, "1": 0.02624, "2": 0.034899, "3": 0.842097, "4": 0.052361},
                "confidence": 0.802621,
            },
        }
    )
    usage = factory.LazyFunction(lambda: {"input_tokens": 86, "output_tokens": 15, "cost": 0})
