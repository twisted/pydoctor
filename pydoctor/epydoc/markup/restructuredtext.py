#
# restructuredtext.py: ReStructuredText docstring parsing
# Edward Loper
#
# Created [06/28/03 02:52 AM]
#
"""
Epydoc parser for ReStructuredText strings.  ReStructuredText is the
standard markup language used by the Docutils project.
L{parse_docstring()} provides the primary interface to this module; it
returns a L{ParsedRstDocstring}, which supports all of the methods
defined by L{ParsedDocstring}.

L{ParsedRstDocstring} is basically just a L{ParsedDocstring} wrapper
for the C{nodes.document} class.

B{Creating C{ParsedRstDocstring}s}:

C{ParsedRstDocstring}s are created by the L{parse_docstring} function,
using the C{docutils.core.publish_string()} method, with the following
helpers:

  - An L{_EpydocReader} is used to capture all error messages as it
    parses the docstring.
  - A L{_DocumentPseudoWriter} is used to extract the document itself,
    without actually writing any output.  The document is saved for
    further processing.  The settings for the writer are copied from
    C{docutils.writers.html4css1.Writer}, since those settings will
    be used when we actually write the docstring to html.

@var CONSOLIDATED_FIELDS: A dictionary encoding the set of
'consolidated fields' that can be used.  Each consolidated field is
marked by a single tag, and contains a single bulleted list, where
each list item starts with an identifier, marked as interpreted text
(C{`...`}).  This module automatically splits these consolidated
fields into individual fields.  The keys of C{CONSOLIDATED_FIELDS} are
the names of possible consolidated fields; and the values are the
names of the field tags that should be used for individual entries in
the list.
"""
from __future__ import annotations
from contextlib import contextmanager
from types import ModuleType

__docformat__ = 'epytext en'

from typing import Any, Iterable, Iterator, List, Optional, Sequence, Set, Tuple, cast

from docutils import nodes
from docutils.utils import SystemMessage
from docutils.core import publish_string
from docutils.writers import Writer
from docutils.parsers.rst.directives.admonitions import BaseAdmonition # type: ignore[import-untyped]
from docutils.readers.standalone import Reader as StandaloneReader
from docutils.utils import Reporter
from docutils.parsers.rst import Directive, directives
from docutils.transforms import Transform, frontmatter
from docutils.parsers.rst import roles
import docutils.parsers.rst.states

from pydoctor.epydoc.markup import Field, ParseError, ParsedDocstring, ParserFunction
from pydoctor.epydoc.markup.plaintext import ParsedPlaintextDocstring
from pydoctor.epydoc.docutils import new_document, set_node_attributes
from pydoctor.model import Documentable
from pydoctor.sphinx import (ALL_SUPPORTED_ROLES, SUPPORTED_DEFAULT_REFTYPES, 
                             SUPPORTED_DOMAINS, SUPPORTED_EXTERNAL_DOMAINS, 
                             SUPPORTED_EXTERNAL_STD_REFTYPES, parse_domain_reftype)

#: A dictionary whose keys are the "consolidated fields" that are
#: recognized by epydoc; and whose values are the corresponding epydoc
#: field names that should be used for the individual fields.
CONSOLIDATED_FIELDS = {
    'parameters': 'param',
    'arguments': 'arg',
    'exceptions': 'except',
    'variables': 'var',
    'ivariables': 'ivar',
    'cvariables': 'cvar',
    'groups': 'group',
    'types': 'type',
    'keywords': 'keyword',
    }

#: A list of consolidated fields whose bodies may be specified using a
#: definition list, rather than a bulleted list.  For these fields, the
#: 'classifier' for each term in the definition list is translated into
#: a @type field.
CONSOLIDATED_DEFLIST_FIELDS = ['param', 'arg', 'var', 'ivar', 'cvar', 'keyword']

def parse_docstring(docstring: str, 
                    errors: List[ParseError], 
                    ) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted using
    ReStructuredText; and return a L{ParsedDocstring} representation
    of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    writer = _DocumentPseudoWriter()
    reader = _EpydocReader(errors) # Outputs errors to the list.
    with patch_docutils_role_function(errors):
        publish_string(docstring, writer=writer, reader=reader,
                       settings_overrides={'report_level':10000,
                                           'halt_level':10000,
                                           'warning_stream':None})
    document = writer.document
    visitor = _SplitFieldsTranslator(document, errors)
    document.walk(visitor)

    return ParsedRstDocstring(document, visitor.fields)

