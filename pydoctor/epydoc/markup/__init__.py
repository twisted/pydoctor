#
# epydoc package file
#
# A python documentation Module
# Edward Loper
#

"""
Markup language support for docstrings.  Each submodule defines a
parser for a single markup language.  These parsers convert an
object's docstring to a L{ParsedDocstring}, a standard intermediate
representation that can be used to generate output.

A C{ParsedDocstring} is used for output generation
(L{to_stan()<ParsedDocstring.to_stan>}).
It also stores the fields that were extracted from the docstring
during parsing (L{fields<ParsedDocstring.fields>}).

The C{parse_docstring()} functions in the format modules take a docstring,
parse it and return a format-specific subclass of C{ParsedDocstring}.
A docstring's fields are separated from the body during parsing.

The C{ParsedDocstring} output generation method
(L{to_stan()<ParsedDocstring.to_stan>}) uses a
L{DocstringLinker} to link the docstring output with the rest of
the documentation that epydoc generates.  C{DocstringLinker}s are
responsible for formatting cross-references
(L{link_xref() <DocstringLinker.link_xref>}).

Markup errors are represented using L{ParseError}s.  These exception
classes record information about the cause, location, and severity of
each error.
"""
__docformat__ = 'epytext en'

from typing import List, Optional, Sequence, Union
import re

from twisted.python.failure import Failure
from twisted.web.template import Tag, XMLString, flattenString

##################################################
## Contents
##################################################
#
# 1. ParsedDocstring abstract base class
# 2. Field class
# 3. Docstring Linker
# 4. ParseError exceptions
#

##################################################
## ParsedDocstring
##################################################
class ParsedDocstring:
    """
    A standard intermediate representation for parsed docstrings that
    can be used to generate output.  Parsed docstrings are produced by
    markup parsers such as L{pydoctor.epydoc.markup.epytext.parse_docstring()}
    or L{pydoctor.epydoc.markup.restructuredtext.parse_docstring()}.

    Subclasses must implement L{has_body()} and L{to_stan()}.
    """

    def __init__(self, fields: Sequence['Field']):
        self.fields = fields
        """
        A list of L{Field}s, each of which encodes a single field.
        The field's bodies are encoded as C{ParsedDocstring}s.
        """

    @property
    def has_body(self) -> bool:
        """Does this docstring have a non-empty body?

        The body is the part of the docstring that remains after the fields
        have been split off.
        """
        raise NotImplementedError()

    def to_stan(self, docstring_linker: 'DocstringLinker') -> Tag:
        """
        Translate this docstring to a Stan tree.

        Implementations are encouraged to generate Stan output directly
        if possible, but if that is not feasible, L{html2stan()} can be
        used instead.

        @param docstring_linker: An HTML translator for crossreference
            links into and out of the docstring.
        @return: The docstring presented as a tree.
        """
        raise NotImplementedError()

_RE_CONTROL = re.compile((
    '[' + ''.join(
    ch for ch in map(chr, range(0, 32)) if ch not in '\r\n\t\f'
    ) + ']'
    ).encode())

def html2stan(html: Union[bytes, str]) -> Tag:
    """
    Convert an HTML string to a Stan tree.

    @param html: An HTML fragment; multiple roots are allowed.
    @return: The fragment as a tree with a transparent root node.
    """
    if isinstance(html, str):
        html = html.encode('utf8')

    html = _RE_CONTROL.sub(lambda m:b'\\x%02x' % ord(m.group()), html)
    stan: Tag = XMLString(b'<div>%s</div>' % html).load()[0]
    assert stan.tagName == 'div'
    stan.tagName = ''
    return stan

def flatten(stan: Tag) -> str:
    """
    Convert a document fragment from a Stan tree to HTML.

    @param stan: Document fragment to flatten.
    @return: An HTML string representation of the C{stan} tree.
    """
    ret: List[bytes] = []
    err: List[Failure] = []
    flattenString(None, stan).addCallback(ret.append).addErrback(err.append)
    if err:
        raise err[0].value
    else:
        return ret[0].decode()

