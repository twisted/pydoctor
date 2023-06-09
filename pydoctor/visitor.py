"""
General purpose visitor pattern implementation, with extensions.
"""
from collections import defaultdict
import enum
import abc
from itertools import chain
from typing import Dict, Generic, Iterable, List, Optional, Type, TypeVar

T = TypeVar("T")

__docformat__ = 'restructuredtext'

class _BaseVisitor(Generic[T]):
      
  def visit(self, ob: T) -> None:
    """Visit an object."""
    method = 'visit_' + ob.__class__.__name__
    visitor = getattr(self, method, getattr(self, method.lower(), self.unknown_visit))
    visitor(ob)
  
  def depart(self, ob: T) -> None:
    """Depart an object."""
    method = 'depart_' + ob.__class__.__name__
    visitor = getattr(self, method, getattr(self, method.lower(), self.unknown_departure))
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

class Visitor(_BaseVisitor[T], abc.ABC):
  """
  "Visitor" pattern abstract superclass implementation for tree traversals.

  Each class has corresponding methods, doing nothing by
  default; override individual methods for specific and useful
  behaviour.  The `visit()` method is called by
  `walkabout()`  upon entering a object, it also calls
  the `depart()` method before exiting a object.

  The generic methods call "``visit_`` + objet class name" or
  "``depart_`` + objet class name", resp.

  This is a base class for visitors whose ``visit_...`` & ``depart_...``
  methods should be implemented for *all* concrete objets types encountered. 

  This visitor can be composed by other vistitors, see L{VisitorExt}.
  """

  def __init__(self, extensions: Optional['ExtList[T]']=None) -> None:
      self.extensions: 'ExtList[T]' = extensions or ExtList()
      self.extensions.attach_visitor(self)

  @classmethod
  def get_children(cls, ob: T) -> Iterable[T]:
    raise NotImplementedError(f"Method '{cls.__name__}.get_children(ob:T) -> Iterable[T]' must be implemented.")

  class _TreePruningException(Exception):
    """
    Base class for `Visitor`-related tree pruning exceptions.

    Raise subclasses from within ``visit_...`` or ``depart_...`` methods
    called from `Visitor.walkabout()` tree traversals to prune
    the tree traversed.
    """
    skip_extensions = False
  class SkipChildren(_TreePruningException):
    """
    Do not visit any children of the current node.  The current node's
    siblings and ``depart_...`` method are not affected.
    """
  class SkipNode(_TreePruningException):
    """
    Do not visit the current node's children, and do not call the current
    node's ``depart_...`` method.
    """
    def __init__(self, skip_extensions:bool=False) -> None:
       """
       :param skip_extensions: Whether to skip visitor extentions as well.
       """
       super().__init__()
       self.skip_extensions = skip_extensions
    
  def visit(self, ob: T) -> None:
    """Extend the base visit with extensions.

    Parameters:
        node: The node to visit.
    """
    for v in chain(self.extensions.before_visit, self.extensions.outter_visit):
      v.visit(ob)
    
    pruning = None
    try:
      super().visit(ob)
    except self._TreePruningException as ex:
      if ex.skip_extensions:
        # this exception should be raised right away since it means
        # not visiting the extension visitors.
        raise
      pruning = ex

    for v in chain(self.extensions.after_visit, self.extensions.inner_visit):
      v.visit(ob)
    
    if pruning:
      raise pruning
  
  def depart(self, ob: T, call_depart:bool) -> None:
    """Extend the base depart with extensions."""
    
    for v in chain(self.extensions.before_visit, self.extensions.inner_visit):
      v.depart(ob)
    
    if call_depart:
      super().depart(ob)

    for v in chain(self.extensions.after_visit, self.extensions.outter_visit):
      v.depart(ob)

  def walkabout(self, ob: T) -> None:
    """
    Perform a tree traversal, calling `visit()` method when entering a 
    node and the `depart()` method before exiting each node.

    Takes special care to handle  L{_TreePruningException} the following way:

    - If a L{SkipNode} exception is raised inside the main visitor C{visit()} method,
      the C{depart_*} method on the extensions will still be called. 

    :param ob: An object to walk.
    """
    call_depart = True
    try:
      try:
        self.visit(ob)
      except self.SkipNode as e:
        if e.skip_extensions:
          return
        else:
          call_depart = False
      else:
        for child in self.get_children(ob):
          self.walkabout(child)
    except self.SkipChildren:
      pass
    self.depart(ob, call_depart)

