"""Allow-list validator for user-supplied search expressions.

This replaces the hand-written deny-list in ``workers/eval.py``. That one
enumerated forbidden identifiers, which fails in two ways: anything not thought
of is permitted, and a mistake fails silently. It carried a live example --

    'exec', 'breakpoint', 'classmethod', 'compile'
    'delattr', 'dir', 'getattr', ...

a missing comma concatenated two entries into ``'compiledelattr'``, so neither
``compile`` nor ``delattr`` was blocked, and nothing complained.

This module inverts that: everything is rejected unless explicitly permitted.

WHAT THIS IS NOT
----------------
This is **not** a security boundary, and must never be treated as one. Sage is
far too large to sandbox at the Python level -- it touches the filesystem and
shells out to Singular, GAP, PARI and Maxima. The boundary is the container:
no network, read-only root, dropped capabilities, one forked child per
evaluation. See ``docs/design/eval-sandbox.md``.

What this *does* buy: it rejects the overwhelming majority of hostile input
cheaply, before Sage is involved, and gives honest users a clear error instead
of a traceback.

DESIGN NOTES
------------
Two properties do most of the work:

1. ``ast.Attribute`` is not allowed at all. Nearly every published Python
   sandbox escape goes through attribute traversal
   (``().__class__.__bases__[0].__subclasses__()``). No attribute access, no
   traversal. Legitimate search expressions do not need it.

2. The allowed-name set is *derived from the evaluation namespace* rather than
   maintained separately, so the validator and the executor cannot drift apart.
   A name that is not in the namespace is not callable, and a name added to the
   namespace is automatically permitted.

Validation runs on the **preparsed** source, so it must tolerate what Sage's
preparser emits: ``2^n`` becomes ``Integer(2)**n`` and ``[1..10]`` becomes
``ellipsis_range(Integer(1),Ellipsis,Integer(10))``. Those generated names live
in ``PREPARSER_NAMES``.
"""

import ast

__all__ = [
    'ExpressionRejected',
    'validate_expression',
    'PREPARSER_NAMES',
    'ALLOWED_NODES',
]


class ExpressionRejected(ValueError):
    """Raised when an expression is not permitted. Message is user-facing."""


#: Names Sage's preparser introduces. Rejecting these would break ordinary
#: input such as ``2^n`` or ``[1..10]``.
PREPARSER_NAMES = frozenset({
    'Integer', 'RealNumber', 'ellipsis_range', 'ellipsis_iter', 'Ellipsis',
})


#: Node types permitted anywhere in the tree. Everything absent is rejected,
#: including Attribute, Lambda, NamedExpr, Yield, Await, JoinedStr, Starred,
#: and every statement type other than a single bare expression.
ALLOWED_NODES = frozenset({
    ast.Expression, ast.Expr, ast.Module,
    # literals and containers
    ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Set,
    # comprehensions
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
    # operators
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UAdd, ast.USub, ast.Not,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    # names and calls
    ast.Name, ast.Load, ast.Store, ast.Call, ast.keyword,
})


# Bitwise operators are deliberately excluded: after preparsing, ``^`` has
# already become ``**``, so a surviving BitXor means the user wrote something we
# do not intend to support. Subscript is excluded for now -- no known legitimate
# use in search expressions -- and can be added if one appears.


def _describe(node):
    return type(node).__name__


def _check_name(name, allowed_names, node):
    if '__' in name:
        raise ExpressionRejected(
            "Names containing '__' are not allowed (found %r)." % (name,)
        )
    if name not in allowed_names:
        raise ExpressionRejected(
            "Unknown or not-allowed name %r. Only mathematical functions and "
            "constants provided by the search environment may be used." % (name,)
        )


def _comprehension_targets(generator):
    """Names bound by one comprehension generator's target."""
    names = set()
    target = generator.target
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, ast.Tuple):
        for element in target.elts:
            if not isinstance(element, ast.Name):
                raise ExpressionRejected(
                    "Only plain names may be used as loop variables."
                )
            names.add(element.id)
    else:
        raise ExpressionRejected("Unsupported loop variable.")
    for name in names:
        if '__' in name:
            raise ExpressionRejected(
                "Names containing '__' are not allowed (found %r)." % (name,)
            )
    return names


