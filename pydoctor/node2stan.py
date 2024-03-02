"""
Helper function to convert L{docutils} nodes to Stan tree.
"""
from __future__ import annotations

import re
import optparse
from typing import Any, ClassVar, Iterable, List, Optional, Sequence, Union, TYPE_CHECKING
import attr
from docutils.writers import html4css1
from docutils import nodes, frontend, __version_info__ as docutils_version_info

from twisted.web.template import Tag
if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    from pydoctor.epydoc.markup import DocstringLinker

from pydoctor.epydoc.docutils import get_lineno
from pydoctor.epydoc.doctest import colorize_codeblock, colorize_doctest
from pydoctor.stanutils import flatten, html2stan

def node2html(node: nodes.Node, docstring_linker: 'DocstringLinker') -> List[str]:
    """
    Convert a L{docutils.nodes.Node} object to HTML strings.
    """
    visitor = HTMLTranslator(node.document, docstring_linker)
    node.walkabout(visitor)
    return visitor.body

def node2stan(node: Union[nodes.Node, Iterable[nodes.Node]], docstring_linker: 'DocstringLinker') -> Tag:
    """
    Convert L{docutils.nodes.Node} objects to a Stan tree.

    @param node: An docutils document or a fragment of document.
    @return: The element as a stan tree.
    @note:  Any L{nodes.Node} can be passed to that function, the only requirement is 
        that the node's L{nodes.Node.document} attribute is set to a valid L{nodes.document} object.
    """
    html = []
    if isinstance(node, nodes.Node):
        html += node2html(node, docstring_linker)
    else:
        for child in node:
            html += node2html(child, docstring_linker)
    return html2stan(''.join(html))


def gettext(node: Union[nodes.Node, List[nodes.Node]]) -> List[str]:
    """Return the text inside the node(s)."""
    filtered: List[str] = []
    if isinstance(node, (nodes.Text)):
        filtered.append(node.astext())
    elif isinstance(node, (list, nodes.Element)):
        for child in node[:]:
            filtered.extend(gettext(child))
    return filtered


_TARGET_RE = re.compile(r'^(.*?)\s*<(?:URI:|URL:)?([^<>]+)>$')
_VALID_IDENTIFIER_RE = re.compile('[^0-9a-zA-Z_]')
_CALLABLE_RE = re.compile(r'^[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)*$')
_CALLABLE_ARGS_RE = re.compile(r'\(.*\)$')

@attr.s(auto_attribs=True)
class Reference:
    label: Union[str, Sequence[nodes.Node]]
    target: str
    invname: Optional[str] = None
    domain: Optional[str] = None
    reftype: Optional[str] = None
    external: bool = False

def parse_reference(node:nodes.Node) -> Reference:
    """
    Split a reference into (label, target).
    """
    label: Union[str, Sequence[nodes.Node]]
    if 'refuri' in node.attributes:
        # Epytext parsed or manually constructed nodes.
        label, target = node.children, node.attributes['refuri']
    else:
        # RST parsed.
        # Sanitize links spaning over multiple lines
        node_text = re.sub(r'\s', ' ', node.astext())
        m = _TARGET_RE.match(node_text)
        if m:
            label, target = m.groups()
        else:
            label = target = node_text
    # Support linking to functions and methods with parameters
    try:
        begin_parameters = target.index('(')
    except ValueError:
        pass
    else:
        if target.endswith(')') and _CALLABLE_RE.match(target, endpos=begin_parameters):
            # Remove arg lists for functions (e.g., L{_colorize_link()})
            target = _CALLABLE_ARGS_RE.sub('', target)
        
    return Reference(label, target, 
                     invname=node.attributes.get('invname'), 
                     domain=node.attributes.get('domain'),
                     reftype=node.attributes.get('reftype'),
                     external=node.attributes.get('external', False))

def _valid_identifier(s: str) -> str:
    """Remove invalid characters to create valid CSS identifiers. """
    return _VALID_IDENTIFIER_RE.sub('', s)

def _label2flattenable(label: Union[str, Sequence[nodes.Node]], linker:DocstringLinker) -> "Flattenable":
    if not isinstance(label, str):
        return node2stan(label, linker)
    else:
        return label

