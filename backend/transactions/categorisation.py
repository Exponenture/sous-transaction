"""Assign one of the 10 categories: Claude first, keyword rules as the fallback (NOTES AM1/AM2)."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import anthropic
from django.conf import settings

from transactions.models import Transaction

logger = logging.getLogger(__name__)

Category = Transaction.Category
Source = Transaction.Source

MODEL = "claude-haiku-5-5"
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "categorise.md").read_text()
OUTPUT_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": Category.values}},
        "required": ["category"],
        "additionalProperties": False,
    },
}

# Checked in order; first match wins. Whole-word, case-insensitive (NOTES AM2).
RULES = [
    # Money movements first: "Salary from School Employer" is not Education (NOTES AM7a).
    (
        Category.MISCELLANEOUS,
        ["salary", "payroll", "transfer", "refund", "atm", "withdrawal", "credit card"],
    ),
    (Category.DINING_OUT, ["restaurant", "cafe", "café", "thuisbezorgd", "uber eats", "deliveroo"]),
    (
        Category.GROCERIES,
        ["albert heijn", "ah", "groceries", "grocery", "supermarket", "jumbo", "lidl", "aldi"],
    ),
    (
        Category.UTILITIES,
        [
            "eneco",
            "vattenfall",
            "essent",
            "energy",
            "electricity",
            "gas",
            "water",
            "ziggo",
            "kpn",
            "t-mobile",
            "vodafone",
            "internet",
            "municipal",
        ],
    ),
    (
        Category.TRANSPORTATION,
        ["ns", "train", "car lease", "ov-chipkaart", "fuel", "parking", "taxi", "uber"],
    ),
    (
        Category.ENTERTAINMENT,
        ["netflix", "spotify", "disney+", "cinema", "pathé", "pathe", "concert", "theatre"],
    ),
    (
        Category.HEALTHCARE,
        ["pharmacy", "apotheek", "doctor", "huisarts", "dentist", "hospital", "health insurance"],
    ),
    (Category.SHOPPING, ["bol.com", "amazon", "zalando", "coolblue", "ikea", "hema"]),
    (Category.HOUSING, ["rent", "mortgage", "hypotheek", "landlord"]),
    (Category.EDUCATION, ["tuition", "university", "school", "course", "udemy", "coursera"]),
]
_PATTERNS = [
    (category, re.compile(r"(?<![\w])(?:" + "|".join(map(re.escape, words)) + r")(?![\w])", re.I))
    for category, words in RULES
]


@dataclass(frozen=True)
class Categorisation:
    category: str | None
    source: str
    fell_back: bool = False


def by_rules(description: str) -> str:
    for category, pattern in _PATTERNS:
        if pattern.search(description):
            return category.value
    return Category.MISCELLANEOUS.value


def by_llm(*, description: str, amount, transaction_type) -> str | None:
    """One Claude call, no retries. None on any failure; never sees account or owner."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    context = {
        "description": description,
        "amount": None if amount is None else str(amount),
        "transaction_type": transaction_type,
    }
    try:  # client construction included: it can fail too (NOTES AM7b)
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=5, max_retries=0)
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            thinking={"type": "disabled"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(context)}],
            output_config={"format": OUTPUT_FORMAT},
        )
        text = next(block.text for block in response.content if block.type == "text")
        category = json.loads(text)["category"]
    except Exception as exc:  # timeouts, API errors, refusals, malformed output: all fall back
        logger.warning("llm_categorisation_failed error=%s", type(exc).__name__)
        return None
    if category not in Category.values:
        logger.warning("llm_categorisation_off_list")
        return None
    return category


def categorise(*, description: str | None, amount, transaction_type) -> Categorisation:
    if not description:
        return Categorisation(None, Source.NONE)
    category = by_llm(description=description, amount=amount, transaction_type=transaction_type)
    if category is not None:
        return Categorisation(category, Source.LLM)
    return Categorisation(by_rules(description), Source.RULES, fell_back=True)
