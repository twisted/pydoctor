# -*- coding: utf8 -*-
# Copyright (c) 2021 Pydoctor contributors
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.1'
__docformat__ = 'restructuredtext'
__all__ = [
  'Location',
  'Argument',
  'ApiObject',
  'Data',
  'Function',
  'Class',
  'Module',
  'load_module',
  'load_modules',
  'dump_module',
  'filter_visit',
  'visit',
  'ReverseMap',
  'get_member',
]


import io
import json
import sys
import dataclasses
import enum
import weakref
import typing as t
import typing_extensions as te

import databind.core.annotations as A
import databind.json

from pydoctor import visitor

@dataclasses.dataclass
class Location:
  filename: t.Optional[str]
  lineno: int

  def __str__(self) -> str:
    return f"{self.filename or ''}:{self.lineno}"

@dataclasses.dataclass
class Argument:

  class Type(enum.Enum):
    POSITIONAL_ONLY = 0
    POSITIONAL_OR_KEYWORD = 1
    VAR_POSITIONAL = 2
    KEYWORD_ONLY = 3
    VAR_KEYWORD = 4

  name: str
  type: Type
  datatype: t.Optional[str] = None
  default_value: t.Optional[str] = None


@dataclasses.dataclass
class ApiObject:
  """
  The base class for representing "API Objects". Any API object is any addressable entity in code,
  be that a variable/constant, function, class or module.
  """
      
  class Kind(enum.Enum):
    """
    Replicate the model.DocumentableKind enum, plus the spcial kind INDIRECTION, 
    which is not a documentable, only there to resolve links correclty.
    """
    PACKAGE             = 1000
    MODULE              = 900
    CLASS               = 800
    INTERFACE           = 850
    CLASS_METHOD        = 700
    STATIC_METHOD       = 600
    METHOD              = 500
    FUNCTION            = 400
    CLASS_VARIABLE      = 300
    SCHEMA_FIELD        = 220
    ATTRIBUTE           = 210
    INSTANCE_VARIABLE   = 200
    PROPERTY            = 150
    VARIABLE            = 100
    INDIRECTION         = -1

  name: str
  location: t.Optional[Location] = dataclasses.field(repr=False)
  docstring: t.Optional[str] = dataclasses.field(repr=False)
  kind: Kind

  def __post_init__(self) -> None:
        self._parent: t.Optional['weakref.ReferenceType[HasMembers]'] = None

  @property
  def parent(self) -> t.Optional['HasMembers']:
    """
    Returns the parent of the #HasMembers. Note that if you make any modifications to the API object tree,
    you will need to call #sync_hierarchy() afterwards because adding to #Class.members or #Module.members
    does not automatically keep the #parent property in sync.
    """

    if self._parent is not None:
      parent = self._parent()
      if parent is None:
        raise RuntimeError(f'lost reference to parent object')
    else:
      parent = None
    return parent

  @parent.setter
  def parent(self, parent: t.Optional['HasMembers']) -> None:
    if parent is not None:
      self._parent = weakref.ref(parent)
    else:
      self._parent = None

  @property
  def path(self) -> t.List['ApiObject']:
    """
    Returns a list of all of this API object's parents, from top to bottom. The list includes *self* as the
    last item.
    """

    result = []
    current: t.Optional[ApiObject] = self
    while current:
      result.append(current)
      current = current.parent
    result.reverse()
    return result
  
  @property
  def full_name(self) -> str:
    return '.'.join(ob.name for ob in self.path)

  def sync_hierarchy(self, parent: t.Optional['HasMembers'] = None) -> None:
    """
    Synchronize the hierarchy of this API object and all of it's children. This should be called when the
    #HasMembers.members are updated to ensure that all child objects reference the right #parent. Loaders
    are expected to return #ApiObject#s in a fully synchronized state such that the user does not have to
    call this method unless they are doing modifications to the tree.
    """

    self.parent = parent
  
  def walk(self, v: visitor.Visitor['ApiObject']) -> None:
    visitor.walk(self, v, get_children=lambda ob: getattr(ob, 'members', ()))
  def walkabout(self, v: visitor.Visitor['ApiObject']) -> None:
    visitor.walkabout(self, v, get_children=lambda ob: getattr(ob, 'members', ()))

@dataclasses.dataclass
class Data(ApiObject):
  datatype: t.Optional[str] = None
  value: t.Optional[str] = None
  kind = ApiObject.Kind.VARIABLE


@dataclasses.dataclass
class Function(ApiObject):
  modifiers: t.Optional[t.List[str]]
  args: t.List[Argument]
  return_type: t.Optional[str]
  decorators: t.Optional[t.List[str]]
  kind = ApiObject.Kind.FUNCTION

class HasMembers(ApiObject):
  """
  Base class for API objects that can have members, e.g. #Class and #Module.
  """

  #: The members of the API object.
  members: t.List[ApiObject]

  def sync_hierarchy(self, parent: t.Optional['HasMembers'] = None) -> None:
    self.parent = parent
    for member in self.members:
      member.sync_hierarchy(self)

