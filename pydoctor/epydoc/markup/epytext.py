#
# epytext.py: epydoc formatted docstring parsing
# Edward Loper
#
# Created [04/10/01 12:00 AM]
#

"""
Parser for epytext strings.  Epytext is a lightweight markup whose
primary intended application is Python documentation strings.  This
parser converts Epytext strings to a simple DOM-like representation
(encoded as a tree of L{Element} objects and strings).  Epytext
strings can contain the following I{structural blocks}:

    - C{epytext}: The top-level element of the DOM tree.
    - C{para}: A paragraph of text.  Paragraphs contain no newlines,
      and all spaces are soft.
    - C{section}: A section or subsection.
    - C{field}: A tagged field.  These fields provide information
      about specific aspects of a Python object, such as the
      description of a function's parameter, or the author of a
      module.
    - C{literalblock}: A block of literal text.  This text should be
      displayed as it would be displayed in plaintext.  The
      parser removes the appropriate amount of leading whitespace
      from each line in the literal block.
    - C{doctestblock}: A block containing sample python code,
      formatted according to the specifications of the C{doctest}
      module.
    - C{ulist}: An unordered list.
    - C{olist}: An ordered list.
    - C{li}: A list item.  This tag is used both for unordered list
      items and for ordered list items.

Additionally, the following I{inline regions} may be used within
C{para} blocks:

    - C{code}:   Source code and identifiers.
    - C{math}:   Mathematical expressions.
    - C{index}:  A term which should be included in an index, if one
                 is generated.
    - C{italic}: Italicized text.
    - C{bold}:   Bold-faced text.
    - C{uri}:    A Universal Resource Indicator (URI) or Universal
                 Resource Locator (URL)
    - C{link}:   A Python identifier which should be hyperlinked to
                 the named object's documentation, when possible.

The returned DOM tree will conform to the the following Document Type
Description::

   <!ENTITY % colorized '(code | math | index | italic |
                          bold | uri | link | symbol)*'>

   <!ELEMENT epytext ((para | literalblock | doctestblock |
                      section | ulist | olist)*, fieldlist?)>

   <!ELEMENT para (#PCDATA | %colorized;)*>

   <!ELEMENT section (para | listblock | doctestblock |
                      section | ulist | olist)+>

   <!ELEMENT fieldlist (field+)>
   <!ELEMENT field (tag, arg?, (para | listblock | doctestblock)
                                ulist | olist)+)>
   <!ELEMENT tag (#PCDATA)>
   <!ELEMENT arg (#PCDATA)>

   <!ELEMENT literalblock (#PCDATA | %colorized;)*>
   <!ELEMENT doctestblock (#PCDATA)>

   <!ELEMENT ulist (li+)>
   <!ELEMENT olist (li+)>
   <!ELEMENT li (para | literalblock | doctestblock | ulist | olist)+>
   <!ATTLIST li bullet NMTOKEN #IMPLIED>
   <!ATTLIST olist start NMTOKEN #IMPLIED>

   <!ELEMENT uri     (name, target)>
   <!ELEMENT link    (name, target)>
   <!ELEMENT name    (#PCDATA | %colorized;)*>
   <!ELEMENT target  (#PCDATA)>

   <!ELEMENT code    (#PCDATA | %colorized;)*>
   <!ELEMENT math    (#PCDATA | %colorized;)*>
   <!ELEMENT italic  (#PCDATA | %colorized;)*>
   <!ELEMENT bold    (#PCDATA | %colorized;)*>
   <!ELEMENT indexed (#PCDATA | %colorized;)>
   <!ATTLIST code style CDATA #IMPLIED>

   <!ELEMENT symbol (#PCDATA)>

@var SYMBOLS: A list of the of escape symbols that are supported by epydoc.  Currently the following symbols are supported ::

    # Arrows
    '<-', '->', '^', 'v',

    # Greek letters
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta',
    'eta', 'theta', 'iota', 'kappa', 'lambda', 'mu',
    'nu', 'xi', 'omicron', 'pi', 'rho', 'sigma',
    'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega',
    'Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta',
    'Eta', 'Theta', 'Iota', 'Kappa', 'Lambda', 'Mu',
    'Nu', 'Xi', 'Omicron', 'Pi', 'Rho', 'Sigma',
    'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega',

    # HTML character entities
    'larr', 'rarr', 'uarr', 'darr', 'harr', 'crarr',
    'lArr', 'rArr', 'uArr', 'dArr', 'hArr',
    'copy', 'times', 'forall', 'exist', 'part',
    'empty', 'isin', 'notin', 'ni', 'prod', 'sum',
    'prop', 'infin', 'ang', 'and', 'or', 'cap', 'cup',
    'int', 'there4', 'sim', 'cong', 'asymp', 'ne',
    'equiv', 'le', 'ge', 'sub', 'sup', 'nsub',
    'sube', 'supe', 'oplus', 'otimes', 'perp',

    # Alternate (long) names
    'infinity', 'integral', 'product',
    '>=', '<=',

"""
# Note: the symbol list is appended to the docstring automatically,
# below.

__docformat__ = 'epytext en'

# Code organization..
#   1. parse()
#   2. tokenize()
#   3. colorize()
#   4. helpers
#   5. testing

from typing import Any, List, Optional, Sequence, Union, cast, overload
import re

from twisted.web.template import CharRef, Tag, tags
from pydoctor.epydoc.doctest import colorize_doctest
from pydoctor.epydoc.markup import DocstringLinker, Field, ParseError, ParsedDocstring

##################################################
## DOM-Like Encoding
##################################################

