"""The background hook's JSON input/output and failure boundary."""

import json
import sys

from .checker import check
from .core import Finding, Unavailable, hook_output, question_from_event


def main() -> int:
    try:
        question = question_from_event(json.load(sys.stdin))
        result = {} if question is None else hook_output(check(question))
    except (Unavailable, ValueError, OSError) as error:
        result = hook_output(Finding(warning=str(error)))
    print(json.dumps(result))
    return 0
