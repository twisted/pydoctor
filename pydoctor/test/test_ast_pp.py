# this is not stolen from exarkun's sandbox; he didn't seem to write
# any tests :)

from pydoctor import ast_pp
from compiler.transformer import parse

from hypothesis import strategies as st, assume, given, settings, HealthCheck

import string


def identifiers():
    """
    Create a L{hypothesis} strategy that generates valid Python
    identifiers.

    @return: A strategy that generates L{str}
    """
    keywords = {"and", "del", "from", "not", "while", "as", "elif",
                "global", "or", "with", "assert", "else", "if",
                "pass", "yield", "break", "except", "import", "print",
                "class", "exec", "in", "raise", "continue", "finally",
                "is", "return", "def", "for", "lambda", "try",
                "async", "await"}
    return st.from_regex(b"\A[_a-zA-Z][_a-zA-Z0-9]*\Z").filter(
        lambda i: i not in keywords
    )


def attributes():
    """
    Create a L{hypothesis} strategy that generates sequences of
    attribute accesses, e.g. C{a.b.c.d}.

    @return: A strategy that generates L{str}
    """
    return st.lists(identifiers(), min_size=1, max_size=5).map(".".join)


def builtins():
    """
    Create a L{hypothesis} strategy that generates the names of
    C{__builtin__}s.

    @return: A strategy that generates L{str}
    """
    bltnsDict = __builtins__
    if not isinstance(bltnsDict, dict):
        bltnsDict = __builtins__.__dict__
    bltns = [name for name in bltnsDict if name not in {"print"}]
    return st.sampled_from(bltns)


def stringLiterals():
    """
    Create a L{hypothesis} strategy that generates ASCII string
    literals.

    @return: A strategy that generates L{str}
    """
    return st.text(
        alphabet=string.ascii_lowercase + string.ascii_uppercase
    ).map(repr)


def numericLiterals():
    """
    Create a L{hypothesis} strategy that generates ASCII string
    literals.

    @return: A strategy that generates L{str}
    """

    return (st.integers() | st.floats()).map(repr)


def tupleLiterals(literals, min_size=0, max_size=5):
    """
    Create a L{hypothesis} strategy that generates L{tuple} literals

    @param literals: A strategy used to generated the tuples' members.

    @param min_size: (optional) The minimum length of the generated
        tuples.

    @param max_size: (optional) The max length of the generated
        tuples.

    @return: A strategy that generates L{str}
    """
    def joinMaybeWithTrailingComma(members):
        joined = ", ".join(members)
        if len(members) == 1:
            joined += ','
        return joined

    return st.lists(literals, min_size=min_size, max_size=max_size).map(
        lambda l: "(%s)" % (joinMaybeWithTrailingComma(l),))


def listLiterals(literals, min_size=0, max_size=5):
    """
    Create a L{hypothesis} strategy that generates L{list} literals.

    @param literals: A strategy used to generated the lists' members.

    @param min_size: (optional) The minimum length of the generated
        lists

    @param max_size: (optional) The max length of the generated lists.

    @return: A strategy that generates L{str}
    """
    return st.lists(literals, min_size=min_size, max_size=max_size).map(
        lambda l: "[%s]" % (", ".join(l),))


def setLiterals(literals, min_size=0, max_size=5):
    """
    Create a L{hypothesis} strategy that generates L{list} literals.

    @param literals: A strategy used to generated the lists' members.

    @param min_size: (optional) The minimum length of the generated
        lists

    @param max_size: (optional) The max length of the generated lists.

    @return: A strategy that generates L{str}
    """
    return st.lists(literals, min_size=min_size, max_size=max_size).map(
        lambda l: "{%s}" % (", ".join(l),))


def dictLiterals(keys, values, min_size=0, max_size=5):
    """
    Create a L{hypothesis} strategy that generates dict literals.

    @param literals: A strategy used to generated the lists' members.

    @param min_size: (optional) The minimum length of the generated
        lists.

    @param max_size: (optional) The max length of the generated lists.

    @return: A strategy that generates L{str}
    """
    return st.lists(
        st.tuples(keys, values),
        min_size=0,
        max_size=5,
    ).map(
        lambda l: "{%s}" % (", ".join("%s: %s" % kv for kv in l),)
    )


def literals(min_size=0):
    """
    Create a L{hypothesis} strategy that generates literals.

    @param min_size: (optional) The minimum length of generated L{tuple}
        and L{list} literals.

    @return: A strategy that generates L{str}
    """
    return (
        numericLiterals()
        | stringLiterals()
        | tupleLiterals(stringLiterals(), min_size=min_size)
        | listLiterals(stringLiterals(), min_size=min_size)
        | setLiterals(stringLiterals(), min_size=min_size)
        | dictLiterals(keys=stringLiterals(), values=stringLiterals())
    )


