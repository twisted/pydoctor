"""
General epytext formating markups are documented here.

Epydoc code related formating are demonstrated in the L{demo_epytext_module}.

Read the U{the epytext manual <http://epydoc.sourceforge.net/manual-epytext.html>} for more documentation.

Scope and Purpose
=================

Sample package for describing and demonstrating C{pydoctor} HTML API rendering for B{Epytext} based documentation.

Many examples are copied from U{the epytext manual <http://epydoc.sourceforge.net/manual-epytext.html>}.

Try to keep the example as condensed as possible.

    - Make  it easy to review HTML rendering.

    - Cover all epytext markup.
    Like the usage of list with various indentation types.

    - Have it build as part of our continuous integration tests.
      To ensure we don't introduce regressions.

Lists
=====

Epytext supports both ordered and unordered lists.
A list consists of one or more consecutive list items with the same indentation.
Each list item is marked by a bullet.
The bullet for unordered list items is a single dash character (C{-}).
Bullets for ordered list items consist of a series of numbers followed by periods,
such as C{12.} or C{1.2.8.}.

Ordered list example:

    1. This is an ordered list item.

    2. This is a another ordered list
    item.

    3. This is a third list item.  Note that
       the paragraph may be indented more
       than the bullet.

Example of unordered list:

    - This is an ordered list item.

    - This is a another ordered list
    item.

Example of complex list:

    1. This is a list item.
      - This is a sublist.
      - The sublist contains two
        items.
          - The second item of the
            sublist has its own sublist.

    2. This list item contains two
       paragraphs and a doctest block.

       >>> print 'This is a doctest block'
       This is a doctest block

       This is the second paragraph.


Literal Blocks
==============

Literal blocks are used to represent "preformatted" text.
Everything within a literal block should be displayed exactly as it appears in plaintext.

    - Spaces and newlines are preserved.
    - Text is shown in a monospaced font.
    - Inline markup is not detected.

Literal blocks are introduced by paragraphs ending in the special sequence C{::}.
Literal blocks end at the first line whose indentation is equal to or less than that of the paragraph that introduces them.

The following is a literal block::

    Literal /
           / X{Block}


Doctest Blocks
==============

    - contain examples consisting of Python expressions and their output
    - can be used by the doctest module to test the documented object
    - begin with the special sequence C{>>>}
    - are delimited from surrounding blocks by blank lines
    - may not contain blank lines

The following is a doctest block:

    >>> print (1+3,
    ...        3+5)
    (4, 8)
    >>> 'a-b-c-d-e'.split('-')
    ['a', 'b', 'c', 'd', 'e']

This is a paragraph following the doctest block.


Basic Inline Markup
===================

I{B{Inline markup} may be nested; and
it may span} multiple lines.

Epytext defines four types of inline markup that specify how text should be displayed:

    - I{Italicized text}
    - B{Bold-faced text}
    - C{Source code}
    - M{Math}

In the raw source file this list looks like this::

    - I{Italicized text}
    - B{Bold-faced text}
    - C{Source code}
    - M{Math}


Without the capital letter, matching
braces are not interpreted as markup:
C{my_dict={1:2, 3:4}}.


URLs
====

The inline markup construct U{text<url>} is used to create links to external URLs and URIs.
'text' is the text that should be displayed for the link, and 'url' is the target of the link.
If you wish to use the URL as the text for the link, you can simply write "U{url}".
Whitespace within URL targets is ignored.
In particular, URL targets may be split over multiple lines.
The following example illustrates how URLs can be used:

    - U{www.python.org}
    - U{http://www.python.org}
    - U{The epydoc homepage<http://
    epydoc.sourceforge.net>}
    - U{The B{Python} homepage
    <www.python.org>}
    - U{Edward Loper<mailto:edloper@
    gradient.cis.upenn.edu>}


Symbols
=======

Symbols are used to insert special characters in your documentation.
A symbol has the form SE{lb}codeE{rb},
where code is a symbol code that specifies what character should be produced.

Symbols can be used in equations: S{sum}S{alpha}/x S{<=} S{beta}

S{<-} and S{larr} both give left
arrows.  Some other arrows are
S{rarr}, S{uarr}, and S{darr}.


Escaping
========

Escaping is used to write text that would otherwise be interpreted as epytext
markup. Escaped text has the form C{EE{lb}textE{rb}}, where C{text} specifies
the character that should be produced.

For example, to begin a paragraph with a dash (which would normally signal
a list item), write C{EE{lb}-E{rb}} in the source file. As an
exception, special escape codes are defined for opening and closing curly
braces: C{EE{lb}lbE{rb}} produces a left curly brace (E{lb});
and C{EE{lb}rbE{rb}} produces a right curly brace (E{rb}).

This paragraph ends with two
colons, but does not introduce
a literal blockE{:}E{:}

E{-} This is not a list item.

Escapes can be used to write
unmatched curly braces:
E{rb}E{lb}

"""