class HTMLTranslator(html4css1.HTMLTranslator):
    """
    Pydoctor's HTML translator.
    """
    
    settings: ClassVar[Optional[optparse.Values]] = None
    body: List[str]

    def __init__(self,
            document: nodes.document,
            docstring_linker: 'DocstringLinker'
            ):
        self._linker = docstring_linker

        # Set the document's settings.
        if self.settings is None:
            if docutils_version_info >= (0,19):
                # Direct access to OptionParser is deprecated from Docutils 0.19
                # FIXME: https://github.com/twisted/pydoctor/issues/504
                # Stubs are not up to date because we use pinned version of types-docutils
                settings = frontend.get_default_settings(html4css1.Writer()) # type:ignore[attr-defined]
            else:
                settings = frontend.OptionParser([html4css1.Writer()]).get_default_values()
            
            # Save default settings as class attribute not to re-compute it all the times
            self.__class__.settings = settings
        
        document.settings = self.settings

        super().__init__(document)

        # don't allow <h1> tags, start at <h2>
        # h1 is reserved for the page nodes.title. 
        self.section_level += 1

    # Handle interpreted text (crossreferences)
    def visit_title_reference(self, node: nodes.Node) -> None:
        lineno = get_lineno(node)
        ref = parse_reference(node)
        target = ref.target        
        label = _label2flattenable(ref.label, self._linker)
        link = self._linker.link_xref(target, label, lineno, 
                    invname=ref.invname, domain=ref.domain, 
                    reftype=ref.reftype, external=ref.external)
        self.body.append(flatten(link))
        raise nodes.SkipNode()
    
    # Handle internal references
    def visit_obj_reference(self, node: nodes.Node) -> None:
        ref = parse_reference(node)
        target = ref.target        
        label = _label2flattenable(ref.label, self._linker)
        self.body.append(flatten(self._linker.link_to(target, label)))
        raise nodes.SkipNode()

    def should_be_compact_paragraph(self, node: nodes.Node) -> bool:
        if self.document.children == [node]:
            return True
        else:
            return super().should_be_compact_paragraph(node)  # type: ignore[no-any-return]

    def visit_document(self, node: nodes.Node) -> None:
        pass

    def depart_document(self, node: nodes.Node) -> None:
        pass

    def starttag(self, node: nodes.Node, tagname: str, suffix: str = '\n', **attributes: Any) -> str:
        """
        This modified version of starttag makes a few changes to HTML
        tags, to prevent them from conflicting with epydoc.  In particular:
          - existing class attributes are prefixed with C{'rst-'}
          - existing names are prefixed with C{'rst-'}
          - hrefs starting with C{'#'} are prefixed with C{'rst-'}
          - hrefs not starting with C{'#'} are given target='_top'
          - all headings (C{<hM{n}>}) are given the css class C{'heading'}
        """
        # Get the list of all attribute dictionaries we need to munge.
        attr_dicts = [attributes]
        if isinstance(node, nodes.Node):
            attr_dicts.append(node.attributes)
        if isinstance(node, dict):
            attr_dicts.append(node)
        # Munge each attribute dictionary.  Unfortunately, we need to
        # iterate through attributes one at a time because some
        # versions of docutils don't case-normalize attributes.
        for attr_dict in attr_dicts:
            for key, val in tuple(attr_dict.items()):
                # Prefix all CSS classes with "rst-"; and prefix all
                # names with "rst-" to avoid conflicts.
                if key.lower() in ('class', 'id', 'name'):
                    if not val.startswith('rst-'):
                        attr_dict[key] = f'rst-{val}'
                elif key.lower() in ('classes', 'ids', 'names'):
                    attr_dict[key] = [f'rst-{cls}' if not cls.startswith('rst-') 
                                      else cls for cls in val]
                elif key.lower() == 'href':
                    if attr_dict[key][:1]=='#':
                        href = attr_dict[key][1:]
                        # We check that the class doesn't alrealy start with "rst-"
                        if not href.startswith('rst-'):
                            attr_dict[key] = f'#rst-{href}'
                    else:
                        # If it's an external link, open it in a new
                        # page.
                        attr_dict['target'] = '_top'

        # For headings, use class="heading"
        if re.match(r'^h\d+$', tagname):
            attributes['class'] = ' '.join([attributes.get('class',''),
                                            'heading']).strip()

        return super().starttag(node, tagname, suffix, **attributes)  # type: ignore[no-any-return]

    def visit_doctest_block(self, node: nodes.Node) -> None:
        pysrc = node[0].astext()
        if node.get('codeblock'):
            self.body.append(flatten(colorize_codeblock(pysrc)))
        else:
            self.body.append(flatten(colorize_doctest(pysrc)))
        raise nodes.SkipNode()


    # Other ressources on how to extend docutils:
    # https://docutils.sourceforge.io/docs/user/tools.html
    # https://docutils.sourceforge.io/docs/dev/hacking.html
    # https://docutils.sourceforge.io/docs/howto/rst-directives.html
    # docutils apidocs:
    # http://code.nabla.net/doc/docutils/api/docutils.html#package-structure

    # this part of the HTMLTranslator is based on sphinx's HTMLTranslator:
    # https://github.com/sphinx-doc/sphinx/blob/3.x/sphinx/writers/html.py#L271
    def _visit_admonition(self, node: nodes.Node, name: str) -> None:
        self.body.append(self.starttag(
            node, 'div', CLASS=('admonition ' + _valid_identifier(name))))
        node.insert(0, nodes.title(name, name.title()))
        self.set_first_last(node)

    def visit_note(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'note')

    def depart_note(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_warning(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'warning')

    def depart_warning(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_attention(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'attention')

    def depart_attention(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_caution(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'caution')

    def depart_caution(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_danger(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'danger')

    def depart_danger(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_error(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'error')

    def depart_error(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_hint(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'hint')

    def depart_hint(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_important(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'important')

    def depart_important(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_tip(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'tip')

    def depart_tip(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_wbr(self, node: nodes.Node) -> None:
        self.body.append('<wbr></wbr>')
    
    def depart_wbr(self, node: nodes.Node) -> None:
        pass

    def visit_seealso(self, node: nodes.Node) -> None:
        self._visit_admonition(node, 'see also')

    def depart_seealso(self, node: nodes.Node) -> None:
        self.depart_admonition(node)

    def visit_versionmodified(self, node: nodes.Node) -> None:
        self.body.append(self.starttag(node, 'div', CLASS=node['type']))

    def depart_versionmodified(self, node: nodes.Node) -> None:
        self.body.append('</div>\n')