@st.composite
def subscriptedLiteral(
        draw,
        sequences=(
            stringLiterals()
            | listLiterals(stringLiterals())
            | tupleLiterals(stringLiterals())
            | dictLiterals(keys=stringLiterals(), values=stringLiterals())
        ),
        indices=st.lists(
            st.integers().map(repr) | st.just(""),
            min_size=1, max_size=2,
        ),
):
    """
    A L{hypothesis} strategy that generates subscripted sequence
    literals.  Subscripts can include slices.

    @return: A strategy that generates L{str}
    """

    slice = draw(indices)
    assume(slice != [""])
    return "%s[%s]" % (draw(sequences), ":".join(slice))


def arithmeticOperators():
    """
    Create a L{hypothesis} strategy that generates arithmetic
    operators.

    @return: A strategy that generates L{str}
    """
    return st.sampled_from(["*", "+", "-", "**", "%"])


def arithmeticExpressions():
    """
    Create a L{hypothesis} strategy that generates arithmetic
    expressions.

    @return: A strategy that generates L{str}
    """
    _expr = st.deferred(
        lambda: (
            numericLiterals()
            | st.tuples(_expr, arithmeticOperators(), _expr).map(" ".join)
        ))
    return _expr


@st.composite
def assignments(
        draw,
        identifiers=identifiers() | attributes(),
        expressions=arithmeticExpressions(),
        literals=literals(min_size=1),
):
    """
    A L{hypothesis} strategy that generates assignment statements.
    Assignments can include unpacking.

    @return: A strategy that generates L{str}
    """
    tuplesOfIdentifiers = tupleLiterals(identifiers, min_size=1)

    return draw(st.tuples(
        (identifiers
         | tuplesOfIdentifiers),
        st.just('='),
        (expressions
         | literals)
    ).map(" ".join))


@st.composite
def augmentedAssignments(
        draw,
        identifiers=identifiers() | attributes(),
        expressions=arithmeticExpressions(),
        operators=st.sampled_from([
            "=", "-=", "+=", "*=", "/=", "**=",
        ]),
        literals=literals(min_size=1),
):
    """
    A L{hypothesis} strategy that generates augmented assignment
    statements (e.g, C{a += 1}).

    @return: A strategy that generates L{str}
    """
    return draw(st.tuples(
        (identifiers),
        operators,
        (expressions | literals)
    ).map(" ".join))


@st.composite
def tryFinally(
        draw,
        expressions=(
            stringLiterals()
            | arithmeticExpressions()
            | subscriptedLiteral()
        ),
):
    """
    A L{hypothesis} strategy that generates C{try} C{finally}.

    @return: A strategy that generates L{str}
    """
    stmt = ("try:\n"
            "    %s\n"
            "finally:\n"
            "    %s" % (draw(expressions),
                        draw(expressions)))
    return stmt


def booleanExpressions(
        operators=st.sampled_from(
            ["<", ">", "==", "!=", ">=", "<="],
        ),
        operands=(
            literals()
            | identifiers()
            | st.sampled_from(["True", "False"])
        ),
):
    """
    Create a L{hypothesis} strategy that generates boolean
    expressions.

    @return: A strategy that generates L{str}
    """
    return st.deferred(
        lambda:
        st.tuples(operands, operators, operands)
        | st.tuples(booleanExpressions(), operators, booleanExpressions())
    ).map(" ".join)


@st.composite
def ifStatement(
        draw,
        booleanOps=booleanExpressions(),
        elifs=st.integers(min_value=0, max_value=5),
        hasElse=st.booleans(),
        bodies=st.deferred(lambda: execableBodies())
):
    """
    A L{hypothesis} strategy that generates C{if} statements with
    C{elif}s and C{else}s sometimes.

    @return: A strategy that generates L{str}
    """
    stmt = []

    def ifish(condition):
        stmt.append(condition)
        stmt.append("\n    ".join([""] + draw(bodies)))
        stmt.append("\n")

    ifish("if %s:" % (draw(booleanOps,)))

    for _ in range(draw(elifs)):
        ifish("elif %s:" % (draw(booleanOps,)))

    if hasElse:
        ifish("else:")

    return "".join(stmt[:-1])


