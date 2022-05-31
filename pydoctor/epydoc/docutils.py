"""
Collection of helper functions and classes related to the creation and processing of L{docutils} nodes.
"""
from typing import Iterable, Iterator, Optional, Tuple

from docutils import nodes
import docutils
from docutils.transforms import parts

__docformat__ = 'epytext en'

def _set_nodes_parent(nodes: Iterable[nodes.Node], parent: nodes.Element) -> Iterator[nodes.Node]:
    """
    Set the L{nodes.Node.parent} attribute of the C{nodes} to the defined C{parent}. 
    
    @returns: An iterator containing the modified nodes.
    """
    for node in nodes:
        node.parent = parent
        yield node

def set_node_attributes(node: nodes.Node, 
                        document: Optional[nodes.document] = None, 
                        lineno: Optional[int] = None, 
                        children: Optional[Iterable[nodes.Node]] = None) -> nodes.Node:
    """
    Set the attributes of a Node and return the modified node.
    This is required to manually construct a docutils document that is consistent.

    @param node: A node to edit.
    @param document: The L{nodes.Node.document} attribute.
    @param lineno: The L{nodes.Node.line} attribute.
    @param children: The L{nodes.Element.children} attribute. Special care is taken 
        to appropriately set the L{nodes.Node.parent} attribute on the child nodes. 
    """
    if lineno is not None:
        node.line = lineno
    
    if document:
        node.document = document

    if children:
        assert isinstance(node, nodes.Element), (f'Cannot set the children on Text node: "{node.astext()}". '
                                                 f'Children: {children}')
        node.extend(_set_nodes_parent(children, node))

    return node

def build_table_of_content(node: nodes.Node, depth: int, level: int = 0) -> Optional[nodes.Node]:
    """
    Simplified from docutils Contents transform. 

    All section nodes MUST have set attribute 'ids' to a list of strings.
    """

    def _copy_and_filter(node: nodes.Node) -> nodes.Node:
        """Return a copy of a title, with references, images, etc. removed."""
        visitor = parts.ContentsFilter(node.document)
        node.walkabout(visitor)
        return visitor.get_entry_text()

    level += 1
    sections = [sect for sect in node if isinstance(sect, nodes.section)]
    entries = []
    for section in sections:
        title = section[0]
        entrytext = _copy_and_filter(title)
        reference = nodes.reference('', '', refid=section['ids'][0],
                                    *entrytext)
        ref_id = node.document.set_id(reference,
                                    suggested_prefix='toc-entry')
        entry = nodes.paragraph('', '', reference)
        item = nodes.list_item('', entry)
        if title.next_node(nodes.reference) is None:
            title['refid'] = ref_id
        if level < depth:
            subsects = build_table_of_content(section, depth=depth, level=level)
            item += subsects or []
        entries.append(item)
    if entries:
        contents = nodes.bullet_list('', *entries)
        return contents
    else:
        return None

def get_lineno(node: nodes.Node) -> int:
    """
    Get the 0-based line number for a docutils `nodes.title_reference`.

    Walk up the tree hierarchy until we find an element with a line number, then
    counts the number of newlines until the reference element is found.
    """
    # Fixes https://github.com/twisted/pydoctor/issues/237
        
    def get_first_parent_lineno(_node: Optional[nodes.Node]) -> int:
        if _node is None:
            return 0
        
        if _node.line:
            # This line points to the start of the containing node
            # Here we are removing 1 to the result because ParseError class is zero-based
            # while docutils line attribute is 1-based.
            line:int = _node.line-1
            # Let's figure out how many newlines we need to add to this number 
            # to get the right line number.
            parent_rawsource: Optional[str] = _node.rawsource or None
            node_rawsource: Optional[str] = node.rawsource or None

            if parent_rawsource is not None and \
               node_rawsource is not None:
                if node_rawsource in parent_rawsource:
                    node_index = parent_rawsource.index(node_rawsource)
                    # Add the required number of newlines to the result
                    line += parent_rawsource[:node_index].count('\n')
        else:
            line = get_first_parent_lineno(_node.parent)
        return line

    if node.line:
        line = node.line
    else:
        line = get_first_parent_lineno(node.parent)
    
    return line # type:ignore[no-any-return]

class wbr(nodes.inline):
    """
    Word break opportunity.
    """
    def __init__(self) -> None:
        super().__init__('', '')

class obj_reference(nodes.title_reference):
    """
    A reference to a documentable object.
    """

def _get_docutils_version() -> Tuple[int, int,int]:
    """
    Returns tuple (major, minor, micro).
    
    Pre-release info is ignored (replaced by zero).
    """
    def int_or_zero(s:str) -> int:
        try:
            return int(s)
        except ValueError:
            return  0
    
    version = [int_or_zero(p) for p in docutils.__version__.split('.')[:3]]
    if len(version)==2:
        version += [0]
    
    assert len(version)==3, version
    return tuple(version)
