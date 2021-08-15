"""
General purpose visitor pattern implementation. 
"""
from typing import Callable, Generic, Iterable, TypeVar

__docformat__ = 'restructuredtext'
T = TypeVar("T")

# Visitor pattern. This is a mix of ast.NodeVisitor and docutils.nodes.NodeVisitor
# https://github.com/python/cpython/blob/main/Lib/ast.py#L386
# https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.17.1//docutils/nodes.py#l1968

class Visitor(Generic[T]):
  """
  "Visitor" pattern abstract superclass implementation for tree traversals.

  Each class has corresponding methods, doing nothing by
  default; override individual methods for specific and useful
  behaviour.  The `visit()` method is called by
  `walk()` upon entering a object.  `walkabout()` also calls
  the `depart()` method before exiting a object.

  The generic methods call "``visit_`` + objet class name" or
  "``depart_`` + objet class name", resp.

  This is a base class for visitors whose ``visit_...`` & ``depart_...``
  methods should be implemented for *all* concrete objets types encountered. 
  """

  def visit(self, ob: T) -> None:
    """Visit an object."""
    method = 'visit_' + ob.__class__.__name__
    visitor = getattr(self, method, self.unknown_visit)
    visitor(ob)
  
  def depart(self, ob: T) -> None:
    """Depart an object."""
    method = 'depart_' + ob.__class__.__name__
    visitor = getattr(self, method, self.unknown_departure)
    visitor(ob)
  
  def unknown_visit(self, ob: T) -> None:
    """
    Called when entering unknown object types.

    Raise an exception unless overridden.
    """
    raise NotImplementedError(
        '%s visiting unknown object type: %s'
        % (self.__class__, ob.__class__.__name__))

  def unknown_departure(self, ob: T) -> None:
    """
    Called before exiting unknown object types.

    Raise exception unless overridden.
    """
    raise NotImplementedError(
        '%s departing unknown object type: %s'
        % (self.__class__, ob.__class__.__name__))

def walk(ob: T, visitor: Visitor[T], get_children: Callable[[T], Iterable[T]]) -> None:
    """
    Traverse a tree of objects, calling the
    `visit()` method of `visitor` when entering each
    node.  (The `walkabout()` method is similar, except it also
    calls the `depart()` method before exiting each objects.)

    This tree traversal supports limited in-place tree
    modifications.  Replacing one node with one or more nodes is
    OK, as is removing an element.  However, if the node removed
    or replaced occurs after the current node, the old node will
    still be traversed, and any new nodes will not.

    :param ob: An object to walk.
    :param visitor: A `Visitor` object, containing a 
        ``visit`` implementation for each object type encountered.
    :param get_children: A callable that returns the children of an object. 
    """
    visitor.visit(ob)
    children = get_children(ob)
    for child in children:
        walk(child, visitor, get_children)

def walkabout(ob: T, visitor: Visitor[T], get_children: Callable[[T], Iterable[T]]) -> None:
    """
    Perform a tree traversal similarly to `walk` (which
    see), except also call the `depart` method before exiting each node.

    :param ob: An object to walk.
    :param visitor: A `Visitor` object, containing a
        ``visit`` and ``depart`` implementation for each concrete object type encountered.
    :param get_children: A callable that returns the children of an object. 
    """
    visitor.visit(ob)
    children = get_children(ob)
    for child in children:
        walkabout(child, visitor, get_children)
    visitor.depart(ob)
