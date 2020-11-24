Frequently asked questions
==========================

Why?
----

``pydoctor`` was written to be used by the `Twisted project <http://twistedmatrix.com>`_ which was
using `epydoc <http://epydoc.sourceforge.net/>`_ but was becoming increasingly unhappy with it for various reasons.  
In addition, development on Epydoc seemed to have halted.

The needs of the Twisted project are still the main driving force for ``pydoctor``'s
development, but it is getting to the point where there's some chance that it is
useful for your project too.

Who wrote ``pydoctor``?
------------------------

Michael "mwhudson" Hudson, PyPy, Launchpad and sometimes
Twisted hacker, with help from Christopher "radix" Armstrong
and Jonathan "jml" Lange and advice and ideas from many
people who hang out in #twisted on freenode.

More recently, Maarten ter Huurne "mthuurne", took the lead.
Always backed with `numerous contributors <https://github.com/twisted/pydoctor/graphs/contributors>`_.

Why would I use it?
-------------------

``pydoctor`` is probably best suited to documenting a library that have some degree of internal subclassing. 
It also has support for `zope.interface <https://zopeinterface.readthedocs.io/en/latest/>`_, and can
recognise interfaces and classes which implement such interfaces.

How is it different from ``sphinx-autodoc``
-------------------------------------------

``sphinx-autodoc`` can be hazardous and the output is sometimes overwhelming, ``pydoctor`` will generate 
one page per class, module and package, it tries to keeps it simple and present information in a efficient way with tables. 

It can be integrated to your Sphinx prose documentation seemlesly to link to your API documentation, please refer to `Usage <usage.html>`_ section.

What does the output look like?
-------------------------------

It looks `like this <http://twistedmatrix.com/documents/current/api/>`_, which is the Twisted API documentation.

The output is reasonably simple.

As a bonus here are other projects using ``pydoctor``:
    - Wokkel 
    - msiempy
    - An many others! 

How do I use it?
----------------

Please review the `Usage <usage.html>`_ section. 