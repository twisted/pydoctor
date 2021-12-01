"""
Collection of helper functions and classes related to the creation L{docutils} nodes.
"""
from typing import Iterable, Iterator, Optional

from docutils import nodes

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