class _Validator:
    def __init__(self, allowed_names, max_nodes, max_depth):
        self.allowed_names = allowed_names
        self.max_nodes = max_nodes
        self.max_depth = max_depth
        self.node_count = 0

    def visit(self, node, bound, depth):
        self.node_count += 1
        if self.node_count > self.max_nodes:
            raise ExpressionRejected(
                "Expression is too large (limit %d nodes)." % (self.max_nodes,)
            )
        if depth > self.max_depth:
            raise ExpressionRejected(
                "Expression is nested too deeply (limit %d)." % (self.max_depth,)
            )
        if type(node) not in ALLOWED_NODES:
            raise ExpressionRejected(
                "%s is not allowed in search expressions." % (_describe(node),)
            )

        # Comprehensions introduce scope, so they are walked explicitly rather
        # than via generic child iteration.
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp,
                             ast.GeneratorExp)):
            return self._visit_comprehension(node, bound, depth)

        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                _check_name(node.id, self.allowed_names | bound, node)
            return

        if isinstance(node, ast.Call):
            return self._visit_call(node, bound, depth)

        for child in ast.iter_child_nodes(node):
            self.visit(child, bound, depth + 1)

    def _visit_call(self, node, bound, depth):
        # Only calls to bare allowed names. This rules out f()(), and -- since
        # Attribute is not an allowed node at all -- any method call.
        if not isinstance(node.func, ast.Name):
            raise ExpressionRejected(
                "Only direct calls to permitted functions are allowed."
            )
        _check_name(node.func.id, self.allowed_names | bound, node.func)
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                raise ExpressionRejected("Argument unpacking is not allowed.")
            self.visit(argument, bound, depth + 1)
        for kw in node.keywords:
            if kw.arg is None:
                raise ExpressionRejected("Keyword unpacking is not allowed.")
            self.visit(kw.value, bound, depth + 1)

    def _visit_comprehension(self, node, bound, depth):
        # The first generator's iterable is evaluated in the enclosing scope;
        # each subsequent one, and the conditions and element expressions, see
        # the variables bound so far.
        inner = set(bound)
        for index, generator in enumerate(node.generators):
            if generator.is_async:
                raise ExpressionRejected("Async comprehensions are not allowed.")
            self.visit(generator.iter, bound if index == 0 else inner, depth + 1)
            inner |= _comprehension_targets(generator)
            for condition in generator.ifs:
                self.visit(condition, inner, depth + 1)

        if isinstance(node, ast.DictComp):
            self.visit(node.key, inner, depth + 1)
            self.visit(node.value, inner, depth + 1)
        else:
            self.visit(node.elt, inner, depth + 1)


def validate_expression(source_python, namespace, *,
                        max_nodes=2000, max_depth=25, max_length=4096):
    """Validate already-preparsed Python source against ``namespace``.

    ``namespace`` is the mapping the expression will actually be evaluated in;
    its keys define which names are permitted. Passing the real namespace keeps
    the allow-list and the execution environment in step.

    Returns the parsed ``ast.Expression`` on success. Raises
    ``ExpressionRejected`` -- whose message is safe to show a user -- otherwise.
    """
    if not isinstance(source_python, str):
        raise ExpressionRejected("Expression must be text.")
    if len(source_python) > max_length:
        raise ExpressionRejected(
            "Expression is too long (limit %d characters)." % (max_length,)
        )
    if '\x00' in source_python:
        raise ExpressionRejected("Expression contains a null byte.")

    try:
        tree = ast.parse(source_python, mode='eval')
    except SyntaxError as error:
        raise ExpressionRejected("Could not parse expression: %s" % (error.msg,))

    allowed_names = frozenset(namespace) | PREPARSER_NAMES
    _Validator(allowed_names, max_nodes, max_depth).visit(tree, frozenset(), 0)
    return tree