class Element:
    """
    A very simple DOM-like representation for parsed epytext
    documents.  Each epytext document is encoded as a tree whose nodes
    are L{Element} objects, and whose leaves are C{string}s.  Each
    node is marked by a I{tag} and zero or more I{attributes}.  Each
    attribute is a mapping from a string key to a string value.
    """
    def __init__(self, tag: str, *children: Union[str, 'Element'], **attribs: Any):
        self.tag = tag
        """A string tag indicating the type of this element."""

        self.children = list(children)
        """A list of the children of this element."""

        self.attribs = attribs
        """A dictionary mapping attribute names to attribute values for this element."""

    def __str__(self) -> str:
        """
        Return a string representation of this element, using XML
        notation.
        @note: Doesn't escape '<' or '&' or '>', so the result is only XML-like
            and cannot actually be parsed as XML.
        """
        attribs = ''.join(f' {k}={v!r}' for k, v in self.attribs.items())
        content = ''.join(str(child) for child in self.children)
        return f'<{self.tag}{attribs}>{content}</{self.tag}>'

    def __repr__(self) -> str:
        attribs = ''.join(f', {k}={v!r}' for k, v in self.attribs.items())
        args = ''.join(f', {c!r}' for c in self.children)
        return f'Element({self.tag}{args}{attribs})'

##################################################
## Constants
##################################################

# The possible heading underline characters, listed in order of
# heading depth.
_HEADING_CHARS = '=-~'

# Escape codes.  These should be needed very rarely.
_ESCAPES = {'lb':'{', 'rb': '}'}

# Symbols.  These can be generated via S{...} escapes.
SYMBOLS = [
    # Arrows
    '<-', '->', '^', 'v',

    # Greek letters
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta',
    'eta', 'theta', 'iota', 'kappa', 'lambda', 'mu',
    'nu', 'xi', 'omicron', 'pi', 'rho', 'sigma',
    'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega',
    'Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta',
    'Eta', 'Theta', 'Iota', 'Kappa', 'Lambda', 'Mu',
    'Nu', 'Xi', 'Omicron', 'Pi', 'Rho', 'Sigma',
    'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega',

    # HTML character entities
    'larr', 'rarr', 'uarr', 'darr', 'harr', 'crarr',
    'lArr', 'rArr', 'uArr', 'dArr', 'hArr',
    'copy', 'times', 'forall', 'exist', 'part',
    'empty', 'isin', 'notin', 'ni', 'prod', 'sum',
    'prop', 'infin', 'ang', 'and', 'or', 'cap', 'cup',
    'int', 'there4', 'sim', 'cong', 'asymp', 'ne',
    'equiv', 'le', 'ge', 'sub', 'sup', 'nsub',
    'sube', 'supe', 'oplus', 'otimes', 'perp',

    # Alternate (long) names
    'infinity', 'integral', 'product',
    '>=', '<=',
    ]
# Convert to a set, for quick lookup
_SYMBOLS = set(SYMBOLS)

# Add symbols to the docstring.
symblist = '      '
symblist += ';\n      '.join(' - C{E{S}{%s}}=S{%s}' % (symbol, symbol)
                             for symbol in SYMBOLS)
__doc__ = __doc__.replace('<<<SYMBOLS>>>', symblist)
del symblist

# Tags for colorizing text.
_COLORIZING_TAGS = {
    'C': 'code',
    'M': 'math',
    'I': 'italic',
    'B': 'bold',
    'U': 'uri',
    'L': 'link',       # A Python identifier that should be linked to
    'E': 'escape',     # escapes characters or creates symbols
    'S': 'symbol',
    }

# Which tags can use "link syntax" (e.g., U{Python<www.python.org>})?
_LINK_COLORIZING_TAGS = ['link', 'uri']

##################################################
## Structuring (Top Level)
##################################################

@overload
def parse(text: str) -> Element: ...

@overload
def parse(text: str, errors: List[ParseError]) -> Optional[Element]: ...

def parse(text: str, errors: Optional[List[ParseError]] = None) -> Optional[Element]:
    """
    Return a DOM tree encoding the contents of an epytext string.  Any
    errors generated during parsing will be stored in C{errors}.

    @param text: The epytext string to parse.
    @param errors: A list where any errors generated during parsing
        will be stored.  If no list is specified, then fatal errors
        will generate exceptions, and non-fatal errors will be
        ignored.
    @return: a DOM tree encoding the contents of an epytext string,
        or C{None} if non-fatal errors were encountered and no C{errors}
        accumulator was provided.
    @raise ParseError: If C{errors} is C{None} and an error is
        encountered while parsing.
    """
    # Initialize errors list.
    if errors is None:
        errors = []
        raise_on_error = True
    else:
        raise_on_error = False

    # Preprocess the string.
    text = re.sub('\015\012', '\012', text)
    text = text.expandtabs()

    # Tokenize the input string.
    tokens = _tokenize(text, errors)

    # Have we encountered a field yet?
    encountered_field = False

    # Create an document to hold the epytext.
    doc = Element('epytext')

    # Maintain two parallel stacks: one contains DOM elements, and
    # gives the ancestors of the current block.  The other contains
    # indentation values, and gives the indentation of the
    # corresponding DOM elements.  An indentation of "None" reflects
    # an unknown indentation.  However, the indentation must be
    # greater than, or greater than or equal to, the indentation of
    # the prior element (depending on what type of DOM element it
    # corresponds to).  No 2 consecutive indent_stack values will be
    # ever be "None."  Use initial dummy elements in the stack, so we
    # don't have to worry about bounds checking.
    stack = [cast(Element, None), doc]
    indent_stack = [-1, None]

    for token in tokens:
        # Uncomment this for debugging:
        #print('%s: %s\n%s: %s\n' %
        #       (''.join('%-11s' % (t and t.tag) for t in stack),
        #        token.tag, ''.join('%-11s' % i for i in indent_stack),
        #        token.indent))

        # Pop any completed blocks off the stack.
        _pop_completed_blocks(token, stack, indent_stack)

        # If Token has type PARA, colorize and add the new paragraph
        if token.tag == Token.PARA:
            _add_para(token, stack, indent_stack, errors)

        # If Token has type HEADING, add the new section
        elif token.tag == Token.HEADING:
            _add_section(token, stack, indent_stack, errors)

        # If Token has type LBLOCK, add the new literal block
        elif token.tag == Token.LBLOCK:
            stack[-1].children.append(token.to_dom())

        # If Token has type DTBLOCK, add the new doctest block
        elif token.tag == Token.DTBLOCK:
            stack[-1].children.append(token.to_dom())

        # If Token has type BULLET, add the new list/list item/field
        elif token.tag == Token.BULLET:
            _add_list(token, stack, indent_stack, errors)
        else:
            raise AssertionError(f"Unknown token type: {token.tag}")

        # Check if the DOM element we just added was a field..
        if stack[-1].tag == 'field':
            encountered_field = True
        elif encountered_field:
            if len(stack) <= 3:
                estr = ("Fields must be the final elements in an "+
                        "epytext string.")
                errors.append(StructuringError(estr, token.startline))

    # If there was an error, then signal it!
    if any(e.is_fatal() for e in errors):
        if raise_on_error:
            raise errors[0]
        else:
            return None

    # Return the top-level epytext DOM element.
    return doc

