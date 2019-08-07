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
C{ParsedDocstring}s support the following operations:
  - output generation (L{to_html()<ParsedDocstring.to_html>}).
  - Field extraction (L{split_fields()<ParsedDocstring.split_fields>}).

The L{parse()} function provides a single interface to the
C{pydoctor.epydoc.markup} package: it takes a docstring and the name of
a markup language; delegates to the appropriate parser; and returns the
parsed docstring (along with any errors or warnings that were
generated).

The C{ParsedDocstring} output generation methods (C{to_M{format}()})
use a L{DocstringLinker} to link the docstring output with the rest of
the documentation that epydoc generates.  C{DocstringLinker}s are
currently responsible for translating two kinds of crossreference:
  - index terms (L{translate_indexterm()
    <DocstringLinker.translate_indexterm>}).
  - identifier crossreferences (L{translate_identifier_xref()
    <DocstringLinker.translate_identifier_xref>}).

A parsed docstring's fields can be extracted using the
L{ParsedDocstring.split_fields()} method.  This method divides a
docstring into its main body and a list of L{Field}s, each of which
encodes a single field.  The field's bodies are encoded as
C{ParsedDocstring}s.

Markup errors are represented using L{ParseError}s.  These exception
classes record information about the cause, location, and severity of
each error.

@sort: ParsedDocstring, Field, DocstringLinker
@group Errors and Warnings: ParseError
"""
__docformat__ = 'epytext en'

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
    markup parsers (such as L{epytext.parse} or L{javadoc.parse}).
    C{ParsedDocstring}s support several kinds of operation:
      - output generation (L{to_html()}).
      - Field extraction (L{split_fields()}).

    The output generation methods (C{to_M{format}()}) use a
    L{DocstringLinker} to link the docstring output with the rest
    of the documentation that epydoc generates.

    Subclasses must implement all methods of this class.
    """

    def split_fields(self, errors=None):
        """
        Split this docstring into its body and its fields.

        @return: A tuple C{(M{body}, M{fields})}, where C{M{body}} is
            the main body of this docstring, and C{M{fields}} is a list
            of its fields.  If the resulting body is empty, return
            C{None} for the body.
        @rtype: C{(L{ParsedDocstring}, list of L{Field})}
        @param errors: A list where any errors generated during
            splitting will be stored.  If no list is specified, then
            errors will be ignored.
        @type errors: C{list} of L{ParseError}
        """
        raise NotImplementedError('ParsedDocstring.split_fields()')

    def to_html(self, docstring_linker, **options):
        """
        Translate this docstring to HTML.

        @param docstring_linker: An HTML translator for crossreference
            links into and out of the docstring.
        @type docstring_linker: L{DocstringLinker}
        @param options: Any extra options for the output.  Unknown
            options are ignored.
        @return: An HTML fragment that encodes this docstring.
        @rtype: C{string}
        """
        raise NotImplementedError('ParsedDocstring.to_html()')

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
    def __init__(self, tag, arg, body):
        self._tag = tag.lower().strip()
        if arg is None: self._arg = None
        else: self._arg = arg.strip()
        self._body = body

    def tag(self):
        """
        @return: This field's tag.
        @rtype: C{string}
        """
        return self._tag

    def arg(self):
        """
        @return: This field's argument, or C{None} if this field has
            no argument.
        @rtype: C{string} or C{None}
        """
        return self._arg

    def body(self):
        """
        @return: This field's body.
        @rtype: L{ParsedDocstring}
        """
        return self._body

    def __repr__(self):
        if self._arg is None:
            return '<Field @%s: ...>' % self._tag
        else:
            return '<Field @%s %s: ...>' % (self._tag, self._arg)

##################################################
## Docstring Linker (resolves crossreferences)
##################################################
class DocstringLinker:
    """
    A translator for crossreference links into and out of a
    C{ParsedDocstring}.  C{DocstringLinker} is used by
    C{ParsedDocstring} to convert these crossreference links into
    appropriate output formats.  For example,
    C{DocstringLinker.to_html} expects a C{DocstringLinker} that
    converts crossreference links to HTML.
    """
    def translate_indexterm(self, indexterm):
        """
        Translate an index term to the appropriate output format.  The
        output will typically include a crossreference anchor.

        @type indexterm: L{ParsedDocstring}
        @param indexterm: The index term to translate.
        @rtype: C{string}
        @return: The translated index term.
        """
        raise NotImplementedError('DocstringLinker.translate_indexterm()')

    def translate_identifier_xref(self, identifier, label=None):
        """
        Translate a crossreference link to a Python identifier to the
        appropriate output format.  The output will typically include
        a reference or pointer to the crossreference target.

        @type identifier: C{string}
        @param identifier: The name of the Python identifier that
            should be linked to.
        @type label: C{string} or C{None}
        @param label: The label that should be used for the identifier,
            if it's different from the name of the identifier.  This
            should be expressed in the target markup language.
        @rtype: C{string}
        @return: The translated crossreference link.
        """
        raise NotImplementedError('DocstringLinker.translate_xref()')


##################################################
## ParseError exceptions
##################################################

class ParseError(Exception):
    """
    The base class for errors generated while parsing docstrings.

    @ivar _linenum: The line on which the error occured within the
        docstring.  The linenum of the first line is 0.
    @type _linenum: C{int}
    @ivar _descr: A description of the error.
    @type _descr: C{string}
    @ivar _fatal: True if this is a fatal error.
    @type _fatal: C{bool}
    """
    def __init__(self, descr, linenum=None, is_fatal=True):
        """
        @type descr: C{string}
        @param descr: A description of the error.
        @type linenum: C{int}
        @param linenum: The line on which the error occured within
            the docstring.  The linenum of the first line is 0.
        @type is_fatal: C{bool}
        @param is_fatal: True if this is a fatal error.
        """
        self._descr = descr
        self._linenum = linenum
        self._fatal = is_fatal

    def is_fatal(self):
        """
        @return: true if this is a fatal error.  If an error is fatal,
            then epydoc should ignore the output of the parser, and
            parse the docstring as plaintext.
        @rtype: C{bool}
        """
        return self._fatal

    def linenum(self):
        """
        @return: The line number on which the error occured (including
        any offset).  If the line number is unknown, then return
        C{None}.
        @rtype: C{int} or C{None}
        """
        if self._linenum is None: return None
        else: return self._linenum + 1

    def descr(self):
        return self._descr

    def __str__(self):
        """
        Return a string representation of this C{ParseError}.  This
        multi-line string contains a description of the error, and
        specifies where it occured.

        @return: the informal representation of this C{ParseError}.
        @rtype: C{string}
        """
        if self._linenum is not None:
            return 'Line %d: %s' % (self._linenum + 1, self.descr())
        else:
            return self.descr()

    def __repr__(self):
        """
        Return the formal representation of this C{ParseError}.
        C{ParseError}s have formal representations of the form::
           <ParseError on line 12>

        @return: the formal representation of this C{ParseError}.
        @rtype: C{string}
        """
        if self._linenum is None:
            return '<ParseError on unknown line>'
        else:
            return '<ParseError on line %d>' % (self._linenum + 1)

    def __cmp__(self, other):
        """
        Compare two C{ParseError}s, based on their line number.
          - Return -1 if C{self.linenum<other.linenum}
          - Return +1 if C{self.linenum>other.linenum}
          - Return 0 if C{self.linenum==other.linenum}.
        The return value is undefined if C{other} is not a
        ParseError.

        @rtype: C{int}
        """
        if not isinstance(other, ParseError): return -1000
        return cmp(self._linenum, other._linenum)
