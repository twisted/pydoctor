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

from typing import Callable, ContextManager, List, Optional, Sequence, Iterator, TYPE_CHECKING
import abc
import sys
import re
from importlib import import_module
from inspect import getmodulename

from docutils import nodes, utils
from twisted.web.template import Tag, tags

from pydoctor import node2stan
from pydoctor.epydoc.docutils import set_node_attributes, build_table_of_content


# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    from pydoctor.model import Documentable

##################################################
## Contents
##################################################
#
# 1. ParsedDocstring abstract base class
# 2. Field class
# 3. Docstring Linker
# 4. ParseError exceptions
#

ParserFunction = Callable[[str, List['ParseError']], 'ParsedDocstring']

def get_supported_docformats() -> Iterator[str]:
    """
    Get the list of currently supported docformat.
    """
    for fileName in (path.name for path in importlib_resources.files('pydoctor.epydoc.markup').iterdir()):
        moduleName = getmodulename(fileName)
        if moduleName is None or moduleName.startswith("_"):
            continue
        else:
            yield moduleName

def get_parser_by_name(docformat: str, obj: Optional['Documentable'] = None) -> ParserFunction:
    """
    Get the C{parse_docstring(str, List[ParseError], bool) -> ParsedDocstring} function based on a parser name. 

    @raises ImportError: If the parser could not be imported, probably meaning that your are missing a dependency
        or it could be that the docformat name do not match any know L{pydoctor.epydoc.markup} submodules.
    """
    mod = import_module(f'pydoctor.epydoc.markup.{docformat}')
    # We can safely ignore this mypy warning, since we can be sure the 'get_parser' function exist and is "correct".
    return mod.get_parser(obj) # type:ignore[no-any-return]

def processtypes(parse:ParserFunction) -> ParserFunction:
    """
    Wraps a docstring parser function to provide option --process-types.
    """
    
    def _processtypes(doc: 'ParsedDocstring', errs: List['ParseError']) -> None:
        """
        Mutates the type fields of the given parsed docstring to replace 
        their body by parsed version with type auto-linking.
        """
        from pydoctor.epydoc.markup._types import ParsedTypeDocstring
        for field in doc.fields:
            if field.tag() in ParsedTypeDocstring.FIELDS:
                body = ParsedTypeDocstring(field.body().to_node(), lineno=field.lineno)
                append_warnings(body.warnings, errs, lineno=field.lineno+1)
                field.replace_body(body)
    
    def parse_and_processtypes(doc:str, errs:List['ParseError']) -> 'ParsedDocstring':
        parsed_doc = parse(doc, errs)
        _processtypes(parsed_doc, errs)
        return parsed_doc

    return parse_and_processtypes

##################################################
## ParsedDocstring
##################################################
class ParsedDocstring(abc.ABC):
    """
    A standard intermediate representation for parsed docstrings that
    can be used to generate output.  Parsed docstrings are produced by
    markup parsers such as L{pydoctor.epydoc.markup.epytext.parse_docstring()}
    or L{pydoctor.epydoc.markup.restructuredtext.parse_docstring()}.

    Subclasses must implement L{has_body()} and L{to_node()}.
    
    A default implementation for L{to_stan()} method, relying on L{to_node()} is provided.
    But some subclasses override this behaviour.
    
    Implementation of L{get_toc()} also relies on L{to_node()}.
    """

    def __init__(self, fields: Sequence['Field']):
        self.fields = fields
        """
        A list of L{Field}s, each of which encodes a single field.
        The field's bodies are encoded as C{ParsedDocstring}s.
        """

        self._stan: Optional[Tag] = None
        self._summary: Optional['ParsedDocstring'] = None

    @abc.abstractproperty
    def has_body(self) -> bool:
        """
        Does this docstring have a non-empty body?

        The body is the part of the docstring that remains after the fields
        have been split off.
        """
    
    def get_toc(self, depth: int) -> Optional['ParsedDocstring']:
        """
        The table of contents of the docstring if titles are defined or C{None}.
        """
        try:
            document = self.to_node()
        except NotImplementedError:
            return None
        contents = build_table_of_content(document, depth=depth)
        docstring_toc = utils.new_document('toc')
        if contents:
            docstring_toc.extend(contents)
            from pydoctor.epydoc.markup.restructuredtext import ParsedRstDocstring
            return ParsedRstDocstring(docstring_toc, ())
        else:
            return None

    def to_stan(self, docstring_linker: 'DocstringLinker') -> Tag:
        """
        Translate this docstring to a Stan tree.

        @note: The default implementation relies on functionalities 
            provided by L{node2stan.node2stan} and L{ParsedDocstring.to_node()}.

        @param docstring_linker: An HTML translator for crossreference
            links into and out of the docstring.
        @return: The docstring presented as a stan tree.
        @raises Exception: If something went wrong. Callers should generally catch C{Exception}
            when calling L{to_stan()}.
        """
        if self._stan is not None:
            return self._stan
        self._stan = Tag('', children=node2stan.node2stan(self.to_node(), docstring_linker).children)
        return self._stan
    
    @abc.abstractmethod
    def to_node(self) -> nodes.document:
        """
        Translate this docstring to a L{nodes.document}.

        @return: The docstring presented as a L{nodes.document}.

        @note: Some L{ParsedDocstring} subclasses do not support docutils nodes.
            This method might raise L{NotImplementedError} in such cases. (i.e. L{pydoctor.epydoc.markup._types.ParsedTypeDocstring})
        """
        raise NotImplementedError()
    
    def get_summary(self) -> 'ParsedDocstring':
        """
        Returns the summary of this docstring.
        
        @note: The summary is cached.
        """
        # Avoid rare cyclic import error, see https://github.com/twisted/pydoctor/pull/538#discussion_r845668735
        from pydoctor import epydoc2stan
        if self._summary is not None:
            return self._summary
        try: 
            _document = self.to_node()
            visitor = SummaryExtractor(_document)
            _document.walk(visitor)
        except Exception: 
            self._summary = epydoc2stan.ParsedStanOnly(tags.span(class_='undocumented')("Broken summary"))
        else:
            self._summary = visitor.summary or epydoc2stan.ParsedStanOnly(tags.span(class_='undocumented')("No summary"))
        return self._summary

      
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
    
    def replace_body(self, newbody:ParsedDocstring) -> None:
        self._body = newbody

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

    def link_to(self, target: str, label: "Flattenable") -> Tag:
        """
        Format a link to a Python identifier.
        This will resolve the identifier like Python itself would.

        @param target: The name of the Python identifier that
            should be linked to.
        @param label: The label to show for the link.
        @return: The link, or just the label if the target was not found.
        """
        raise NotImplementedError()

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
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

    def switch_context(self, ob:Optional['Documentable']) -> ContextManager[None]:
        """
        Switch the context of the linker, keeping the same underlying lookup rules.

        Useful to resolve links with the right L{Documentable} context but
        create correct - absolute or relative - links to be clicked on from another page 
        rather than the initial page of the context. "Cannot find link target" errors will be reported
        relatively to the new context object.

        Pass C{None} to always generate full URLs (for summaries for example), 
        in this case error will NOT be reported at all.
        """
        raise NotImplementedError()