def _pop_completed_blocks(
        token: 'Token',
        stack: List[Element],
        indent_stack: List[Optional[int]]
        ) -> None:
    """
    Pop any completed blocks off the stack.  This includes any
    blocks that we have dedented past, as well as any list item
    blocks that we've dedented to.  The top element on the stack
    should only be a list if we're about to start a new list
    item (i.e., if the next token is a bullet).
    """
    indent = token.indent
    if indent is not None:
        while (len(stack) > 2):
            pop = False

            # Dedent past a block
            if indent_stack[-1] is not None and indent < indent_stack[-1]:
                pop = True
            elif indent_stack[-1] is None and indent < cast(int, indent_stack[-2]):
                pop = True

            # Dedent to a list item, if it is follwed by another list
            # item with the same indentation.
            elif (token.tag == 'bullet' and indent==indent_stack[-2] and
                  stack[-1].tag in ('li', 'field')): pop = True

            # End of a list (no more list items available)
            elif (stack[-1].tag in ('ulist', 'olist') and
                  (token.tag != 'bullet' or token.contents[-1] == ':')):
                pop = True

            # Pop the block, if it's complete.  Otherwise, we're done.
            if not pop: return
            stack.pop()
            indent_stack.pop()

def _add_para(
        para_token: 'Token',
        stack: List[Element],
        indent_stack: List[Optional[int]],
        errors: List[ParseError]
        ) -> None:
    """Colorize the given paragraph, and add it to the DOM tree."""
    # Check indentation, and update the parent's indentation
    # when appropriate.
    if indent_stack[-1] is None:
        indent_stack[-1] = para_token.indent
    if para_token.indent == indent_stack[-1]:
        # Colorize the paragraph and add it.
        para = _colorize(para_token, errors)
        if para_token.inline:
            para.attribs['inline'] = True
        stack[-1].children.append(para)
    else:
        estr = "Improper paragraph indentation."
        errors.append(StructuringError(estr, para_token.startline))

def _add_section(
        heading_token: 'Token',
        stack: List[Element],
        indent_stack: List[Optional[int]],
        errors: List[ParseError]
        ) -> None:
    """Add a new section to the DOM tree, with the given heading."""
    if indent_stack[-1] is None:
        indent_stack[-1] = heading_token.indent
    elif indent_stack[-1] != heading_token.indent:
        estr = "Improper heading indentation."
        errors.append(StructuringError(estr, heading_token.startline))

    # Check for errors.
    for tok in stack[2:]:
        if tok.tag != 'section':
            estr = "Headings must occur at the top level."
            errors.append(StructuringError(estr, heading_token.startline))
            break
    index = cast(int, heading_token.level) + 2
    if index > len(stack):
        estr = "Wrong underline character for heading."
        errors.append(StructuringError(estr, heading_token.startline))

    # Pop the appropriate number of headings so we're at the
    # correct level.
    stack[index:] = []
    indent_stack[index:] = []

    # Colorize the heading
    head = _colorize(heading_token, errors, 'heading')

    # Add the section's and heading's DOM elements.
    sec = Element('section')
    stack[-1].children.append(sec)
    stack.append(sec)
    sec.children.append(head)
    indent_stack.append(None)

def _add_list(
        bullet_token: 'Token',
        stack: List[Element],
        indent_stack: List[Optional[int]],
        errors: List[ParseError]
        ) -> None:
    """
    Add a new list item or field to the DOM tree, with the given
    bullet or field tag.  When necessary, create the associated
    list.
    """
    # Determine what type of bullet it is.
    if bullet_token.contents[-1] == '-':
        list_type = 'ulist'
    elif bullet_token.contents[-1] == '.':
        list_type = 'olist'
    elif bullet_token.contents[-1] == ':':
        list_type = 'fieldlist'
    else:
        raise AssertionError(f'Bad Bullet: {bullet_token.contents!r}')

    # Is this a new list?
    newlist = False
    if stack[-1].tag != list_type:
        newlist = True
    elif list_type == 'olist' and stack[-1].tag == 'olist':
        old_listitem = cast(Element, stack[-1].children[-1])
        old_bullet = old_listitem.attribs['bullet'].split('.')[:-1]
        new_bullet = bullet_token.contents.split('.')[:-1]
        if (new_bullet[:-1] != old_bullet[:-1] or
            int(new_bullet[-1]) != int(old_bullet[-1])+1):
            newlist = True

    # Create the new list.
    if newlist:
        if stack[-1].tag == 'fieldlist':
            # The new list item is not a field list item (since this
            # is a new list); but it's indented the same as the field
            # list.  This either means that they forgot to indent the
            # list, or they are trying to put something after the
            # field list.  The first one seems more likely, so we'll
            # just warn about that (to avoid confusion).
            estr = "Lists must be indented."
            errors.append(StructuringError(estr, bullet_token.startline))
        if stack[-1].tag in ('ulist', 'olist', 'fieldlist'):
            stack.pop()
            indent_stack.pop()

        if (list_type != 'fieldlist' and indent_stack[-1] is not None and
            bullet_token.indent == indent_stack[-1]):
            # Ignore this error if there's text on the same line as
            # the comment-opening quote -- epydoc can't reliably
            # determine the indentation for that line.
            if bullet_token.startline != 1 or bullet_token.indent != 0:
                estr = "Lists must be indented."
                errors.append(StructuringError(estr, bullet_token.startline))

        if list_type == 'fieldlist':
            # Fieldlist should be at the top-level.
            for tok in stack[2:]:
                if tok.tag != 'section':
                    estr = "Fields must be at the top level."
                    errors.append(
                        StructuringError(estr, bullet_token.startline))
                    break
            stack[2:] = []
            indent_stack[2:] = []

        # Add the new list.
        lst = Element(list_type)
        stack[-1].children.append(lst)
        stack.append(lst)
        indent_stack.append(bullet_token.indent)
        if list_type == 'olist':
            start = bullet_token.contents.split('.')[:-1]
            if start != '1':
                lst.attribs['start'] = start[-1]

    # Fields are treated somewhat specially: A 'fieldlist'
    # node is created to make the parsing simpler, but fields
    # are adjoined directly into the 'epytext' node, not into
    # the 'fieldlist' node.
    if list_type == 'fieldlist':
        li = Element('field', lineno=str(bullet_token.startline))
        token_words = bullet_token.contents[1:-1].split(None, 1)
        tag_elt = Element('tag')
        tag_elt.children.append(token_words[0])
        li.children.append(tag_elt)

        if len(token_words) > 1:
            arg_elt = Element('arg')
            arg_elt.children.append(token_words[1])
            li.children.append(arg_elt)
    else:
        li = Element('li')
        if list_type == 'olist':
            li.attribs['bullet'] = bullet_token.contents

    # Add the bullet.
    stack[-1].children.append(li)
    stack.append(li)
    indent_stack.append(None)