def _modulesWithAliases(modules, min_size=1, max_size=5):
    """
    Create a L{hypothesis} strategy that generates modules with
    optional aliases (C{a.b.c, d.e as f, ...})

    @param modules: A L{hypothesis} strategy for generating modules

    @param min_size: (optional) The minimum length of the generated
        import lists.

    @param max_size: (optional) The max length of the generated import
        lists.

    @return: A strategy that generates L{str}
    """
    def fmt(moduleAndAlias):
        module, alias = moduleAndAlias
        if alias:
            return "%s as %s" % moduleAndAlias
        return module

    modulesAndAliases = st.tuples(
        modules,
        identifiers()
        | st.just(None)
    ).map(fmt)

    return st.lists(
        modulesAndAliases,
        min_size=min_size,
        max_size=max_size,
    ).map(", ".join)


@st.composite
def importStatements(draw, imports=_modulesWithAliases(modules=attributes())):
    """
    A L{hypothesis} strategy that generates C{import} statements with
    aliases (C{import ... as ...}) occasionally.

    @return: A strategy that generates L{str}
    """
    return 'import ' + draw(imports)


@st.composite
def importFromStatements(
        draw,
        modules=attributes(),
        imports=_modulesWithAliases(modules=identifiers()),
):
    """
    A L{hypothesis} strategy that generates C{from ... import}
    statements with aliases (C{from ... import ... as ...})
    occasionally.

    @return: A strategy that generates L{str}
    """
    return "from %s import %s" % (draw(modules), draw(imports))


@st.composite
def returnStatements(draw, maybeIdentifiers=identifiers() | st.just(None)):
    """
    A L{hypothesis} strategy that generates C{return} statements.

    @return: A strategy that generates L{str}
    """
    maybeIdentifier = draw(maybeIdentifiers)
    stmt = "return"
    if maybeIdentifier:
        stmt += " %s" % (maybeIdentifier,)
    return stmt


@st.composite
def raiseStatement(
        draw,
        exceptions=st.sampled_from(["", " Exception", " ValueError"]),
        values=identifiers() | st.just(None),
        tracebacks=identifiers() | st.just(None)
):
    """
    A L{hypothesis} strategy that generates C{raise} statements.

    @return: A strategy that generates L{str}
    """
    exc = draw(exceptions)
    stmt = "raise%s" % (exc,)
    if exc:
        value = draw(values)
        if value:
            stmt += ", %s" % (value,)
        tb = draw(tracebacks)
        if tb:
            stmt += ", %s" % (tb,)
    return stmt


@st.composite
def printStatement(
        draw,
        destinations=identifiers() | st.just(None),
        things=st.lists(
            literals()
            | identifiers()
            | attributes(),
            max_size=5
        ),
):
    """
    A L{hypothesis} strategy that generates C{print} statements that
    have destinations (C{print >>thing}).

    @return: A strategy that generates L{str}
    """
    stmt = "print "
    toPrint = draw(things)
    if toPrint:
        destination = draw(destinations)
        if destination:
            stmt += ">>%s, " % (destination,)

    stmt += ", ".join(toPrint)
    return stmt


@st.composite
def comprehension(
        draw,
        markers,
        identifiers=identifiers(),
        iterables=st.lists(
            identifiers()
            | attributes()
            | tupleLiterals(stringLiterals()),
            min_size=1,
            max_size=5,
        ),
        filters=st.lists(booleanExpressions(), max_size=5)
):
    """
    A L{hypothesis} strategy that generates comprehension expressions.

    @return: A strategy that generates L{str}
    """

    iters = draw(iterables)
    ids = [draw(identifiers) for _ in iters]
    pairs = iter(zip(ids, iters))
    id, it = next(pairs)
    fors = ["%s for %s in %s" % (id, id, it)]

    fors.extend("for %s in %s" % vi for vi in pairs)

    ifs = ['if %s' % (condition,) for condition in draw(filters)]
    if ifs:
        ifs.insert(0, " ")

    return "%s%s%s%s" % (
        markers[0], " ".join(fors), " ".join(ifs), markers[1]
    )


def listComprehension():
    """
    A L{hypothesis} strategy that generates list comprehensions.

    @return: A strategy that generates L{str}
    """
    return comprehension('[]')


@st.composite
def arguments(
        draw,
        positionals=st.lists(identifiers(), max_size=5),
):
    """
    A L{hypothesis} strategy that generates the arguments component of
    function signatures C{(a, b)}.

    @return: A strategy that generates L{str}
    """
    return ', '.join(draw(positionals))


@st.composite
def lambdaDef(
        draw,
        arguments=arguments() | st.just(""),
        bodies=(
            builtins()
            | literals()
            | arithmeticExpressions()
            | listComprehension()
            | st.deferred(lambda: lambdaDef())
            | st.deferred(lambda: callFunction())
            | st.just(repr(None))
        )
):
    """
    A L{hypothesis} strategy that generates C{lambda} definitions.

    @return: A strategy that generates L{str}
    """
    return "lambda %s: %s" % (draw(arguments), draw(bodies))


