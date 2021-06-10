"""
Collection of helper functions and classes related to the creation L{docutils} nodes.
"""
from typing import Iterable, Iterator, Optional, List

from docutils import nodes

def set_nodes_parent(nodes: Iterable[nodes.Node], parent: nodes.Node) -> Iterator[None]:
    """
    Set the parent of the nodes to the defined C{parent} node and return an 
    iterator containing the modified nodes.
    """
    for node in nodes:
        node.parent = parent
        yield node

def set_node_attributes(node: nodes.Node, 
                        document: nodes.document, 
                        lineno: Optional[int] = None, 
                        children: Optional[List[nodes.Node]] = None) -> nodes.Node:
    """
    Set the attributes to the Node. 
    This is required to manually construct a docutils document that is consistent.
    """
    if lineno is not None:
        node.line = lineno

    node.document = document

    if children:
        node.extend(set_nodes_parent(children, node))

    return node

class wbr(nodes.inline):
    """
    Word break opportunity.
    """
    def __init__(self) -> None:
        super().__init__('', '')

class newline(nodes.inline):
    """
    Newline in HTML output.
    """
    def __init__(self) -> None:
        super().__init__('', '')
