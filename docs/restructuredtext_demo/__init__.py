r"""
Few general reStructuredText formating markups are documented here. 

reStructuredText code related formating are demonstrated in the `demo_restructuredtext_module`. 

Many examples are copied from `the docutils quickref 
<https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_.

Scope and Purpose
=================

Sample package for describing and demonstrating ``pydoctor`` HTML API rendering for **reStructuredText** based documentation.

Try to keep the example as condensed as possible.

- Make  it easy to review HTML rendering.
- Cover all most common reStructuredText markup.
  Like the usage of list with various indentation types.
- Have it build as part of our continuous integration tests.
  To ensure we don't introduce regressions.

.. note:: Even if most of the structural (i.e. not inline) reST markup appears to ressemble Epytext markup, 
    blank lines are often needed where Epytext allowed no blank line after parent element. Indentation
    is also much more important, lists content and child items must be correctly indented.  

Lists
=====

reStructuredText supports both ordered and unordered lists.
A list consists of one or more consecutive list items with the same indentation.
Each list item is marked by a bullet.
The bullet for unordered list items is a single dash character (``-``).
Bullets for ordered list items consist of a series of numbers followed by periods,
such as ``12.`` or ``1.2.8.``.

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

Literal blocks are introduced by paragraphs ending in the special sequence ``::``.
Literal blocks end at the first line whose indentation is equal to or less than that of the paragraph that introduces them.

The following is a literal block::

    Literal /
           / **Block**


Doctest Blocks
==============

- contain examples consisting of Python expressions and their output
- can be used by the doctest module to test the documented object
- begin with the special sequence ``>>>``
- are delimited from surrounding blocks by blank lines
- may not contain blank lines

The following is a doctest block inside a block quote (automatically added because of indentation):

    >>> print (1+3,
    ...        3+5)
    (4, 8)
    >>> 'a-b-c-d-e'.split('-')
    ['a', 'b', 'c', 'd', 'e']

This is a paragraph following the doctest block.


Python code Blocks
==================

Using reStructuredText markup it is possible to specify Python code snippets in a ``.. python::`` directive . 

If the Python prompt gets in your way when you try to copy and paste and you are not interested in self-testing docstrings, 
the 

This will let you obtain a simple block of colorized text:

.. python::

    def fib(n):
        '''Print a Fibonacci series.'''
        a, b = 0, 1
        while b < n:
            print b,
            a, b = b, a+b


Inline Markup
=============

reStructuredText defines a lot of inline markup, here's a few of the most common:

- *Italicized text*
- **Bold-faced text**
- ``Source code``
- `subprocess.Popen` (Interpreted text: used for cross-referencing python objects)

.. note::
    Inline markup cannot be nested.
    A workaround is to use the ``.. replace::`` directive: 

    I recommend you try |Python|_.

    .. |Python| replace:: **Python**, *the* best language around

URLs
====

The inline markup construct ```text <url>`_`` is used to create links to external URLs and URIs.
'text' is the text that should be displayed for the link, and 'url' is the target of the link.
If you wish to use the URL as the text for the link, you can simply write the URL as is.

The following example illustrates how URLs can be used:

- http://www.python.org (A standalone hyperlink.)
- `docutils quickref 
  <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_
- External hyperlinks with substitution, like Python_.

.. _Python: http://www.python.org/


Admonitions
===========

.. note:: This is just a info. 

.. tip:: This is good for you. 

.. hint:: This too. 

.. important:: Important information here. 

.. warning:: This should be taken seriouly. 

.. attention:: Beware. 

.. caution:: This should be taken very seriouly. 

.. danger:: This function is a security whole!

.. error:: This is not right. 

.. raw:: html

    <style>
        .rst-admonition-purple {
            background-color: plum ! important;
        }
        .rst-admonition-purple p.rst-admonition-title{
            color: purple ! important;
        }
    </style>

.. admonition:: Purple

   This needs additionnal CSS for the new "rst-admonition-purple" class. 
   Include additional CSS by customizing the ``apidocs.css`` temlate file or by defining a raw block::

    .. raw:: html

    <style>
        .rst-admonition-purple {
            background-color: plum ! important;
        }
        .rst-admonition-purple p.rst-admonition-title{
            color: purple ! important;
        }
    </style>

   .. note:: The ``! important`` is required to overrride ``apidocs.css``. 


Symbols
=======

Any symbol can be rendered with the ``.. unicode::`` directive. 

Copyright |copy| 2021, |MojoInc (TM)| |---|
all rights reserved.

.. |copy| unicode:: 0xA9 .. copyright sign
.. |MojoInc (TM)| unicode:: MojoInc U+2122
.. with trademark sign
.. |---| unicode:: U+02014 .. em dash
    :trim:

Comments
========

This is a commented warning::

    .. .. warning:: This should not be used!

.. .. warning:: This should not be used!

Escaping
========

Escaping is used to write text that would otherwise be interpreted as reStructuredText markup.
ReStructuredText handles escaping with the backslash character. 

thisis\ *one*\ word. 

.. note:: The docstring must be declared as a raw docstring: with the ``r`` prefix to prevent Python to interpret the backslashes. 

See more on escaping on `docutils documentation page <https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#escaping-mechanism>`_




"""