def get_parser(obj:Documentable) -> ParserFunction:
    """
    Get the L{parse_docstring} function. 
    """
    return parse_docstring

class OptimizedReporter(Reporter):
    """A reporter that ignores all debug messages.  This is used to
    shave a couple seconds off of epydoc's run time, since docutils
    isn't very fast about processing its own debug messages.
    """

    def debug(self, *args: object, **kwargs: object) -> None:
        pass

class ParsedRstDocstring(ParsedDocstring):
    """
    An encoded version of a ReStructuredText docstring.  The contents
    of the docstring are encoded in the L{_document} instance
    variable.
    """

    def __init__(self, document: nodes.document, fields: Sequence[Field]):
        self._document = document
        """A ReStructuredText document, encoding the docstring."""

        document.reporter = OptimizedReporter(
            document.reporter.source, 
            report_level=10000, halt_level=10000, 
            stream='')

        ParsedDocstring.__init__(self, fields)

    @property
    def has_body(self) -> bool:
        return any(
            isinstance(child, nodes.Text) or child.children
            for child in self._document.children
            )

    def to_node(self) -> nodes.document:
        return self._document

    def __repr__(self) -> str:
        return '<ParsedRstDocstring: ...>'

class _EpydocReader(StandaloneReader):
    """
    A reader that captures all errors that are generated by parsing,
    and appends them to a list as L{ParseError}.
    """

    def __init__(self, errors: List[ParseError]):
        self._errors = errors
        StandaloneReader.__init__(self)

    def get_transforms(self) -> List[Transform]:
        # Remove the DocInfo transform, to ensure that :author: fields
        # are correctly handled.
        return [t for t in StandaloneReader.get_transforms(self)
                if t != frontmatter.DocInfo]

    def new_document(self) -> nodes.document:
        document = new_document(self.source.source_path, self.settings)
        # Capture all warning messages.
        document.reporter.attach_observer(self.report)
        # Return the new document.
        return document

    def report(self, error: nodes.system_message) -> None:
        level: int = error['level']
        is_fatal = level >= Reporter.ERROR_LEVEL

        linenum: Optional[int] = error.get('line')

        msg = ''.join(c.astext() for c in error)

        self._errors.append(ParseError(msg, linenum, is_fatal))

class _DocumentPseudoWriter(Writer):
    """
    A pseudo-writer for the docutils framework, that can be used to
    access the document itself.  The output of C{_DocumentPseudoWriter}
    is just an empty string; but after it has been used, the most
    recently processed document is available as the instance variable
    C{document}.
    """

    document: nodes.document
    """The most recently processed document."""

    def translate(self) -> None:
        self.output = ''

