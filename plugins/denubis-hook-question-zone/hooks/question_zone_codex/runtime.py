"""The synchronous hook's JSON input/output and failure boundary."""

import json
import sys

from .checker import check
from .core import Rewrite, Unavailable, Verdict, hook_output, question_from_event


def main() -> int:
    try:
        question = question_from_event(json.load(sys.stdin))
        result = {} if question is None else hook_output(check(question))
    except Rewrite as error:
        result = hook_output(Verdict("rewrite", str(error)))
    except (Unavailable, ValueError, OSError) as error:
        result = hook_output(Verdict("unavailable", str(error)))
    print(json.dumps(result))
    return 0
