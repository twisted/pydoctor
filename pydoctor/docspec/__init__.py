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
  'Decoration',
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

import dataclasses
import enum
import io
import json
import sys
import typing as t
import typing_extensions as te

import databind.core.annotations as A
import databind.json


@dataclasses.dataclass
class Location:
  filename: t.Optional[str]
  lineno: int


@dataclasses.dataclass
class Decoration:
  name: str
  args: t.Optional[str] = None


@dataclasses.dataclass
class Argument:

  class Type(enum.Enum):
    PositionalOnly = 0
    Positional = 1
    PositionalRemainder = 2
    KeywordOnly = 3
    KeywordRemainder = 4

  name: str
  type: Type
  decorations: t.Optional[t.List[Decoration]] = None
  datatype: t.Optional[str] = None
  default_value: t.Optional[str] = None


@dataclasses.dataclass
class ApiObject:
  name: str
  location: t.Optional[Location] = dataclasses.field(repr=False)
  docstring: t.Optional[str] = dataclasses.field(repr=False)


@dataclasses.dataclass
class Data(ApiObject):
  datatype: t.Optional[str] = None
  value: t.Optional[str] = None


@dataclasses.dataclass
class Function(ApiObject):
  modifiers: t.Optional[t.List[str]]
  args: t.List[Argument]
  return_type: t.Optional[str]
  decorations: t.Optional[t.List[Decoration]]


@dataclasses.dataclass
class Class(ApiObject):
  metaclass: t.Optional[str]
  bases: t.Optional[t.List[str]]
  decorations: t.Optional[t.List[Decoration]]
  members: t.List['_MemberType']


_MemberType = te.Annotated[
  t.Union[Data, Function, Class],
  A.unionclass({ 'data': Data, 'function': Function, 'class': Class }, style=A.unionclass.Style.flat)]


@dataclasses.dataclass
class Module(ApiObject):
  members: t.List['_MemberType']


def load_module(
  source: t.Union[str, t.TextIO, t.Dict[str, t.Any]],
  filename: t.Optional[str] = None,
  loader: t.Callable[[t.IO[str]], t.Any] = json.load,
) -> Module:
  """
  Loads a #Module from the specified *source*, which may be either a filename,
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
      return load_module(sys.stdin, source, loader)
    with io.open(source, encoding='utf-8') as fp:
      return load_module(fp, source, loader)
  elif hasattr(source, 'read'):
    # we ar sure the type is "IO" since the source has a read attribute.
    source = loader(source) # type: ignore[arg-type]

  return databind.json.load(source, Module, filename=filename)


def load_modules(
  source: t.Union[str, t.TextIO, t.Iterable[t.Any]],
  filename: t.Optional[str] = None,
  loader: t.Callable[[t.IO[str]], t.Any] = json.load,
) -> t.Iterable[Module]:
  """
  Loads a stream of modules from the specified *source*. Similar to
  #load_module(), the *source* can be a filename, file-like object or a
  list of plain structured data to deserialize from.
  """

  filename = filename or getattr(source, 'name', None)

  if isinstance(source, str):
    with io.open(source, encoding='utf-8') as fp:
      yield from load_modules(fp, source, loader)
    return
  elif hasattr(source, 'read'):
    source = (loader(io.StringIO(line)) for line in t.cast(t.IO[str], source))

  for data in source:
    yield databind.json.load(data, Module, filename=filename)


def dump_module(
  module: Module,
  target: t.Optional[t.Union[str, t.IO[str]]] = None,
  dumper: t.Callable[[t.Any, t.IO[str]], None] = json.dump
) -> t.Optional[t.Dict[str, t.Any]]:
  """
  Dumps a module to the specified target or returns it as plain structured data.
  """

  if isinstance(target, str):
    with io.open(target, 'w', encoding='utf-8') as fp:
      dump_module(module, fp, dumper)
    return None

  data = databind.json.dump(module, Module)
  if target:
    dumper(data, target)
    target.write('\n')
    return None
  else:
    return t.cast(t.Dict[str, t.Any], data)


def filter_visit(
  objects: t.List[ApiObject],
  predicate: t.Callable[[ApiObject], bool],
  order: str = 'pre',
) -> None:
  """
  Visits all *objects* recursively, applying the *predicate* in the specified *order*. If
  the predicate returrns #False, the object will be removed from it's containing list.

  If an object is removed in pre-order, it's members will not be visited.

  :param objects: A list of objects to visit recursively. This list will be modified if
    the *predicate* returns #False for an object.
  :param predicate: The function to apply over all visited objects.
  :param order: The order in which the objects are visited. The default order is `'pre'`
    in which case the *predicate* is called before visiting the object's members. The
    order may also be `'post'`.
  """

  if order not in ('pre', 'post'):
    raise ValueError('invalid order: {!r}'.format(order))

  offset = 0
  for index in range(len(objects)):
    if order == 'pre':
      if not predicate(objects[index - offset]):
        del objects[index - offset]
        offset += 1
        continue
    filter_visit(getattr(objects[index - offset], 'members', []), predicate, order)
    if order == 'post':
      if not predicate(objects[index - offset]):
        del objects[index - offset]
        offset += 1


def visit(
  objects: t.List[ApiObject],
  func: t.Callable[[ApiObject], t.Any],
  order: str = 'pre',
) -> None:
  """
  Visits all *objects*, applying *func* in the specified *order*.
  """

  filter_visit(objects, (lambda obj: func(obj) or True), order)


class ReverseMap:
  """
  Reverse map for finding the parent of an #ApiObject.
  """

  def __init__(self, modules: t.List[Module]) -> None:
    self._modules = modules
    self._reverse_map: t.Dict[int, t.Optional[ApiObject]] = {}
    for module in modules:
      self._init(module, None)

  def _init(self, obj: ApiObject, parent: t.Optional[ApiObject]) -> None:
    self._reverse_map[id(obj)] = parent
    for member in getattr(obj, 'members', []):
      self._init(member, obj)

  def get_parent(self, obj: ApiObject) -> t.Optional[ApiObject]:
    try:
      return self._reverse_map[id(obj)]
    except KeyError:
      raise KeyError(obj)

  def path(self, obj: ApiObject) -> t.List[ApiObject]:
    result = []
    current: t.Optional[ApiObject] = obj
    while current:
      result.append(current)
      current = self.get_parent(current)
    result.reverse()
    return result


def get_member(obj: ApiObject, name: str) -> t.Optional[ApiObject]:
  """
  Generic function to retrieve a member from an API object. This will always return #None for
  objects that don't support members (eg. #Function and #Data).
  """

  for member in getattr(obj, 'members', []):
    if member.name == name:
      assert isinstance(member, ApiObject)
      return member
  return None
