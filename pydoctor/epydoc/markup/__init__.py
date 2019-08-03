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
  - output generation (L{to_plaintext()<ParsedDocstring.to_plaintext>}
    and L{to_html()<ParsedDocstring.to_html>}.
  - Summarization (L{summary()<ParsedDocstring.summary>}).
  - Field extraction (L{split_fields()<ParsedDocstring.split_fields>}).
  - Index term extraction (L{index_terms()<ParsedDocstring.index_terms>}.

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

@sort: parse, ParsedDocstring, Field, DocstringLinker
@group Errors and Warnings: ParseError
@var _parse_warnings: Used by L{_parse_warn}.
"""
__docformat__ = 'epytext en'

import re
from pydoctor.epydoc import log
from pydoctor.epydoc.util import plaintext_to_html
from pydoctor import epydoc

##################################################
## Contents
##################################################
#
# 1. parse() dispatcher
# 2. ParsedDocstring abstract base class
# 3. Field class
# 4. Docstring Linker
# 5. ParseError exceptions
#

##################################################
## Dispatcher
##################################################

_markup_language_registry = {
    'restructuredtext': 'pydoctor.epydoc.markup.restructuredtext',
    'epytext': 'pydoctor.epydoc.markup.epytext',
    'plaintext': 'pydoctor.epydoc.markup.plaintext',
    'javadoc': 'pydoctor.epydoc.markup.javadoc',
    }
"""
Maps a case-insensitive markup language name to a function
that parses that markup language to a L{ParsedDocstring}.
The function should have the following signature:

        >>> def parse(s, errors):
        ...     'returns a ParsedDocstring'

    Where:
        - C{s} is the string to parse.  (C{s} will be a unicode
            string.)
        - C{errors} is a list; any errors that are generated
            during docstring parsing should be appended to this
            list (as L{ParseError} objects).
"""

def parse(docstring, markup='plaintext', errors=None, **options):
    """
    Parse the given docstring, and use it to construct a
    C{ParsedDocstring}.  If any fatal C{ParseError}s are encountered
    while parsing the docstring, then the docstring will be rendered
    as plaintext, instead.

    @type docstring: C{string}
    @param docstring: The docstring to encode.
    @type markup: C{string}
    @param markup: The name of the markup language that is used by
        the docstring.  If the markup language is not supported, then
        the docstring will be treated as plaintext.  The markup name
        is case-insensitive.
    @param errors: A list where any errors generated during parsing
        will be stored.  If no list is specified, then fatal errors
        will generate exceptions, and non-fatal errors will be
        ignored.
    @type errors: C{list} of L{ParseError}
    @rtype: L{ParsedDocstring}
    @return: A L{ParsedDocstring} that encodes the contents of
        C{docstring}.
    @raise ParseError: If C{errors} is C{None} and an error is
        encountered while parsing.
    """
    # Initialize errors list.
    raise_on_error = (errors is None)
    if errors == None: errors = []

    # Normalize the markup language name.
    markup = markup.lower()

    # Is the markup language valid?
    if not re.match(r'\w+', markup):
        _parse_warn('Bad markup language name %r.  Treating '
                    'docstrings as plaintext.' % markup)
        import pydoctor.epydoc.markup.plaintext as plaintext
        return plaintext.parse_docstring(docstring, errors, **options)

    # Is the markup language supported?
    if markup not in _markup_language_registry:
        _parse_warn('Unsupported markup language %r.  Treating '
                    'docstrings as plaintext.' % markup)
        import pydoctor.epydoc.markup.plaintext as plaintext
        return plaintext.parse_docstring(docstring, errors, **options)

    # Get the parse function.
    parse_docstring = _markup_language_registry[markup]

    # If it's a string, then it names a function to import.
    if isinstance(parse_docstring, basestring):
        try: exec('from %s import parse_docstring' % parse_docstring)
        except ImportError, ex:
            _parse_warn('Error importing %s for markup language %s: %s' %
                        (parse_docstring, markup, ex))
            import pydoctor.epydoc.markup.plaintext as plaintext
            return plaintext.parse_docstring(docstring, errors, **options)
        _markup_language_registry[markup] = parse_docstring

    # Parse the docstring.
    try: parsed_docstring = parse_docstring(docstring, errors, **options)
    except KeyboardInterrupt: raise
    except Exception, ex:
        if epydoc.DEBUG: raise
        log.error('Internal error while parsing a docstring: %s; '
                  'treating docstring as plaintext' % ex)
        import pydoctor.epydoc.markup.plaintext as plaintext
        return plaintext.parse_docstring(docstring, errors, **options)

    # Check for fatal errors.
    fatal_errors = [e for e in errors if e.is_fatal()]
    if fatal_errors and raise_on_error: raise fatal_errors[0]
    if fatal_errors:
        import pydoctor.epydoc.markup.plaintext as plaintext
        return plaintext.parse_docstring(docstring, errors, **options)

    return parsed_docstring

# only issue each warning once:
_parse_warnings = {}
def _parse_warn(estr):
    """
    Print a warning message.  If the given error has already been
    printed, then do nothing.
    """
    global _parse_warnings
    if estr in _parse_warnings: return
    _parse_warnings[estr] = 1
    log.warning(estr)

##################################################
## ParsedDocstring
##################################################
class ParsedDocstring:
    """
    A standard intermediate representation for parsed docstrings that
    can be used to generate output.  Parsed docstrings are produced by
    markup parsers (such as L{epytext.parse} or L{javadoc.parse}).
    C{ParsedDocstring}s support several kinds of operation:
      - output generation (L{to_plaintext()} and L{to_html()}.
      - Summarization (L{summary()}).
      - Field extraction (L{split_fields()}).
      - Index term extraction (L{index_terms()}.

    The output generation methods (C{to_M{format}()}) use a
    L{DocstringLinker} to link the docstring output with the rest
    of the documentation that epydoc generates.

    Subclassing
    ===========
    The only method that a subclass is I{required} to implement is
    L{to_plaintext()}; but it is often useful to override the other
    methods.  The default behavior of each method is described below:
      - C{to_I{format}}: Calls C{to_plaintext}, and uses the string it
        returns to generate verbatim output.
      - C{summary}: Returns C{self} (i.e., the entire docstring).
      - C{split_fields}: Returns C{(self, [])} (i.e., extracts no
        fields).
      - C{index_terms}: Returns C{[]} (i.e., extracts no index terms).

    If and when epydoc adds more output formats, new C{to_I{format}}
    methods will be added to this base class; but they will always
    be given a default implementation.
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
        # Default behavior:
        return self, []

    def summary(self):
        """
        @return: A pair consisting of a short summary of this docstring and a
            boolean value indicating whether there is further documentation
            in addition to the summary. Typically, the summary consists of the
            first sentence of the docstring.
        @rtype: (L{ParsedDocstring}, C{bool})
        """
        # Default behavior:
        return self, False

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
        # Default behavior:
        plaintext = plaintext_to_html(self.to_plaintext(docstring_linker))
        return '<pre class="literalblock">\n%s\n</pre>\n' % plaintext

    def to_plaintext(self, docstring_linker, **options):
        """
        Translate this docstring to plaintext.

        @param docstring_linker: A plaintext translator for
            crossreference links into and out of the docstring.
        @type docstring_linker: L{DocstringLinker}
        @param options: Any extra options for the output.  Unknown
            options are ignored.
        @return: A plaintext fragment that encodes this docstring.
        @rtype: C{string}
        """
        raise NotImplementedError, 'ParsedDocstring.to_plaintext()'

    def index_terms(self):
        """
        @return: The list of index terms that are defined in this
            docstring.  Each of these items will be added to the index
            page of the documentation.
        @rtype: C{list} of C{ParsedDocstring}
        """
        # Default behavior:
        return []

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
    @ivar _offset: The line number where the docstring begins.  This
        offset is added to C{_linenum} when displaying the line number
        of the error.  Default value: 1.
    @type _offset: C{int}
    @ivar _descr: A description of the error.
    @type _descr: C{string}
    @ivar _fatal: True if this is a fatal error.
    @type _fatal: C{boolean}
    """
    def __init__(self, descr, linenum=None, is_fatal=1):
        """
        @type descr: C{string}
        @param descr: A description of the error.
        @type linenum: C{int}
        @param linenum: The line on which the error occured within
            the docstring.  The linenum of the first line is 0.
        @type is_fatal: C{boolean}
        @param is_fatal: True if this is a fatal error.
        """
        self._descr = descr
        self._linenum = linenum
        self._fatal = is_fatal
        self._offset = 1

    def is_fatal(self):
        """
        @return: true if this is a fatal error.  If an error is fatal,
            then epydoc should ignore the output of the parser, and
            parse the docstring as plaintext.
        @rtype: C{boolean}
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
        else: return self._offset + self._linenum

    def set_linenum_offset(self, offset):
        """
        Set the line number offset for this error.  This offset is the
        line number where the docstring begins.  This offset is added
        to C{_linenum} when displaying the line number of the error.

        @param offset: The new line number offset.
        @type offset: C{int}
        @rtype: C{None}
        """
        self._offset = offset

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
            return 'Line %s: %s' % (self._linenum+self._offset, self.descr())
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
            return '<ParseError on line %d' % self._offset
        else:
            return '<ParseError on line %d>' % (self._linenum+self._offset)

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
        return cmp(self._linenum+self._offset,
                   other._linenum+other._offset)
