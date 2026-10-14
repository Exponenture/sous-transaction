from rest_framework import exceptions
from rest_framework.parsers import JSONParser

from transactions.validation import MAX_DEPTH


class DepthSafeJSONParser(JSONParser):
    """json.loads recurses, so a body nested ~1000+ deep raises RecursionError before our own
    iterative depth check runs. Report it like any other over-deep body (NOTES AM8b)."""

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return super().parse(stream, media_type, parser_context)
        except RecursionError:
            message = f"JSON nesting is deeper than {MAX_DEPTH} levels."
            raise exceptions.ValidationError({"body": [message]}) from None