class _SplitFieldsTranslator(nodes.NodeVisitor):
    """
    A docutils translator that removes all fields from a document, and
    collects them into the instance variable C{fields}

    @ivar fields: The fields of the most recently walked document.
    @type fields: C{list} of L{Field<markup.Field>}
    """

    ALLOW_UNMARKED_ARG_IN_CONSOLIDATED_FIELD = True
    """If true, then consolidated fields are not required to mark
    arguments with C{`backticks`}.  (This is currently only
    implemented for consolidated fields expressed as definition lists;
    consolidated fields expressed as unordered lists still require
    backticks for now."""

    def __init__(self, document: nodes.document, errors: List[ParseError]):
        nodes.NodeVisitor.__init__(self, document)
        self._errors = errors
        self.fields: List[Field] = []
        self._newfields: Set[str] = set()

    def visit_document(self, node: nodes.Node) -> None:
        self.fields = []

    def visit_field(self, node: nodes.Node) -> None:
        # Remove the field from the tree.
        node.parent.remove(node)

        # Extract the field name & optional argument
        # FIXME: https://github.com/twisted/pydoctor/issues/267
        #   Support combined parameter type and description, if the type is a single word like::
        #       :param str user_agent: user agent
        tag = node[0].astext().split(None, 1)
        tagname = tag[0]
        if len(tag)>1: 
            arg = tag[1]
        else: 
            arg = None

        # Handle special fields:
        fbody = node[1]
        if arg is None:
            for (list_tag, entry_tag) in CONSOLIDATED_FIELDS.items():
                if tagname.lower() == list_tag:
                    try:
                        self.handle_consolidated_field(fbody, entry_tag)
                        return
                    except ValueError as e:
                        estr = 'Unable to split consolidated field '
                        estr += f'"{tagname}" - {e}'
                        self._errors.append(ParseError(estr, node.line,
                                                       is_fatal=False))

                        # Use a @newfield to let it be displayed as-is.
                        if tagname.lower() not in self._newfields:
                            newfield = Field('newfield', tagname.lower(),
                                             ParsedPlaintextDocstring(tagname),
                                             node.line - 1)
                            self.fields.append(newfield)
                            self._newfields.add(tagname.lower())

        self._add_field(tagname, arg, fbody, node.line)

    def _add_field(self,
            tagname: str,
            arg: Optional[str],
            fbody: Iterable[nodes.Node],
            lineno: int
            ) -> None:
        field_doc = self.document.copy()
        for child in fbody: 
            field_doc.append(child)
        field_parsed_doc = ParsedRstDocstring(field_doc, ())
        self.fields.append(Field(tagname, arg, field_parsed_doc, lineno - 1))

    def visit_field_list(self, node: nodes.Node) -> None:
        # Remove the field list from the tree.  The visitor will still walk
        # over the node's children.
        node.parent.remove(node)

    def handle_consolidated_field(self, body: Sequence[nodes.Node], tagname: str) -> None:
        """
        Attempt to handle a consolidated section.
        """
        if len(body) != 1:
            raise ValueError('does not contain a single list.')
        elif body[0].tagname == 'bullet_list':
            self.handle_consolidated_bullet_list(body[0], tagname)
        elif (body[0].tagname == 'definition_list' and
              tagname in CONSOLIDATED_DEFLIST_FIELDS):
            self.handle_consolidated_definition_list(body[0], tagname)
        elif tagname in CONSOLIDATED_DEFLIST_FIELDS:
            raise ValueError('does not contain a bulleted list or '
                             'definition list.')
        else:
            raise ValueError('does not contain a bulleted list.')

    def handle_consolidated_bullet_list(self, items: Iterable[nodes.Node], tagname: str) -> None:
        # Check the contents of the list.  In particular, each list
        # item should have the form:
        #   - `arg`: description...
        n = 0
        _BAD_ITEM = ("list item %d is not well formed.  Each item must "
                     "consist of a single marked identifier (e.g., `x`), "
                     "optionally followed by a colon or dash and a "
                     "description.")
        for item in items:
            n += 1
            if item.tagname != 'list_item' or len(item) == 0:
                raise ValueError('bad bulleted list (bad child %d).' % n)
            if item[0].tagname != 'paragraph':
                if item[0].tagname == 'definition_list':
                    raise ValueError(('list item %d contains a definition '+
                                      'list (it\'s probably indented '+
                                      'wrong).') % n)
                else:
                    raise ValueError(_BAD_ITEM % n)
            if len(item[0]) == 0:
                raise ValueError(_BAD_ITEM % n)
            if item[0][0].tagname != 'title_reference':
                raise ValueError(_BAD_ITEM % n)

        # Everything looks good; convert to multiple fields.
        for item in items:
            # Extract the arg
            arg = item[0][0].astext()

            # Extract the field body, and remove the arg
            fbody = item[:]
            fbody[0] = fbody[0].copy()
            fbody[0][:] = item[0][1:]

            # Remove the separating ":", if present
            if (len(fbody[0]) > 0 and
                isinstance(fbody[0][0], nodes.Text)):
                text = fbody[0][0].astext()
                if text[:1] in ':-':
                    fbody[0][0] = nodes.Text(text[1:].lstrip())
                elif text[:2] in (' -', ' :'):
                    fbody[0][0] = nodes.Text(text[2:].lstrip())

            # Wrap the field body, and add a new field
            self._add_field(tagname, arg, fbody, fbody[0].line)

    def handle_consolidated_definition_list(self, items: Iterable[nodes.Node], tagname: str) -> None:
        # Check the list contents.
        n = 0
        _BAD_ITEM = ("item %d is not well formed.  Each item's term must "
                     "consist of a single marked identifier (e.g., `x`), "
                     "optionally followed by a space, colon, space, and "
                     "a type description.")
        for item in items:
            n += 1
            if (item.tagname != 'definition_list_item' or len(item) < 2 or
                item[-1].tagname != 'definition'):
                raise ValueError('bad definition list (bad child %d).' % n)
            if len(item) > 3:
                raise ValueError(_BAD_ITEM % n)
            if not ((item[0][0].tagname == 'title_reference') or
                    (self.ALLOW_UNMARKED_ARG_IN_CONSOLIDATED_FIELD and
                     isinstance(item[0][0], nodes.Text))):
                raise ValueError(_BAD_ITEM % n)
            for child in item[0][1:]:
                if child.astext() != '':
                    raise ValueError(_BAD_ITEM % n)

        # Extract it.
        for item in items:
            # The basic field.
            arg = item[0][0].astext()
            lineno = item[0].line
            fbody = item[-1]
            self._add_field(tagname, arg, fbody, lineno)
            # If there's a classifier, treat it as a type.
            if len(item) == 3:
                type_descr = item[1]
                self._add_field('type', arg, type_descr, lineno)

    def unknown_visit(self, node: nodes.Node) -> None:
        'Ignore all unknown nodes'

