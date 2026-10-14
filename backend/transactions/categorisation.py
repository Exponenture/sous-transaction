"""Assign one of the 10 categories to a description: keyword rules (LLM comes in slice 2)."""

import re
from dataclasses import dataclass

from transactions.models import Transaction

Category = Transaction.Category
Source = Transaction.Source

# Checked in order; first match wins. Whole-word, case-insensitive (NOTES AM2).
RULES = [
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


def categorise(*, description: str | None, amount, transaction_type) -> Categorisation:
    if not description:
        return Categorisation(None, Source.NONE)
    return Categorisation(by_rules(description), Source.RULES, fell_back=True)