##################################################
## Tokenization
##################################################

class Token:
    """
    C{Token}s are an intermediate data structure used while
    constructing the structuring DOM tree for a formatted docstring.
    There are five types of C{Token}:

        - Paragraphs
        - Literal blocks
        - Doctest blocks
        - Headings
        - Bullets

    The text contained in each C{Token} is stored in the
    C{contents} variable.  The string in this variable has been
    normalized.  For paragraphs, this means that it has been converted
    into a single line of text, with newline/indentation replaced by
    single spaces.  For literal blocks and doctest blocks, this means
    that the appropriate amount of leading whitespace has been removed
    from each line.

    Each C{Token} has an indentation level associated with it,
    stored in the C{indent} variable.  This indentation level is used
    by the structuring procedure to assemble hierarchical blocks.

    @type tag: C{string}
    @ivar tag: This C{Token}'s type.  Possible values are C{Token.PARA}
        (paragraph), C{Token.LBLOCK} (literal block), C{Token.DTBLOCK}
        (doctest block), C{Token.HEADINGC}, and C{Token.BULLETC}.

    @type startline: C{int}
    @ivar startline: The line on which this C{Token} begins.  This
        line number is only used for issuing errors.

    @type contents: C{string}
    @ivar contents: The normalized text contained in this C{Token}.

    @type indent: C{int} or C{None}
    @ivar indent: The indentation level of this C{Token} (in
        number of leading spaces).  A value of C{None} indicates an
        unknown indentation; this is used for list items and fields
        that begin with one-line paragraphs.

    @type level: C{int} or C{None}
    @ivar level: The heading-level of this C{Token} if it is a
        heading; C{None}, otherwise.  Valid heading levels are 0, 1,
        and 2.

    @type inline: C{bool}
    @ivar inline: If True, the element is an inline level element, comparable
        to an HTML C{<span>} tag. Else, it is a block level element, comparable
        to an HTML C{<div>}.

    @type PARA: C{string}
    @cvar PARA: The C{tag} value for paragraph C{Token}s.
    @type LBLOCK: C{string}
    @cvar LBLOCK: The C{tag} value for literal C{Token}s.
    @type DTBLOCK: C{string}
    @cvar DTBLOCK: The C{tag} value for doctest C{Token}s.
    @type HEADING: C{string}
    @cvar HEADING: The C{tag} value for heading C{Token}s.
    @type BULLET: C{string}
    @cvar BULLET: The C{tag} value for bullet C{Token}s.  This C{tag}
        value is also used for field tag C{Token}s, since fields
        function syntactically the same as list items.
    """
    # The possible token types.
    PARA = 'para'
    LBLOCK = 'literalblock'
    DTBLOCK = 'doctestblock'
    HEADING = 'heading'
    BULLET = 'bullet'

    def __init__(self,
            tag: str,
            startline: int,
            contents: str,
            indent: Optional[int],
            level: Optional[int] = None,
            inline: bool = False
            ):
        """
        Create a new C{Token}.

        @param tag: The type of the new C{Token}.
        @param startline: The line on which the new C{Token} begins.
        @param contents: The normalized contents of the new C{Token}.
        @param indent: The indentation of the new C{Token} (in number
            of leading spaces).  A value of C{None} indicates an
            unknown indentation.
        @param level: The heading-level of this C{Token} if it is a
            heading; C{None}, otherwise.
        @param inline: Is this C{Token} inline as a C{<span>}?.
        """
        self.tag = tag
        self.startline = startline
        self.contents = contents
        self.indent = indent
        self.level = level
        self.inline = inline

    def __repr__(self) -> str:
        """
        @rtype: C{string}
        @return: the formal representation of this C{Token}.
            C{Token}s have formal representaitons of the form::
                <Token: para at line 12>
        """
        return f'<Token: {self.tag} at line {self.startline}>'

    def to_dom(self) -> Element:
        """
        @return: a DOM representation of this C{Token}.
        """
        e = Element(self.tag)
        e.children.append(self.contents)
        return e

# Construct regular expressions for recognizing bullets.  These are
# global so they don't have to be reconstructed each time we tokenize
# a docstring.
_ULIST_BULLET = r'[-]( +|$)'
_OLIST_BULLET = r'(\d+[.])+( +|$)'
_FIELD_BULLET = r'@\w+( [^{}:\n]+)?:'
_BULLET_RE = re.compile(_ULIST_BULLET + '|' +
                        _OLIST_BULLET + '|' +
                        _FIELD_BULLET)
_LIST_BULLET_RE = re.compile(_ULIST_BULLET + '|' + _OLIST_BULLET)
_FIELD_BULLET_RE = re.compile(_FIELD_BULLET)
del _ULIST_BULLET, _OLIST_BULLET, _FIELD_BULLET