versionlabels = {
    'versionadded':   'New in version %s',
    'versionchanged': 'Changed in version %s',
    'deprecated':     'Deprecated since version %s',
}

versionlabel_classes = {
    'versionadded':     'added',
    'versionchanged':   'changed',
    'deprecated':       'deprecated',
}

class VersionChange(Directive):
    """
    Directive to describe a change/addition/deprecation in a specific version.
    """
    class versionmodified(nodes.Admonition, nodes.TextElement):
        """Node for version change entries.
        Currently used for "versionadded", "versionchanged" and "deprecated"
        directives.
        """
    
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True

    def run(self) -> List[nodes.Node]:
        node = self.versionmodified()
        node.document = self.state.document
        node['type'] = self.name
        node['version'] = self.arguments[0]
        text = versionlabels[self.name] % self.arguments[0]
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1],
                                                      self.lineno + 1)
            para = nodes.paragraph(self.arguments[1], '', *inodes)
            node.append(para)
        else:
            messages = []
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        classes = ['versionmodified', versionlabel_classes[self.name]]
        if len(node):
            if isinstance(node[0], nodes.paragraph) and node[0].rawsource:
                content = nodes.inline(node[0].rawsource)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(nodes.paragraph('', '', content))

            para = cast(nodes.paragraph, node[0])
            para.insert(0, nodes.inline('', '%s: ' % text, classes=classes))
        else:
            para = nodes.paragraph('', '',
                                   nodes.inline('', '%s.' % text,
                                                classes=classes), )
            node.append(para)

        ret = [node]  # type: List[nodes.Node]
        ret += messages
        return ret

# Do like Sphinx does for the seealso directive. 
class SeeAlso(BaseAdmonition):
    """
    An admonition mentioning things to look at as reference.
    """
    class seealso(nodes.Admonition, nodes.Element):
        """Custom "see also" admonition node."""

    node_class = seealso

class PythonCodeDirective(Directive):
    """
    A custom restructuredtext directive which can be used to display
    syntax-highlighted Python code blocks.  This directive takes no
    arguments, and the body should contain only Python code.  This
    directive can be used instead of doctest blocks when it is
    inconvenient to list prompts on each line, or when you would
    prefer that the output not contain prompts (e.g., to make
    copy/paste easier).
    """

    has_content = True
    
    def run(self) -> List[nodes.Node]:
        text = '\n'.join(self.content)
        node = nodes.doctest_block(text, text, codeblock=True)
        return [ node ]

class DocutilsAndSphinxCodeBlockAdapter(PythonCodeDirective):
    # Docutils and Sphinx code blocks have both one optional argument, 
    # so we accept it here as well but do nothing with it.
    required_arguments = 0
    optional_arguments = 1

    # Listing all options that docutils.parsers.rst.directives.body.CodeBlock provides
    # And also sphinx.directives.code.CodeBlock. We don't care about their values, 
    # we just don't want to see them in self.content.
    option_spec = {'class': directives.class_option,
                'name': directives.unchanged,
                'number-lines': directives.unchanged, # integer or None
                'force': directives.flag,
                'linenos': directives.flag,
                'dedent': directives.unchanged, # integer or None
                'lineno-start': int,
                'emphasize-lines': directives.unchanged_required,
                'caption': directives.unchanged_required,
    }

