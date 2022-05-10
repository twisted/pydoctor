"""
Collection of helper functions and classes related to the creation and processing of L{docutils} nodes.
"""
from typing import Iterable, Iterator, Optional

from docutils import nodes
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
    Walk up the tree hierarchy until we find an element with a line number.
    """
    # Try fixing https://github.com/twisted/pydoctor/issues/237

    def get_first_parent_lineno(node: Optional[nodes.Node]) -> int:
        if node is None:
            return 0
        # Here we are removing 1 to the result because for some 
        # reason the parent's line seems off by one in many cases.
        return node.line-1 if node.line else get_first_parent_lineno(node.parent) # type:ignore[no-any-return]

    return node.line or get_first_parent_lineno(node.parent)

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
