from pydoctor.epydoc.doctest import colorize_codeblock, colorize_doctest
from pydoctor.epydoc.markup import flatten


def test_colorize_codeblock() -> None:
    src = '''
def foo():
    """A multi-line docstring.

    The "doc" part doesn't matter for this test,
    but the "string" part does.
    """
    return list({1, 2, 3})

class Foo:
    def __init__(self):
        # Nothing to do.
        pass
'''.lstrip()
    expected = '''
<pre class="py-doctest">
<span class="py-keyword">def</span> <span class="py-defname">foo</span>():
    <span class="py-string">"""A multi-line docstring.</span>

<span class="py-string">    The "doc" part doesn't matter for this test,</span>
<span class="py-string">    but the "string" part does.</span>
<span class="py-string">    """</span>
    <span class="py-keyword">return</span> <span class="py-builtin">list</span>({1, 2, 3})

<span class="py-keyword">class</span> <span class="py-defname">Foo</span>:
    <span class="py-keyword">def</span> <span class="py-defname">__init__</span>(self):
        <span class="py-comment"># Nothing to do.</span>
        <span class="py-keyword">pass</span>
</pre>
'''.strip()
    assert flatten(colorize_codeblock(src)) == expected

def test_colorize_doctest_more_string() -> None:
    src = '''
Test multi-line string:

    >>> """A
    ... B
    ... C"""
    'A\\nB\\nC'
'''.lstrip()
    expected = '''
<pre class="py-doctest">
Test multi-line string:

<span class="py-prompt">    &gt;&gt;&gt; </span><span class="py-string">"""A</span>
<span class="py-more">    ... </span><span class="py-string">B</span>
<span class="py-more">    ... </span><span class="py-string">C"""</span>
<span class="py-output">    'A\\nB\\nC'</span>
</pre>
'''.strip()
    assert flatten(colorize_doctest(src)) == expected

def test_colorize_doctest_more_input() -> None:
    src = '''
Test multi-line expression:

    >>> [chr(i + 65)
    ...  for i in range(26)
    ...  if i % 2 == 0]
    ['A', 'C', 'E', 'G', 'I', 'K', 'M', 'O', 'Q', 'S', 'U', 'W', 'Y']
'''.lstrip()
    expected = '''
<pre class="py-doctest">
Test multi-line expression:

<span class="py-prompt">    &gt;&gt;&gt; </span>[<span class="py-builtin">chr</span>(i + 65)
<span class="py-more">    ... </span> <span class="py-keyword">for</span> i <span class="py-keyword">in</span> <span class="py-builtin">range</span>(26)
<span class="py-more">    ... </span> <span class="py-keyword">if</span> i % 2 == 0]
<span class="py-output">    ['A', 'C', 'E', 'G', 'I', 'K', 'M', 'O', 'Q', 'S', 'U', 'W', 'Y']</span>
</pre>
'''.strip()
    assert flatten(colorize_doctest(src)) == expected

def test_colorize_doctest_exception() -> None:
    src = '''
Test division by zero:

    >>> 1/0
    Traceback (most recent call last):
    ZeroDivisionError: integer division or modulo by zero
'''.lstrip()
    expected = '''
<pre class="py-doctest">
Test division by zero:

<span class="py-prompt">    &gt;&gt;&gt; </span>1/0
<span class="py-except">    Traceback (most recent call last):</span>
<span class="py-except">    ZeroDivisionError: integer division or modulo by zero</span>
</pre>
'''.strip()
    assert flatten(colorize_doctest(src)) == expected

def test_colorize_doctest_no_output() -> None:
    src = '''
Test expecting no output:

    >>> None
'''.lstrip()
    expected = '''
<pre class="py-doctest">
Test expecting no output:

<span class="py-prompt">    &gt;&gt;&gt; </span><span class="py-builtin">None</span>
</pre>
'''.strip()
    assert flatten(colorize_doctest(src)) == expected