def _tokenize_doctest(
        lines: List[str],
        start: int,
        block_indent: int,
        tokens: List[Token],
        errors: List[ParseError]
        ) -> int:
    """
    Construct a L{Token} containing the doctest block starting at
    C{lines[start]}, and append it to C{tokens}.  C{block_indent}
    should be the indentation of the doctest block.  Any errors
    generated while tokenizing the doctest block will be appended to
    C{errors}.

    @param lines: The list of lines to be tokenized
    @param start: The index into C{lines} of the first line of the
        doctest block to be tokenized.
    @param block_indent: The indentation of C{lines[start]}.  This is
        the indentation of the doctest block.
    @param errors: A list where any errors generated during parsing
        will be stored.  If no list is specified, then errors will
        generate exceptions.
    @return: The line number of the first line following the doctest
        block.
    """
    # If they dedent past block_indent, keep track of the minimum
    # indentation.  This is used when removing leading indentation
    # from the lines of the doctest block.
    min_indent = block_indent

    linenum = start + 1
    while linenum < len(lines):
        # Find the indentation of this line.
        line = lines[linenum]
        indent = len(line) - len(line.lstrip())

        # A blank line ends doctest block.
        if indent == len(line): break

        # A Dedent past block_indent is an error.
        if indent < block_indent:
            min_indent = min(min_indent, indent)
            estr = 'Improper doctest block indentation.'
            errors.append(TokenizationError(estr, linenum))

        # Go on to the next line.
        linenum += 1

    # Add the token, and return the linenum after the token ends.
    contents = '\n'.join(ln[min_indent:] for ln in lines[start:linenum])
    tokens.append(Token(Token.DTBLOCK, start, contents, block_indent))
    return linenum

def _tokenize_literal(
        lines: List[str],
        start: int,
        block_indent: int,
        tokens: List[Token],
        errors: List[ParseError]
        ) -> int:
    """
    Construct a L{Token} containing the literal block starting at
    C{lines[start]}, and append it to C{tokens}.  C{block_indent}
    should be the indentation of the literal block.  Any errors
    generated while tokenizing the literal block will be appended to
    C{errors}.

    @param lines: The list of lines to be tokenized
    @param start: The index into C{lines} of the first line of the
        literal block to be tokenized.
    @param block_indent: The indentation of C{lines[start]}.  This is
        the indentation of the literal block.
    @param errors: A list of the errors generated by parsing.  Any
        new errors generated while will tokenizing this paragraph
        will be appended to this list.
    @return: The line number of the first line following the literal
        block.
    """
    linenum = start + 1
    while linenum < len(lines):
        # Find the indentation of this line.
        line = lines[linenum]
        indent = len(line) - len(line.lstrip())

        # A Dedent to block_indent ends the literal block.
        # (Ignore blank likes, though)
        if len(line) != indent and indent <= block_indent:
            break

        # Go on to the next line.
        linenum += 1

    # Add the token, and return the linenum after the token ends.
    contents = '\n'.join(ln[block_indent:] for ln in lines[start:linenum])
    contents = re.sub(r'(\A[ \n]*\n)|(\n[ \n]*\Z)', '', contents)
    tokens.append(Token(Token.LBLOCK, start, contents, block_indent))
    return linenum

def _tokenize_listart(
        lines: List[str],
        start: int,
        bullet_indent: int,
        tokens: List[Token],
        errors: List[ParseError]
        ) -> int:
    """
    Construct L{Token}s for the bullet and the first paragraph of the
    list item (or field) starting at C{lines[start]}, and append them
    to C{tokens}.  C{bullet_indent} should be the indentation of the
    list item.  Any errors generated while tokenizing will be
    appended to C{errors}.

    @param lines: The list of lines to be tokenized
    @param start: The index into C{lines} of the first line of the
        list item to be tokenized.
    @param bullet_indent: The indentation of C{lines[start]}.  This is
        the indentation of the list item.
    @param errors: A list of the errors generated by parsing.  Any
        new errors generated while will tokenizing this paragraph
        will be appended to this list.
    @return: The line number of the first line following the list
        item's first paragraph.
    """
    linenum = start + 1
    para_indent = None
    doublecolon = lines[start].rstrip()[-2:] == '::'

    # Get the contents of the bullet.
    match = _BULLET_RE.match(lines[start], bullet_indent)
    assert match is not None
    para_start = match.end()
    bcontents = lines[start][bullet_indent : para_start].strip()

    while linenum < len(lines):
        # Find the indentation of this line.
        line = lines[linenum]
        indent = len(line) - len(line.lstrip())

        # "::" markers end paragraphs.
        if doublecolon: break
        if line.rstrip()[-2:] == '::': doublecolon = True

        # A blank line ends the token
        if indent == len(line): break

        # Dedenting past bullet_indent ends the list item.
        if indent < bullet_indent: break

        # A line beginning with a bullet ends the token.
        if _BULLET_RE.match(line, indent): break

        # If this is the second line, set the paragraph indentation, or
        # end the token, as appropriate.
        if para_indent is None: para_indent = indent

        # A change in indentation ends the token
        if indent != para_indent: break

        # Go on to the next line.
        linenum += 1

    # Add the bullet token.
    tokens.append(Token(Token.BULLET, start, bcontents, bullet_indent,
                        inline=True))

    # Add the paragraph token.
    pcontents = ' '.join(
        [lines[start][para_start:].strip()] +
        [ln.strip() for ln in lines[start+1:linenum]]
        ).strip()
    if pcontents:
        tokens.append(Token(Token.PARA, start, pcontents, para_indent,
                            inline=True))

    # Return the linenum after the paragraph token ends.
    return linenum