def parse_external(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns a tuple: (inventory name, role)

    @raises ValueError: If the format is invalid.
    """
    assert name.startswith('external'), name
    # either we have an explicit inventory name, i.e,
    # :external+inv:reftype:        or
    # :external+inv:domain:reftype:
    # or we look in all inventories, i.e.,
    # :external:reftype:            or
    # :external:domain:reftype:     or
    # :external: 
    suffix = name[9:]
    if len(name) > len('external'):
        if name[8] == '+':
            parts = suffix.split(':', 1)
            if len(parts) == 2:
                inv_name, suffix = parts
                if inv_name and suffix:
                    return inv_name, suffix
            elif len(parts) == 1:
                inv_name, = parts
                if inv_name:
                    return inv_name, None
        elif name[8] == ':' and suffix:
            return None, suffix
        msg = f'Malformed :external: role name: {name!r}'
        raise ValueError(msg)
    return None, None

class LinkRole:
    def __init__(self, errors: List[ParseError]) -> None:
        self.errors = errors
    
    # roles._RoleFn
    def __call__(self, role: str, rawtext: str, text: str, lineno: int, 
                inliner: docutils.parsers.rst.states.Inliner,
                options:Any=None, content:Any=None) -> 'tuple[list[nodes.Node], list[nodes.Node]]':
        
        # See https://www.sphinx-doc.org/en/master/usage/referencing.html
        # and https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
        invname: Optional[str] = None
        domain: Optional[str] = None
        reftype: Optional[str] = None
        external: bool = False
        if role.startswith('external'):
            try:
                invname, suffix = parse_external(role)
                if suffix is not None:
                    domain, reftype = parse_domain_reftype(suffix)
            except ValueError as e:
                self.errors.append(ParseError(str(e), lineno, is_fatal=False))
                return [], []
            else:
                external = True
        elif role:
            try:
                domain, reftype = parse_domain_reftype(role)
            except ValueError as e:
                self.errors.append(ParseError(str(e), lineno, is_fatal=False))
                return [], []
        
        if reftype in SUPPORTED_DOMAINS and domain is None:
            self.errors.append(ParseError('Malformed role name, domain is missing reference type', 
                                          lineno, is_fatal=False))
            return [], []

        if reftype in SUPPORTED_DEFAULT_REFTYPES:
            reftype = None
        
        if reftype in SUPPORTED_EXTERNAL_STD_REFTYPES and domain is None:
            external = True
            domain = 'std'
        
        if domain in SUPPORTED_EXTERNAL_DOMAINS:
            external = True
        
        text_node = nodes.Text(text)
        node = nodes.title_reference(rawtext, '', 
                                    invname=invname,
                                    domain=domain,
                                    reftype=reftype,
                                    external=external,
                                    lineno=lineno)
        
        set_node_attributes(node, children=[text_node], document=inliner.document) # type: ignore
        return [node], []

@contextmanager
def patch_docutils_role_function(errors:List[ParseError]) -> Iterator[None]:
    r"""
    Like sphinx, we are patching the L{docutils.parsers.rst.roles.role} function. 
    This function is a factory for role handlers functions. In order to handle any kind
    of roles names like C{:external+python:doc:`something`} (the role here is C{external+python:doc}, 
    we need to patch this function because Docutils only handles extact matches...
    
    Tip: To list roles contained in a given inventory, use the following command::

        python3 -m sphinx.ext.intersphinx https://docs.python.org/3/objects.inv | grep -v '^\s'
    
    """
    
    old_role = roles.role

    def new_role(role_name: str, language_module: ModuleType, 
                 lineno: int, reporter: Reporter) -> 'tuple[nodes._RoleFn, list[SystemMessage]]':
        
        if role_name in ALL_SUPPORTED_ROLES or any(
            role_name.startswith(f'{n}:') for n in ALL_SUPPORTED_ROLES) or \
            role_name.startswith('external+'): # 'external+' is a special case
            return LinkRole(errors), []
        
        return old_role(role_name, language_module, lineno, reporter) # type: ignore

    roles.role = new_role
    yield
    roles.role = old_role

# https://docutils.sourceforge.io/docs/ref/rst/directives.html#default-role
# there is no possible code path that triggers messages from the default role, 
# so that's ok to use an anonymous list here
roles.register_local_role('default-role', LinkRole([]))

directives.register_directive('python', PythonCodeDirective)
directives.register_directive('code', DocutilsAndSphinxCodeBlockAdapter)
directives.register_directive('code-block', DocutilsAndSphinxCodeBlockAdapter)
directives.register_directive('versionadded', VersionChange)
directives.register_directive('versionchanged', VersionChange)
directives.register_directive('deprecated', VersionChange)
directives.register_directive('seealso', SeeAlso)