def execableBodies():
    """
    Create a L{hypothesis} strategy that generates statements and
    expressions suitable for inclusing in a statement that can be
    C{exec}'d

    @return: A strategy that generates L{list}s of L{str}
    """
    return st.lists(
        builtins()
        | literals()
        | arithmeticExpressions()
        | subscriptedLiteral()
        | attributes()
        | assignments()
        | augmentedAssignments()
        | tryFinally()
        | raiseStatement()
        | importStatements()
        | importFromStatements()
        | ifStatement()
        | printStatement()
        | listComprehension()
        | st.deferred(lambda: lambdaDef())
        | st.deferred(lambda: functionDef(join=False))
        | st.deferred(lambda: classDef())
        | st.deferred(lambda: callFunction())
        | st.deferred(lambda: forLoop())
        | st.just(repr(None)),
        min_size=1,
        max_size=5,
    ).map(lambda body: "\n".join(body).splitlines())


@st.composite
def forLoop(
        draw,
        variables=identifiers() | tupleLiterals(identifiers(), min_size=1),
        iterables=(
            identifiers()
            | attributes()
            | tupleLiterals(stringLiterals())
        ),
        bodies=execableBodies(),
        hasElse=st.booleans(),
):
    """
    A L{hypothesis} strategy that generates C{for} loops.

    @return: A strategy that generates L{str}
    """
    variable = draw(variables)
    iterable = draw(iterables)
    body = "\n    ".join([""] + draw(bodies))
    stmt = ("for %s in %s:"
            "    %s" % (variable, iterable, body))
    if draw(hasElse):
        elseBody = "\n    ".join([""] + draw(bodies))
        stmt += ("\n"
                 "else:\n"
                 "    %s" % (elseBody))
    return stmt


@st.composite
def functionDef(
        draw,
        join=True,
        docstrings=stringLiterals() | st.just(None),
        name=identifiers(),
        arguments=arguments() | st.just(""),
        bodies=execableBodies(),
        maybeReturn=returnStatements() | st.just(None)
):
    """
    A L{hypothesis} strategy that function definitions.

    @return: A strategy that generates L{str}
    """
    preamble = "def %s(%s):" % (draw(name), draw(arguments))

    docstring = draw(docstrings)
    if docstring:
        preamble += "\n    %s" % (docstring,)

    body = draw(bodies)
    returnStatement = draw(maybeReturn)
    if returnStatement:
        body.append(returnStatement)
    return preamble + "\n    ".join([""] + body)


@st.composite
def callFunction(
        draw,
        name=identifiers(),
        arguments=st.lists(identifiers(), max_size=5),
):
    """
    A L{hypothesis} strategy that generates callable calls
    C{callable(...)}.

    @return: A strategy that generates L{str}
    """
    return "%s(%s)" % (
        draw(name),
        ", ".join(draw(arguments)),
    )


@st.composite
def classDef(
        draw,
        classNames=identifiers(),
        docstrings=stringLiterals() | st.just(None),
        baseNames=(
            st.lists(
                identifiers()
                | attributes(),
                min_size=1,
                max_size=3
            )
            | st.lists(st.sampled_from(["object", ""]), max_size=1)
        ),
        bodies=execableBodies(),
):
    """
    A L{hypothesis} strategy that generates C{class} definitions.

    @return: A strategy that generates L{str} """

    name = draw(classNames)
    bases = draw(baseNames)
    if bases:
        stmt = "class %s(%s):" % (name, ", ".join(bases))
    else:
        stmt = "class %s:" % (name,)

    docstring = draw(docstrings)
    if docstring:
        stmt += "\n    %s" % (docstring,)

    return stmt + "\n    ".join([""] + draw(bodies))


@st.composite
def moduleDef(
        draw,
        docstring=stringLiterals() | st.just(None),
        bodies=execableBodies(),
):
    """
    A L{hypothesis} strategy that generates modules.

    @return: A strategy that generates L{str}
    """
    docstring = draw(docstring)
    module = "%s\n" % (docstring,) if docstring else ''
    module += "\n".join(draw(bodies))
    return module + "\n"


def assertRoundTrippable(source):
    """
    Assert that source is parsed the same after being printed by
    ast_pp.pp.
    """
    raw_tree = parse(source)
    ast_pp_source = ast_pp.pp(raw_tree)
    ast_pp_tree = parse(ast_pp_source)
    assert repr(raw_tree) == repr(ast_pp_tree), "%s != %s" % (
        source, ast_pp_source
    )


@settings(
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
@given(source=moduleDef())
def test_variations(source):
    assertRoundTrippable(source)