def _tokenize_para(
        lines: List[str],
        start: int,
        para_indent: int,
        tokens: List[Token],
        errors: List[ParseError]
        ) -> int:
    """
    Construct a L{Token} containing the paragraph starting at
    C{lines[start]}, and append it to C{tokens}.  C{para_indent}
    should be the indentation of the paragraph .  Any errors
    generated while tokenizing the paragraph will be appended to
    C{errors}.

    @param lines: The list of lines to be tokenized
    @param start: The index into C{lines} of the first line of the
        paragraph to be tokenized.
    @param para_indent: The indentation of C{lines[start]}.  This is
        the indentation of the paragraph.
    @param errors: A list of the errors generated by parsing.  Any
        new errors generated while will tokenizing this paragraph
        will be appended to this list.
    @return: The line number of the first line following the
        paragraph.
    """
    linenum = start + 1
    doublecolon = False
    while linenum < len(lines):
        # Find the indentation of this line.
        line = lines[linenum]
        indent = len(line) - len(line.lstrip())

        # "::" markers end paragraphs.
        if doublecolon: break
        if line.rstrip()[-2:] == '::': doublecolon = True

        # Blank lines end paragraphs
        if indent == len(line): break

        # Indentation changes end paragraphs
        if indent != para_indent: break

        # List bullets end paragraphs
        if _BULLET_RE.match(line, indent): break

        # Check for mal-formatted field items.
        if line[indent] == '@':
            estr = "Possible mal-formatted field item."
            errors.append(TokenizationError(estr, linenum, is_fatal=False))

        # Go on to the next line.
        linenum += 1

    contents = [ln.strip() for ln in lines[start:linenum]]

    # Does this token look like a heading?
    if ((len(contents) < 2) or
        (contents[1][0] not in _HEADING_CHARS) or
        (abs(len(contents[0])-len(contents[1])) > 5)):
        looks_like_heading = False
    else:
        looks_like_heading = True
        for char in contents[1]:
            if char != contents[1][0]:
                looks_like_heading = False
                break

    if looks_like_heading:
        if len(contents[0]) != len(contents[1]):
            estr = ("Possible heading typo: the number of "+
                    "underline characters must match the "+
                    "number of heading characters.")
            errors.append(TokenizationError(estr, start, is_fatal=False))
        else:
            level = _HEADING_CHARS.index(contents[1][0])
            tokens.append(Token(Token.HEADING, start,
                                contents[0], para_indent, level))
            return start+2

    # Add the paragraph token, and return the linenum after it ends.
    tokens.append(Token(Token.PARA, start, ' '.join(contents), para_indent))
    return linenum

def _tokenize(text: str, errors: List[ParseError]) -> List[Token]:
    """
    Split a given formatted docstring into an ordered list of
    L{Token}s, according to the epytext markup rules.

    @param text: The epytext string
    @param errors: A list where any errors generated during parsing
        will be stored.  If no list is specified, then errors will
        generate exceptions.
    @return: a list of the L{Token}s that make up the given string.
    """
    tokens: List[Token] = []
    lines = text.split('\n')

    # Scan through the lines, determining what @type of token we're
    # dealing with, and tokenizing it, as appropriate.
    linenum = 0
    while linenum < len(lines):
        # Get the current line and its indentation.
        line = lines[linenum]
        indent = len(line)-len(line.lstrip())

        if indent == len(line):
            # Ignore blank lines.
            linenum += 1
            continue
        elif line[indent:indent+4] == '>>> ':
            # blocks starting with ">>> " are doctest block tokens.
            linenum = _tokenize_doctest(lines, linenum, indent,
                                        tokens, errors)
        elif _BULLET_RE.match(line, indent):
            # blocks starting with a bullet are LI start tokens.
            linenum = _tokenize_listart(lines, linenum, indent,
                                        tokens, errors)
            if tokens[-1].indent is not None:
                indent = tokens[-1].indent
        else:
            # Check for mal-formatted field items.
            if line[indent] == '@':
                estr = "Possible mal-formatted field item."
                errors.append(TokenizationError(estr, linenum, is_fatal=False))

            # anything else is either a paragraph or a heading.
            linenum = _tokenize_para(lines, linenum, indent, tokens, errors)

        # Paragraph tokens ending in '::' initiate literal blocks.
        if (tokens[-1].tag == Token.PARA and
            tokens[-1].contents[-2:] == '::'):
            tokens[-1].contents = tokens[-1].contents[:-1]
            linenum = _tokenize_literal(lines, linenum, indent, tokens, errors)

    return tokens


##################################################
## Inline markup ("colorizing")
##################################################

# Assorted regular expressions used for colorizing.
_BRACE_RE = re.compile(r'{|}')
_TARGET_RE = re.compile(r'^(.*?)\s*<(?:URI:|URL:)?([^<>]+)>$')

