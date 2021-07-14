"""
Collection of helper functions related to the creation L{docutils} nodes.
"""
from typing import Iterable, Iterator, Optional

from docutils import nodes

def set_nodes_parent(nodes: Iterable[nodes.Node], parent: nodes.Node) -> Iterator[nodes.Node]:
    """
    Set the parent of the nodes to the defined C{parent} node and return an 
    iterator containing the modified nodes.
    """
    for node in nodes:
        node.parent = parent
        yield node

def set_node_attributes(node: nodes.Node, 
                        document: Optional[nodes.document] = None, 
                        lineno: Optional[int] = None, 
                        children: Optional[Iterable[nodes.Node]] = None) -> nodes.Node:
    """
    Set the attributes to the Node. 
    This is required to manually construct a docutils document that is consistent.
    """
    if lineno is not None:
        node.line = lineno
    
    if document:
        node.document = document

    if children:
        node.extend(set_nodes_parent(children, node))

    return node
