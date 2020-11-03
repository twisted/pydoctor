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

Why would I use it?  How is it different from ``sphinx-autodoc``
----------------------------------------------------------------

``pydoctor`` is probably best suited to documenting a library that have some degree of internal subclassing. 
It also has support for `zope.interface <http://www.zope.org/Products/ZopeInterface>`_, and can
recognise interfaces and classes which implement such interfaces.

Pydoctor can be integrated to your Sphinx prose documentation seemlesly to replace the hazardous ``sphinx-autodoc`` extension. 
Yep! It's all figured out, this very documentaion uses this feature. 

What does the output look like?
-------------------------------

It looks `like this <http://twistedmatrix.com/documents/current/api/>`_, which is the Twisted API documentation.

The output is reasonably simple.

As a bonus here are other projects using ``pydoctor``:
    - msiempy
    -  

How do I use it?
----------------

Please review the `Usage <usage.html>`_ section. 