def _colorize(token: Token, errors: List[ParseError], tagName: str = 'para') -> Element:
    """
    Given a string containing the contents of a paragraph, produce a
    DOM C{Element} encoding that paragraph.  Colorized regions are
    represented using DOM C{Element}s, and text is represented using
    DOM C{Text}s.

    @param errors: A list of errors.  Any newly generated errors will
        be appended to this list.
    @type errors: C{list} of C{string}

    @param tagName: The element tag for the DOM C{Element} that should
        be generated.
    @type tagName: C{string}

    @return: a DOM C{Element} encoding the given paragraph.
    @returntype: C{Element}
    """
    text = token.contents

    # Maintain a stack of DOM elements, containing the ancestors of
    # the text currently being analyzed.  New elements are pushed when
    # "{" is encountered, and old elements are popped when "}" is
    # encountered.
    stack = [Element(tagName)]

    # This is just used to make error-reporting friendlier.  It's a
    # stack parallel to "stack" containing the index of each element's
    # open brace.
    openbrace_stack = [0]

    # Process the string, scanning for '{' and '}'s.  start is the
    # index of the first unprocessed character.  Each time through the
    # loop, we process the text from the first unprocessed character
    # to the next open or close brace.
    start = 0
    while 1:
        match = _BRACE_RE.search(text, start)
        if match is None: break
        end = match.start()

        # Open braces start new colorizing elements.  When preceeded
        # by a capital letter, they specify a colored region, as
        # defined by the _COLORIZING_TAGS dictionary.  Otherwise,
        # use a special "literal braces" element (with tag "litbrace"),
        # and convert them to literal braces once we find the matching
        # close-brace.
        if match.group() == '{':
            if (end>0) and 'A' <= text[end-1] <= 'Z':
                if (end-1) > start:
                    stack[-1].children.append(text[start:end-1])
                if text[end-1] not in _COLORIZING_TAGS:
                    estr = "Unknown inline markup tag."
                    errors.append(ColorizingError(estr, token, end-1))
                    stack.append(Element('unknown'))
                else:
                    tag = _COLORIZING_TAGS[text[end-1]]
                    stack.append(Element(tag))
            else:
                if end > start:
                    stack[-1].children.append(text[start:end])
                stack.append(Element('litbrace'))
            openbrace_stack.append(end)
            stack[-2].children.append(stack[-1])

        # Close braces end colorizing elements.
        elif match.group() == '}':
            # Check for (and ignore) unbalanced braces.
            if len(stack) <= 1:
                estr = "Unbalanced '}'."
                errors.append(ColorizingError(estr, token, end))
                start = end + 1
                continue

            # Add any remaining text.
            if end > start:
                stack[-1].children.append(text[start:end])

            # Special handling for symbols:
            if stack[-1].tag == 'symbol':
                if (len(stack[-1].children) != 1 or
                    not isinstance(stack[-1].children[0], str)):
                    estr = "Invalid symbol code."
                    errors.append(ColorizingError(estr, token, end))
                else:
                    symb = stack[-1].children[0]
                    if symb in _SYMBOLS:
                        # It's a symbol
                        stack[-2].children[-1] = Element('symbol', symb)
                    else:
                        estr = "Invalid symbol code."
                        errors.append(ColorizingError(estr, token, end))

            # Special handling for escape elements:
            if stack[-1].tag == 'escape':
                if (len(stack[-1].children) != 1 or
                    not isinstance(stack[-1].children[0], str)):
                    estr = "Invalid escape code."
                    errors.append(ColorizingError(estr, token, end))
                else:
                    escp = stack[-1].children[0]
                    if escp in _ESCAPES:
                        # It's an escape from _ESCPAES
                        stack[-2].children[-1] = _ESCAPES[escp]
                    elif len(escp) == 1:
                        # It's a single-character escape (eg E{.})
                        stack[-2].children[-1] = escp
                    else:
                        estr = "Invalid escape code."
                        errors.append(ColorizingError(estr, token, end))

            # Special handling for literal braces elements:
            if stack[-1].tag == 'litbrace':
                stack[-2].children[-1:] = ['{'] + cast(List[str], stack[-1].children) + ['}']

            # Special handling for link-type elements:
            if stack[-1].tag in _LINK_COLORIZING_TAGS:
                _colorize_link(stack[-1], token, end, errors)

            # Pop the completed element.
            openbrace_stack.pop()
            stack.pop()

        start = end+1

    # Add any final text.
    if start < len(text):
        stack[-1].children.append(text[start:])

    if len(stack) != 1:
        estr = "Unbalanced '{'."
        errors.append(ColorizingError(estr, token, openbrace_stack[-1]))

    return stack[0]

def _colorize_link(link: Element, token: Token, end: int, errors: List[ParseError]) -> None:
    variables = link.children[:]

    # If the last child isn't text, we know it's bad.
    if len(variables)==0 or not isinstance(variables[-1], str):
        estr = f"Bad {link.tag} target."
        errors.append(ColorizingError(estr, token, end))
        return

    # Did they provide an explicit target?
    match2 = _TARGET_RE.match(variables[-1])
    if match2:
        (text, target) = match2.groups()
        variables[-1] = text
    # Can we extract an implicit target?
    elif len(variables) == 1:
        target = cast(str, variables[0])
    else:
        estr = f"Bad {link.tag} target."
        errors.append(ColorizingError(estr, token, end))
        return

    # Construct the name element.
    name_elt = Element('name', *variables)

    # Clean up the target.  For URIs, assume http or mailto if they
    # don't specify (no relative urls)
    target = re.sub(r'\s', '', target)
    if link.tag=='uri':
        if not re.match(r'\w+:', target):
            if re.match(r'\w+@(\w+)(\.\w+)*', target):
                target = 'mailto:' + target
            else:
                target = 'http://'+target
    elif link.tag=='link':
        # Remove arg lists for functions (e.g., L{_colorize_link()})
        target = re.sub(r'\(.*\)$', '', target)
        if not re.match(r'^[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)*$', target):
            estr = "Bad link target."
            errors.append(ColorizingError(estr, token, end))
            return

    # Construct the target element.
    target_elt = Element('target', target, lineno=str(token.startline))

    # Add them to the link element.
    link.children = [name_elt, target_elt]

##################################################
## Parse Errors
##################################################

class TokenizationError(ParseError):
    """
    An error generated while tokenizing a formatted documentation
    string.
    """

class StructuringError(ParseError):
    """
    An error generated while structuring a formatted documentation
    string.
    """

class ColorizingError(ParseError):
    """
    An error generated while colorizing a paragraph.
    """
    def __init__(self, descr: str, token: Token, charnum: int, is_fatal: bool = True):
        """
        Construct a new colorizing exception.

        @param descr: A short description of the error.
        @param token: The token where the error occured
        @param charnum: The character index of the position in
            C{token} where the error occured.
        """
        ParseError.__init__(self, descr, token.startline, is_fatal)
        self.token = token
        self.charnum = charnum

    CONTEXT_RANGE = 20
    def descr(self) -> str:
        RANGE = self.CONTEXT_RANGE
        if self.charnum <= RANGE:
            left = self.token.contents[0:self.charnum]
        else:
            left = '...'+self.token.contents[self.charnum-RANGE:self.charnum]
        if (len(self.token.contents)-self.charnum) <= RANGE:
            right = self.token.contents[self.charnum:]
        else:
            right = (self.token.contents[self.charnum:self.charnum+RANGE]
                     + '...')
        return f"{self._descr}\n\n{left}{right}\n{' '*len(left)}^"

#################################################################
##                    SUPPORT FOR EPYDOC
#################################################################

