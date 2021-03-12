"""
Convert docstrings from numpy or google style format to reST. 

This package is a fork of L{sphinx.ext.napoleon} 
adapted for C{pydoctor} usage. 

The following list roughtly describes the changes: 

    - B{Use more type parsing}:

    All types will be pre-processed and links will be automtically created when possible. 
    See L{TypeDocstring} for examples of what's a valid type specification string. 

    - B{Types in google-style C{Returns} and C{Args} clauses can span multiple lines}:

    This will be understood correctly::

        Args:
            docstring (Union[
                list[str] str,
                list[twisted.python.compat.NativeStringIO], 
                twisted.python.compat.NativeStringIO]): The
                    docstring. Note that this last indentation is
                    optional. 
            errors (Sequence[Union[ParseError,
                ParseWarning, ParseInfo, ...]]): The list of errors, 
                warnings or other informations. 

    - B{More flexible numpy-style C{Returns} clause}:

    Allow users who have type annotations in their pure python code to omit 
    types in the returns clause docstrings but as well as specify them when it's needed. 
    Just as google-style docstring (but without the multiline type support)

    All of the following return clauses will be interpreted as expected::

        Returns
        -------
        Description of return value

        Returns
        -------
        subprocess.Popen
            Description of return value

        Returns
        -------
        list[str]

        Returns
        -------
        list of str

    See: U{sphinx/issues/7077 <https://github.com/sphinx-doc/sphinx/issues/7077>} 

    - No settings are supported for a more straight-forward usage simple usage. 
      Also there is no support for custom sections or type aliases. 

Docformat references: 

    - U{Google-style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>} 
    - U{NumpyDoc-style <https://numpydoc.readthedocs.io/en/latest/format.html>}


@note: Sphinx Napoleon related 
    U{PRs <https://github.com/sphinx-doc/sphinx/pulls?q=is%3Apr+napoleon>} and 
    U{issues <https://github.com/sphinx-doc/sphinx/labels/extensions%3Anapoleon>} 
    should be checked once in a while to make sure we don't miss any important updates. 

@copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
@license: BSD, see LICENSE for details.
"""
