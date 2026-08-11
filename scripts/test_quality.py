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
_WORDING_COMPARE_OPERATORS = (ast.Eq, ast.NotEq, ast.In, ast.NotIn)


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


def _is_document_path_expression(
    expression: ast.expr,
    *,
    document_path_names: set[str],
) -> bool:
    if _is_markdown_literal(expression):
        result = True
    elif isinstance(expression, ast.Name):
        result = expression.id in document_path_names
    elif isinstance(expression, ast.BinOp):
        result = _is_document_path_expression(
            expression.left,
            document_path_names=document_path_names,
        ) or _is_document_path_expression(
            expression.right,
            document_path_names=document_path_names,
        )
    elif isinstance(expression, ast.JoinedStr):
        result = any(_is_markdown_literal(value) for value in expression.values)
    elif (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr
        in {
            "glob",
            "rglob",
        }
    ):
        result = any(
            _is_document_path_expression(
                argument,
                document_path_names=document_path_names,
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
            )
        elif (
            isinstance(function, ast.Attribute)
            and function.attr in _RAW_STRING_METHODS
        ):
            result = _is_raw_text_expression(
                function.value,
                document_path_names=document_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            ) or any(
                _is_raw_text_expression(
                    argument,
                    document_path_names=document_path_names,
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
            raw_names=raw_names,
            raw_functions=raw_functions,
        ) or _is_raw_text_expression(
            expression.right,
            document_path_names=document_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
    elif isinstance(expression, ast.Subscript):
        result = _is_raw_text_expression(
            expression.value,
            document_path_names=document_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
    elif isinstance(expression, ast.IfExp):
        result = _is_raw_text_expression(
            expression.body,
            document_path_names=document_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        ) or _is_raw_text_expression(
            expression.orelse,
            document_path_names=document_path_names,
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
            document_path_names = _document_path_names_in_function(
                function,
                module_document_paths=module_document_paths,
            )
            raw_names = _raw_names_in_function(
                function,
                document_path_names=document_path_names,
                raw_functions=raw_functions,
            )
            returns_raw = any(
                node.value is not None
                and _is_raw_text_expression(
                    node.value,
                    document_path_names=document_path_names,
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
    raw_names: set[str],
    raw_functions: set[str],
) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _CONTENT_PROBE_METHODS
        and _is_raw_text_expression(
            node.func.value,
            document_path_names=document_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
        for node in ast.walk(expression)
    )


def _is_wording_assertion(
    assertion: ast.Assert,
    *,
    document_path_names: set[str],
    raw_names: set[str],
    raw_functions: set[str],
) -> bool:
    if _uses_content_probe(
        assertion.test,
        document_path_names=document_path_names,
        raw_names=raw_names,
        raw_functions=raw_functions,
    ):
        return True
    if not isinstance(assertion.test, ast.Compare):
        return False
    if not any(
        isinstance(operator, _WORDING_COMPARE_OPERATORS)
        for operator in assertion.test.ops
    ):
        return False
    operands = [assertion.test.left, *assertion.test.comparators]
    return any(
        _is_raw_text_expression(
            operand,
            document_path_names=document_path_names,
            raw_names=raw_names,
            raw_functions=raw_functions,
        )
        for operand in operands
    )


def find_prose_change_assertions(source: str, *, filename: str) -> list[Violation]:
    """Return raw-document wording assertions in one Python test module."""
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
        document_path_names = _document_path_names_in_function(
            function,
            module_document_paths=module_document_paths,
        )
        raw_names = _raw_names_in_function(
            function,
            document_path_names=document_path_names,
            raw_functions=raw_functions,
        )
        violations.extend(
            Violation(filename=filename, line=assertion.lineno)
            for assertion in ast.walk(function)
            if isinstance(assertion, ast.Assert)
            and _is_wording_assertion(
                assertion,
                document_path_names=document_path_names,
                raw_names=raw_names,
                raw_functions=raw_functions,
            )
        )
    return sorted(violations, key=lambda violation: violation.line)
