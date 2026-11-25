"""Detect automated tests that freeze raw documentation wording."""

import ast
from dataclasses import dataclass

_RAW_STRING_METHODS = {
    "casefold",
    "join",
    "lower",
    "lstrip",
    "removeprefix",
    "removesuffix",
    "replace",
    "rstrip",
    "split",
    "splitlines",
    "strip",
    "upper",
}
_CONTENT_PROBE_METHODS = {"count", "endswith", "find", "index", "startswith"}
_REGEX_PROBE_METHODS = {"fullmatch", "match", "search"}
_WORDING_COMPARE_OPERATORS = (ast.Eq, ast.NotEq, ast.In, ast.NotIn)
_TEMP_PATH_FIXTURES = frozenset(
    {"tmp_path", "tmpdir", "tmp_path_factory", "tmpdir_factory"}
)
_TEMP_PATH_METHODS = frozenset({"glob", "joinpath", "mktemp", "resolve", "rglob"})
_TEMP_PATH_CONSTRUCTORS = frozenset({"TemporaryDirectory", "mkdtemp"})


@dataclass(frozen=True)
class Violation:
    """One raw-document wording assertion."""

    filename: str
    line: int

    def __str__(self) -> str:
        """Render a location and actionable failure."""
        return (
            f"{self.filename}:{self.line}: raw documentation wording assertion; "
            "test processed behavior or move the expectation to a review rubric"
        )


def _mentions_markdown(module: ast.Module) -> bool:
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.lower().endswith(".md")
        for node in ast.walk(module)
    )


def _is_markdown_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.lower().endswith(".md")
    )