@dataclasses.dataclass
class Class(HasMembers):
  bases: t.Optional[t.List[str]]
  decorators: t.Optional[t.List[str]]
  members: t.List['_MemberType'] # type: ignore[assignment]
  kind = ApiObject.Kind.CLASS
  metaclass: t.Optional[str] = None


@dataclasses.dataclass
class Module(HasMembers):
  members: t.List['_ModuleMemberType'] # type: ignore[assignment]
  kind = ApiObject.Kind.MODULE
  all: t.Optional[t.List[str]] = None
  docformat: t.Optional[str] = None


@dataclasses.dataclass
class System:
  projectname: str
  buildtime: str
  options: t.Dict[str, t.Any]
  rootobjects: t.List[Module]
  sourcebase: t.Optional[str]

_MemberType = te.Annotated[
  t.Union[Data, Function, Class],
  A.unionclass({ 'data': Data, 'function': Function, 'class': Class }, style=A.unionclass.Style.flat)]


_ModuleMemberType = te.Annotated[
  t.Union[Data, Function, Class, Module],
  A.unionclass({ 'data': Data, 'function': Function, 'class': Class, 'module': Module }, style=A.unionclass.Style.flat)]


def load_system(
  source: t.Union[str, t.TextIO, t.Dict[str, t.Any]],
  filename: t.Optional[str] = None,
  loader: t.Callable[[t.IO[str]], t.Any] = json.load,
) -> System:
  """
  Loads a #System from the specified *source*, which may be either a filename,
  a file-like object to read from or plain structured data.

  :param source: The JSON source to load the module from.
  :param filename: The name of the source. This will be displayed in error
    messages if the deserialization fails.
  :param loader: A function for loading plain structured data from a file-like
    object. Defaults to #json.load().
  """

  filename = filename or getattr(source, 'name', None)

  if isinstance(source, str):
    if source == '-':
      return load_system(sys.stdin, source, loader)
    with io.open(source, encoding='utf-8') as fp:
      return load_system(fp, source, loader)
  elif hasattr(source, 'read'):
    # we ar sure the type is "IO" since the source has a read attribute.
    source = loader(source) # type: ignore[arg-type]

  system: System = databind.json.load(source, System, filename=filename)
  for module in system.rootobjects:
    module.sync_hierarchy()
  return system

def dump_system(
  system: System,
  target: t.Optional[t.Union[str, t.IO[str]]] = None,
  dumper: t.Callable[[t.Any, t.IO[str]], None] = json.dump
) -> t.Optional[t.Dict[str, t.Any]]:
  """
  Dumps a system to the specified target or returns it as plain structured data.
  """

  if isinstance(target, str):
    with io.open(target, 'w', encoding='utf-8') as fp:
      dump_system(system, fp, dumper)
    return None

  data = databind.json.dump(system, System)
  if target:
    dumper(data, target)
    target.write('\n')
    return None
  else:
    return t.cast(t.Dict[str, t.Any], data)

class FilterVisitor(visitor.Visitor[ApiObject]):
  """
  Visits *objects* applying the *predicate*. 
  
  If the predicate returrns #False, the object will be removed from it's containing list.
  """
  
  def __init__(self, predicate: t.Callable[[ApiObject], bool]):
    self.predicate = predicate

  def unknown_visit(self, ob: ApiObject) -> None:
    self.apply_predicate(ob)
  
  def unknown_departure(self, ob: ApiObject) -> None:
    pass
  
  def apply_predicate(self, ob: ApiObject) -> None:
    if not self.predicate(ob):
      parent = ob.parent
      if parent is None:
        raise RuntimeError(f'cannot remove root module, "{ob.full_name}", from the system.')
      name = ob.name
      assert isinstance(parent, HasMembers)
      assert isinstance(ob, (Data, Function, Class, Module))
      del parent.members[parent.members.index(ob)]
      assert get_member(parent, name) is None

class PrintVisitor(visitor.Visitor[ApiObject]):
      
  def __init__(self, formatstr: str = "{obj_location} - {obj_type} ({obj_kind}): {obj_full_name} {obj_docstring}"):
        self.formatstr = formatstr

  def unknown_visit(self, ob: ApiObject) -> None:
    depth = ob.full_name.count('.')
    tokens = dict(
      obj_type = type(ob).__name__,
      obj_name = ob.name,
      obj_full_name = ob.full_name, 
      obj_docstring = f"(doc: '{ob.docstring}')" if ob.docstring else "",
      obj_kind = ob.kind.name, 
      obj_location = str(ob.location))
    print('| ' * depth + self.formatstr.format(**tokens))
  
  def unknown_departure(self, ob: ApiObject) -> None:
    pass

def get_member(obj: ApiObject, name: str) -> t.Optional[ApiObject]:
  """
  Generic function to retrieve a member from an API object. This will always return #None for
  objects that don't support members (eg. #Function and #Data).
  """

  if isinstance(obj, HasMembers):
    for member in obj.members:
      if member.name == name:
        assert isinstance(member, ApiObject), (name, obj, member)
        return member

  return None