##################################################
## ParseError exceptions
##################################################

def append_warnings(warns:List[str], errs:List['ParseError'], lineno:int) -> None:
    """
    Utility method to create non fatal L{ParseError}s and append them to the provided list.

    @param warns: The warnings strings.
    @param errs: The list of errors.
    """
    for warn in warns:
        errs.append(ParseError(warn, linenum=lineno, is_fatal=False))

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

class SummaryExtractor(nodes.NodeVisitor):
    """
    A docutils node visitor that extracts first sentences from
    the first paragraph in a document.
    """
    def __init__(self, document: nodes.document, maxchars:int=200) -> None:
        """
        @param document: The docutils document to extract a summary from.
        @param maxchars: Maximum of characters the summary can span. 
            Sentences are not cut in the middle, so the actual length
            might be longer if your have a large first paragraph.
        """
        super().__init__(document)
        self.summary: Optional['ParsedDocstring'] = None
        self.other_docs: bool = False
        self.maxchars = maxchars

    def visit_document(self, node: nodes.Node) -> None:
        self.summary = None

    _SENTENCE_RE_SPLIT = re.compile(r'( *[\.\?!][\'"\)\]]* *)')

    def visit_paragraph(self, node: nodes.Node) -> None:
        if self.summary is not None:
            # found a paragraph after the first one
            self.other_docs = True
            raise nodes.StopTraversal()

        summary_doc = utils.new_document('summary')
        summary_pieces = []

        # Extract the first sentences from the first paragraph until maximum number 
        # of characters is reach or until the end of the paragraph.
        char_count = 0

        for child in node:

            if char_count > self.maxchars:
                break
            
            if isinstance(child, nodes.Text):
                text = child.astext().replace('\n', ' ')
                sentences = [item for item in self._SENTENCE_RE_SPLIT.split(text) if item] # Not empty values only
                
                for i,s in enumerate(sentences):
                    
                    if char_count > self.maxchars:
                        # Leave final point alone.
                        if not (i == len(sentences)-1 and len(s)==1):
                            break

                    summary_pieces.append(set_node_attributes(nodes.Text(s), document=summary_doc))
                    char_count += len(s)

            else:
                summary_pieces.append(set_node_attributes(child.deepcopy(), document=summary_doc))
                char_count += len(''.join(node2stan.gettext(child)))
            
        if char_count > self.maxchars:
            if not summary_pieces[-1].astext().endswith('.'):
                summary_pieces.append(set_node_attributes(nodes.Text('...'), document=summary_doc))
            self.other_docs = True

        set_node_attributes(summary_doc, children=[
            set_node_attributes(nodes.paragraph('', ''), document=summary_doc, lineno=1, 
            children=summary_pieces)])

        from pydoctor.epydoc.markup.restructuredtext import ParsedRstDocstring
        self.summary = ParsedRstDocstring(summary_doc, fields=[])

    def visit_field(self, node: nodes.Node) -> None:
        raise nodes.SkipNode()

    def unknown_visit(self, node: nodes.Node) -> None:
        '''Ignore all unknown nodes'''