def _function_parameter_names(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    args = function.args
    parameters = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    return {parameter.arg for parameter in parameters}


def _is_temp_path_call(
    call: ast.Call,
    *,
    temp_path_names: set[str],
) -> bool:
    function = call.func
    if isinstance(function, ast.Name):
        if function.id in _TEMP_PATH_CONSTRUCTORS:
            return True
        return (
            function.id == "Path"
            and bool(call.args)
            and _is_temp_path_expression(
                call.args[0],
                temp_path_names=temp_path_names,
            )
        )
    if isinstance(function, ast.Attribute):
        if function.attr in _TEMP_PATH_CONSTRUCTORS:
            return True
        return function.attr in _TEMP_PATH_METHODS and _is_temp_path_expression(
            function.value,
            temp_path_names=temp_path_names,
        )
    return False


def _is_temp_path_expression(
    expression: ast.expr,
    *,
    temp_path_names: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in temp_path_names
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
        return _is_temp_path_expression(
            expression.left,
            temp_path_names=temp_path_names,
        )
    if isinstance(expression, ast.JoinedStr):
        return any(
            isinstance(value, ast.FormattedValue)
            and _is_temp_path_expression(
                value.value,
                temp_path_names=temp_path_names,
            )
            for value in expression.values
        )
    if isinstance(expression, ast.Call):
        return _is_temp_path_call(expression, temp_path_names=temp_path_names)
    return False


def _temp_with_names(
    node: ast.With | ast.AsyncWith,
    *,
    temp_path_names: set[str],
) -> set[str]:
    names: set[str] = set()
    for item in node.items:
        if item.optional_vars is not None and _is_temp_path_expression(
            item.context_expr,
            temp_path_names=temp_path_names,
        ):
            names.update(_assigned_names([item.optional_vars]))
    return names


def _temp_assigned_names(
    node: ast.AST,
    *,
    temp_path_names: set[str],
) -> set[str]:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        if node.value is None or not _is_temp_path_expression(
            node.value,
            temp_path_names=temp_path_names,
        ):
            return set()
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return _assigned_names(targets)
    if isinstance(node, (ast.For, ast.AsyncFor)):
        if _is_temp_path_expression(node.iter, temp_path_names=temp_path_names):
            return _assigned_names([node.target])
        return set()
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return _temp_with_names(node, temp_path_names=temp_path_names)
    return set()


def _temp_path_names_in_function(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    names = _function_parameter_names(function) & _TEMP_PATH_FIXTURES
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function):
            assigned = _temp_assigned_names(node, temp_path_names=names)
            if assigned and not assigned <= names:
                names.update(assigned)
                changed = True
    return names


def _is_document_path_expression(
    expression: ast.expr,
    *,
    document_path_names: set[str],
    temp_path_names: set[str],
) -> bool:
    if _is_temp_path_expression(expression, temp_path_names=temp_path_names):
        return False
    if _is_markdown_literal(expression):
        result = True
    elif isinstance(expression, ast.Name):
        result = expression.id in document_path_names
    elif isinstance(expression, ast.BinOp):
        result = _is_document_path_expression(
            expression.left,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
        ) or _is_document_path_expression(
            expression.right,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
        )
    elif isinstance(expression, ast.JoinedStr):
        result = any(_is_markdown_literal(value) for value in expression.values)
    elif isinstance(expression, ast.Call):
        function = expression.func
        is_path_constructor = (
            isinstance(function, ast.Name) and function.id == "Path"
        )
        is_path_enumerator = (
            isinstance(function, ast.Attribute)
            and function.attr in {"glob", "rglob"}
        )
        result = (is_path_constructor or is_path_enumerator) and any(
            _is_document_path_expression(
                argument,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
            )
            for argument in expression.args
        )
    else:
        result = False
    return result


def _assigned_names(targets: list[ast.expr]) -> set[str]:
    return {
        node.id
        for target in targets
        for node in ast.walk(target)
        if isinstance(node, ast.Name)
    }


def _module_document_path_names(module: ast.Module) -> set[str]:
    names: set[str] = set()
    assignments = [
        node
        for node in module.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    ]
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            value = assignment.value
            if value is None or not _is_document_path_expression(
                value,
                document_path_names=names,
                temp_path_names=set(),
            ):
                continue
            targets = (
                assignment.targets
                if isinstance(assignment, ast.Assign)
                else [assignment.target]
            )
            assigned = _assigned_names(targets)
            if not assigned <= names:
                names.update(assigned)
                changed = True
    return names


def _document_path_names_in_function(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    module_document_paths: set[str],
    temp_path_names: set[str],
) -> set[str]:
    names = set(module_document_paths)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if value is None or not _is_document_path_expression(
                    value,
                    document_path_names=names,
                    temp_path_names=temp_path_names,
                ):
                    continue
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                assigned = _assigned_names(targets)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                if not _is_document_path_expression(
                    node.iter,
                    document_path_names=names,
                    temp_path_names=temp_path_names,
                ):
                    continue
                assigned = _assigned_names([node.target])
            else:
                continue
            if not assigned <= names:
                names.update(assigned)
                changed = True
    return names


def _is_raw_text_expression(
    expression: ast.expr,
    *,
    document_path_names: set[str],
    temp_path_names: set[str],
    raw_names: set[str],
    raw_functions: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        result = expression.id in raw_names
    elif isinstance(expression, ast.Call):
        function = expression.func
        if isinstance(function, ast.Attribute) and function.attr == "read_text":
            result = _is_document_path_expression(
                function.value,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
            )
        elif (
            isinstance(function, ast.Attribute)
            and function.attr in _RAW_STRING_METHODS
        ):
            result = _is_raw_text_expression(
                function.value,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            ) or any(
                _is_raw_text_expression(
                    argument,
                    document_path_names=document_path_names,
                    temp_path_names=temp_path_names,
                    raw_names=raw_names,
                    raw_functions=raw_functions,
                )
                for argument in expression.args
            )
        else:
            result = isinstance(function, ast.Name) and function.id in raw_functions
    elif isinstance(expression, ast.BinOp):
        result = _is_raw_text_expression(
            expression.left,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        ) or _is_raw_text_expression(
            expression.right,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
    elif isinstance(expression, ast.Subscript):
        result = _is_raw_text_expression(
            expression.value,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
    elif isinstance(expression, ast.IfExp):
        result = _is_raw_text_expression(
            expression.body,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        ) or _is_raw_text_expression(
            expression.orelse,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
    else:
        result = False
    return result


def _raw_names_in_function(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    document_path_names: set[str],
    temp_path_names: set[str],
    raw_functions: set[str],
) -> set[str]:
    raw_names: set[str] = set()
    assignments = [
        node
        for node in ast.walk(function)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    ]
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            value = assignment.value
            if value is None or not _is_raw_text_expression(
                value,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            ):
                continue
            targets = (
                assignment.targets
                if isinstance(assignment, ast.Assign)
                else [assignment.target]
            )
            names = _assigned_names(targets)
            if not names <= raw_names:
                raw_names.update(names)
                changed = True
    return raw_names


def _raw_returning_functions(
    module: ast.Module,
    *,
    module_document_paths: set[str],
) -> set[str]:
    functions = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    raw_functions: set[str] = set()
    changed = True
    while changed:
        changed = False
        for function in functions:
            temp_path_names = _temp_path_names_in_function(function)
            document_path_names = _document_path_names_in_function(
                function,
                module_document_paths=module_document_paths,
                temp_path_names=temp_path_names,
            )
            raw_names = _raw_names_in_function(
                function,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
                raw_functions=raw_functions,
            )
            returns_raw = any(
                node.value is not None
                and _is_raw_text_expression(
                    node.value,
                    document_path_names=document_path_names,
                    temp_path_names=temp_path_names,
                    raw_names=raw_names,
                    raw_functions=raw_functions,
                )
                for node in ast.walk(function)
                if isinstance(node, ast.Return)
            )
            if returns_raw and function.name not in raw_functions:
                raw_functions.add(function.name)
                changed = True
    return raw_functions


def _uses_content_probe(
    expression: ast.expr,
    *,
    document_path_names: set[str],
    temp_path_names: set[str],
    raw_names: set[str],
    raw_functions: set[str],
) -> bool:
    for node in ast.walk(expression):
        if not isinstance(node, ast.Call) or not isinstance(
            node.func, ast.Attribute
        ):
            continue
        if node.func.attr in _CONTENT_PROBE_METHODS and _is_raw_text_expression(
            node.func.value,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        ):
            return True
        if node.func.attr in _REGEX_PROBE_METHODS and any(
            _is_raw_text_expression(
                argument,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            )
            for argument in node.args
        ):
            return True
    return False


def _is_wording_assertion(
    assertion: ast.Assert,
    *,
    document_path_names: set[str],
    temp_path_names: set[str],
    raw_names: set[str],
    raw_functions: set[str],
) -> bool:
    if _uses_content_probe(
        assertion.test,
        document_path_names=document_path_names,
        temp_path_names=temp_path_names,
        raw_names=raw_names,
        raw_functions=raw_functions,
    ):
        return True
    for comparison in ast.walk(assertion.test):
        if not isinstance(comparison, ast.Compare) or not any(
            isinstance(operator, _WORDING_COMPARE_OPERATORS)
            for operator in comparison.ops
        ):
            continue
        operands = [comparison.left, *comparison.comparators]
        if any(
            _is_raw_text_expression(
                operand,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            )
            for operand in operands
        ):
            return True
    return False


def find_prose_change_assertions(source: str, *, filename: str) -> list[Violation]:
    """Return obvious raw-document wording assertions in one Python test module.

    This is a bounded lint for supported AST shapes, not a proof that prose tests are
    absent or semantically independent.
    """
    module = ast.parse(source, filename=filename)
    if not _mentions_markdown(module):
        return []

    module_document_paths = _module_document_path_names(module)
    raw_functions = _raw_returning_functions(
        module,
        module_document_paths=module_document_paths,
    )
    violations: list[Violation] = []
    for function in ast.walk(module):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        temp_path_names = _temp_path_names_in_function(function)
        document_path_names = _document_path_names_in_function(
            function,
            module_document_paths=module_document_paths,
            temp_path_names=temp_path_names,
        )
        raw_names = _raw_names_in_function(
            function,
            document_path_names=document_path_names,
            temp_path_names=temp_path_names,
            raw_functions=raw_functions,
        )
        violations.extend(
            Violation(filename=filename, line=assertion.lineno)
            for assertion in ast.walk(function)
            if isinstance(assertion, ast.Assert)
            and _is_wording_assertion(
                assertion,
                document_path_names=document_path_names,
                temp_path_names=temp_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            )
        )
    return sorted(violations, key=lambda violation: violation.line)