##################################################
## Fields
##################################################
class Field:
    """
    The contents of a docstring's field.  Docstring fields are used
    to describe specific aspects of an object, such as a parameter of
    a function or the author of a module.  Each field consists of a
    tag, an optional argument, and a body:
      - The tag specifies the type of information that the field
        encodes.
      - The argument specifies the object that the field describes.
        The argument may be C{None} or a C{string}.
      - The body contains the field's information.

    Tags are automatically downcased and stripped; and arguments are
    automatically stripped.
    """

    def __init__(self, tag: str, arg: Optional[str], body: ParsedDocstring, lineno: int):
        self._tag = tag.lower().strip()
        self._arg = None if arg is None else arg.strip()
        self._body = body
        self.lineno = lineno

    def tag(self) -> str:
        """
        @return: This field's tag.
        """
        return self._tag

    def arg(self) -> Optional[str]:
        """
        @return: This field's argument, or C{None} if this field has no argument.
        """
        return self._arg

    def body(self) -> ParsedDocstring:
        """
        @return: This field's body.
        """
        return self._body

    def __repr__(self) -> str:
        if self._arg is None:
            return f'<Field @{self._tag}: ...>'
        else:
            return f'<Field @{self._tag} {self._arg}: ...>'

##################################################
## Docstring Linker (resolves crossreferences)
##################################################
class DocstringLinker:
    """
    A resolver for crossreference links out of a C{ParsedDocstring}.
    C{DocstringLinker} is used by C{ParsedDocstring} to look up the
    target URL for crossreference links.
    """

    def link_to(self, target: str, label: str) -> Tag:
        """
        Format a link to a Python identifier.
        This will resolve the identifier like Python itself would.

        @param target: The name of the Python identifier that
            should be linked to.
        @param label: The label to show for the link.
        @return: The link, or just the label if the target was not found.
        """
        raise NotImplementedError()

    def link_xref(self, target: str, label: str, lineno: int) -> Tag:
        """
        Format a cross-reference link to a Python identifier.
        This will resolve the identifier to any reasonable target,
        even if it has to look in places where Python itself would not.

        @param target: The name of the Python identifier that
            should be linked to.
        @param label: The label to show for the link.
        @param lineno: The line number within the docstring at which the
            crossreference is located.
        @return: The link, or just the label if the target was not found.
            In either case, the returned top-level tag will be C{<code>}.
        """
        raise NotImplementedError()

    def resolve_identifier(self, identifier: str) -> Optional[str]:
        """
        Resolve a Python identifier.
        This will resolve the identifier like Python itself would.

        @param identifier: The name of the Python identifier that
            should be linked to.
        @return: The URL of the target, or L{None} if not found.
        """
        raise NotImplementedError()


##################################################
## ParseError exceptions
##################################################

class ParseError(Exception):
    """
    The base class for errors generated while parsing docstrings.
    """

    def __init__(self,
            descr: str,
            linenum: Optional[int] = None,
            is_fatal: bool = True
            ):
        """
        @param descr: A description of the error.
        @param linenum: The line on which the error occured within
            the docstring.  The linenum of the first line is 0.
        @param is_fatal: True if this is a fatal error.
        """
        self._descr = descr
        self._linenum = linenum
        self._fatal = is_fatal

    def is_fatal(self) -> bool:
        """
        @return: true if this is a fatal error.  If an error is fatal,
            then epydoc should ignore the output of the parser, and
            parse the docstring as plaintext.
        """
        return self._fatal

    def linenum(self) -> Optional[int]:
        """
        @return: The line number on which the error occured (including
        any offset).  If the line number is unknown, then return
        C{None}.
        """
        if self._linenum is None: return None
        else: return self._linenum + 1

    def descr(self) -> str:
        """
        @return: A description of the error.
        """
        return self._descr

    def __str__(self) -> str:
        """
        Return a string representation of this C{ParseError}.  This
        multi-line string contains a description of the error, and
        specifies where it occured.

        @return: the informal representation of this C{ParseError}.
        """
        if self._linenum is not None:
            return f'Line {self._linenum + 1:d}: {self.descr()}'
        else:
            return self.descr()

    def __repr__(self) -> str:
        """
        Return the formal representation of this C{ParseError}.
        C{ParseError}s have formal representations of the form::
           <ParseError on line 12>

        @return: the formal representation of this C{ParseError}.
        """
        if self._linenum is None:
            return '<ParseError on unknown line>'
        else:
            return f'<ParseError on line {self._linenum + 1:d}>'
