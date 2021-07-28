# -*- coding: utf8 -*-
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

import argparse
import pydoctor.docspec
import sys

try:
  from termcolor import colored
except ImportError:
  def colored(s, *args, **kwargs):  # type: ignore
    return str(s)

_COLOR_MAP = {
  pydoctor.docspec.Module: 'magenta',
  pydoctor.docspec.Class: 'cyan',
  pydoctor.docspec.Function: 'yellow',
  pydoctor.docspec.Data: 'blue',
}


def _dump_tree(obj: pydoctor.docspec.ApiObject, depth: int = 0) -> None:
  color = _COLOR_MAP.get(type(obj))
  type_name = colored(type(obj).__name__.lower(), color)
  print('| ' * depth + type_name, obj.name)
  for member in getattr(obj, 'members', []):
    _dump_tree(member, depth+1)


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument('file', nargs='?')
  parser.add_argument('-t', '--tty', action='store_true', help='Read from stdin even if it is a TTY.')
  parser.add_argument('-m', '--multiple', action='store_true', help='Load a module per line from the input.')
  parser.add_argument('--dump-tree', action='store_true', help='Dump a simplified tree representation of the parsed module(s) to stdout. Supports colored output if the "termcolor" module is installed.')
  args = parser.parse_args()

  if not args.file and sys.stdin.isatty() and not args.tty:
    parser.print_usage()
    sys.exit(1)

  if args.multiple:
    modules = pydoctor.docspec.load_modules(args.file or sys.stdin)
  else:
    modules = [pydoctor.docspec.load_module(args.file or sys.stdin)]

  if args.dump_tree:
    for module in modules:
      _dump_tree(module)
  else:
    for module in modules:
      pydoctor.docspec.dump_module(module, sys.stdout)


if __name__ == '__main__':
  main()