# Adapted from https://github.com/pawamoy/griffe
# Copyright (c) 2021, Timothée Mazzucotelli

class PartialVisitor(Visitor[T]):
  """
  Visitor class that do not have to define all possible ``visit_.*`` methods since it overrides
  the default behaviour of `unknown_visit()` and `unknown_departure()` not to raise `NotImplementedError`.
  """
  def unknown_visit(self, ob: T) -> None:
    pass
  def unknown_departure(self, ob: T) -> None:
    pass    

class When(enum.Enum):
    """
    This enumeration contains the different times an extension methods are called.
    """

    BEFORE = enum.auto()
    """
    For each node, call extension methods **before** the method of the customizable visitor.
    """

    AFTER = enum.auto()
    """
    For each node, call extension methods **after** the method of the customizable visitor.
    """

    INNER = enum.auto()
    """
    Same as `AFTER` except that the ``depart()`` method will be called **before** calling ``depart()`` on the customizable visitor.
    """
    
    OUTTER = enum.auto()
    """
    Same as `BEFORE` except that the ``depart()`` method will be called **after** calling ``depart()`` on the customizable visitor.
    """

class ExtList(Generic[T]):
    """
    This class helps iterating on visitor extensions that should run at different times.
    """

    def __init__(self, *extensions: Type['VisitorExt[T]']) -> None:
        """
        Initialize the extensions container.

        :param extensions: The extensions to add.
        """
        self._visitors: Dict[When, List['VisitorExt[T]']] = defaultdict(list)
        self.add(*extensions)

    def add(self, *extensions: Type['VisitorExt[T]']) -> None:
        """
        Add extensions to this container.

        :param extensions: The extensions to add.
        """
        for extension in extensions:
            assert isinstance(extension, type) and issubclass(extension, VisitorExt), f"Visitor extension must be a subclass of 'VisitorExt', got '{extension!r}'"
            assert extension.when != NotImplemented, f'Class variable "when" must be set on visitor extension {type(extension)}'
            self._visitors[extension.when].append(extension())
            
    def attach_visitor(self, parent_visitor: 'Visitor[T]') -> None:
        """
        Attach a parent visitor to the visitor extensions.

        :param parent_visitor: The parent visitor, leading the visit.
        """
        for when in self._visitors.keys():
            for visitor in self._visitors[when]:
                visitor.attach(parent_visitor)

    @property
    def before_visit(self) -> List['VisitorExt[T]']:
        """
        Return the visitors that run before the visit."""
        return self._visitors[When.BEFORE]

    @property
    def after_visit(self) -> List['VisitorExt[T]']:
        """Return the visitors that run after the visit."""
        return self._visitors[When.AFTER]
    
    @property
    def inner_visit(self) -> List['VisitorExt[T]']:
        return self._visitors[When.INNER]
    
    @property
    def outter_visit(self) -> List['VisitorExt[T]']:
        return self._visitors[When.OUTTER]
   
class VisitorExt(_BaseVisitor[T]):
    """
    The node visitor extension base class, to inherit from.

    Subclasses must define the `when` class variable, and any custom ``visit_*`` methods.
  
    All `_TreePruningException` raised in the main `Visitor.visit()` method will be 
    delayed until extensions visitor ``visit()`` and ``depart()`` methods are run as well.

    Meaning:
      - If the main module visitor raises `SkipNode`, the extension visitor set to run ``AFTER`` will still visit this node, but not it's children.
      - If your extension visitor is set to run ``BEFORE`` the main visitor and it raises `SkipNode`, the main visitor will not visit this node.
      - If a `SkipNode` exception is raised inside the main visitor `Visitor.visit()` method,
        the ``depart_*`` method on the extensions will still be called.
    
    See: `When` 
    """
    
    when: When = NotImplemented
    When = When

    def __init__(self) -> None:
        """Initialize the visitor extension."""
        super().__init__()
        self.visitor: Visitor[T] = None  # type: ignore[assignment]
        """The parent visitor"""
    
    def unknown_visit(self, ob: T) -> None:
        pass
    def unknown_departure(self, ob: T) -> None:
        pass    
    
    def attach(self, visitor: Visitor[T]) -> None:
        """Attach the parent visitor to this extension.

        Parameters:
            visitor: The parent visitor.
        """
        self.visitor = visitor