def parse_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted using epytext; and
    return a L{ParsedDocstring} representation of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    tree = parse(docstring, errors)
    if tree is None:
        return ParsedEpytextDocstring(None, ())

    tree_children = cast(List[Element], tree.children)

    fields = []
    if tree_children and tree_children[-1].tag == 'fieldlist':
        # Take field list out of the document tree.
        field_list = tree_children.pop()
        field_children = cast(List[Element], field_list.children)

        for field in field_children:
            # Get the tag
            tag = cast(str, cast(Element, field.children.pop(0)).children[0]).lower()

            # Get the argument.
            if field.children and cast(Element, field.children[0]).tag == 'arg':
                arg: Optional[str] = \
                    cast(str, cast(Element, field.children.pop(0)).children[0])
            else:
                arg = None

            # Process the field.
            field.tag = 'epytext'
            fieldDoc = ParsedEpytextDocstring(field, ())
            lineno = int(field.attribs['lineno'])
            fields.append(Field(tag, arg, fieldDoc, lineno))

    # Save the remaining docstring as the description.
    if tree_children and tree_children[0].children:
        return ParsedEpytextDocstring(tree, fields)
    else:
        return ParsedEpytextDocstring(None, fields)


class ParsedEpytextDocstring(ParsedDocstring):
    SYMBOL_TO_CODEPOINT = {
        # Symbols
        '<-': 8592, '->': 8594, '^': 8593, 'v': 8595,

        # Greek letters
        'alpha': 945, 'beta': 946, 'gamma': 947,
        'delta': 948, 'epsilon': 949, 'zeta': 950,
        'eta': 951, 'theta': 952, 'iota': 953,
        'kappa': 954, 'lambda': 955, 'mu': 956,
        'nu': 957, 'xi': 958, 'omicron': 959,
        'pi': 960, 'rho': 961, 'sigma': 963,
        'tau': 964, 'upsilon': 965, 'phi': 966,
        'chi': 967, 'psi': 968, 'omega': 969,
        'Alpha': 913, 'Beta': 914, 'Gamma': 915,
        'Delta': 916, 'Epsilon': 917, 'Zeta': 918,
        'Eta': 919, 'Theta': 920, 'Iota': 921,
        'Kappa': 922, 'Lambda': 923, 'Mu': 924,
        'Nu': 925, 'Xi': 926, 'Omicron': 927,
        'Pi': 928, 'Rho': 929, 'Sigma': 931,
        'Tau': 932, 'Upsilon': 933, 'Phi': 934,
        'Chi': 935, 'Psi': 936, 'Omega': 937,

        # HTML character entities
        'larr': 8592, 'rarr': 8594, 'uarr': 8593,
        'darr': 8595, 'harr': 8596, 'crarr': 8629,
        'lArr': 8656, 'rArr': 8658, 'uArr': 8657,
        'dArr': 8659, 'hArr': 8660,
        'copy': 169, 'times': 215, 'forall': 8704,
        'exist': 8707, 'part': 8706,
        'empty': 8709, 'isin': 8712, 'notin': 8713,
        'ni': 8715, 'prod': 8719, 'sum': 8721,
        'prop': 8733, 'infin': 8734, 'ang': 8736,
        'and': 8743, 'or': 8744, 'cap': 8745, 'cup': 8746,
        'int': 8747, 'there4': 8756, 'sim': 8764,
        'cong': 8773, 'asymp': 8776, 'ne': 8800,
        'equiv': 8801, 'le': 8804, 'ge': 8805,
        'sub': 8834, 'sup': 8835, 'nsub': 8836,
        'sube': 8838, 'supe': 8839, 'oplus': 8853,
        'otimes': 8855, 'perp': 8869,

        # Alternate (long) names
        'infinity': 8734, 'integral': 8747, 'product': 8719,
        '<=': 8804, '>=': 8805,
        }

    def __init__(self, body: Optional[Element], fields: Sequence['Field']):
        ParsedDocstring.__init__(self, fields)
        self._tree = body
        # Caching:
        self._stan: Optional[Tag] = None

    def __str__(self) -> str:
        return str(self._tree)

    @property
    def has_body(self) -> bool:
        return self._tree is not None

    def to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        if self._stan is not None:
            return self._stan
        if self._tree is None:
            self._stan = Tag('')
        else:
            self._stan = self._to_stan(self._tree, docstring_linker)
        return self._stan

    def _to_stan(self,
            tree: Union[Element, str],
            linker: DocstringLinker,
            seclevel: int = 0
            ) -> Any:
        if isinstance(tree, str):
            return tree

        if tree.tag == 'section':
            seclevel += 1

        # Process the variables first.
        variables = [self._to_stan(c, linker, seclevel) for c in tree.children]

        # Perform the approriate action for the DOM tree type.
        if tree.tag == 'para':
            if tree.attribs.get('inline'):
                return variables
            else:
                return tags.p(*variables)
        elif tree.tag == 'code':
            return tags.code(*variables)
        elif tree.tag == 'uri':
            return tags.a(variables[0], href=variables[1], target='_top')
        elif tree.tag == 'link':
            label, target = variables
            lineno = int(cast(Element, tree.children[1]).attribs['lineno'])
            return linker.link_xref(target, label, lineno)
        elif tree.tag == 'target':
            value, = variables
            return value
        elif tree.tag == 'italic':
            return tags.i(*variables)
        elif tree.tag == 'math':
            return tags.i(*variables, class_='math')
        elif tree.tag == 'bold':
            return tags.b(*variables)
        elif tree.tag == 'ulist':
            return tags.ul(*variables)
        elif tree.tag == 'olist':
            stan = tags.ol(*variables)
            start = tree.attribs.get('start', '1')
            if start != '1':
                stan(start=start)
            return stan
        elif tree.tag == 'li':
            return tags.li(*variables)
        elif tree.tag == 'heading':
            return getattr(tags, f'h{seclevel:d}')(*variables)
        elif tree.tag == 'literalblock':
            variables.append('\n')
            return tags.pre('\n', *variables, class_='literalblock')
        elif tree.tag == 'doctestblock':
            return colorize_doctest(cast(str, tree.children[0]).strip())
        elif tree.tag in ('fieldlist', 'tag', 'arg'):
            raise AssertionError("There should not be any field lists left")
        elif tree.tag in ('epytext', 'section', 'name'):
            return Tag('')(*variables)
        elif tree.tag == 'symbol':
            symbol = cast(str, tree.children[0])
            return CharRef(self.SYMBOL_TO_CODEPOINT[symbol])
        else:
            raise AssertionError(f"Unknown epytext DOM element {tree.tag!r}")
