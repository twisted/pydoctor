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
from pydoctor import docspec, visitor
import sys

def _dump_tree(obj: docspec.ApiObject) -> None:
  obj.walk(docspec.PrintVisitor())

def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument('file', nargs='?')
  parser.add_argument('-t', '--tty', action='store_true', help='Read from stdin even if it is a TTY.')
  parser.add_argument('--dump-tree', action='store_true', help='Dump a simplified tree representation of the parsed module(s) to stdout.')
  args = parser.parse_args()

  if not args.file and sys.stdin.isatty() and not args.tty:
    parser.print_usage()
    sys.exit(1)

  system = docspec.load_system(args.file or sys.stdin)

  if args.dump_tree:
    for module in system.rootobjects:
      _dump_tree(module)
  else:
    docspec.dump_system(system, sys.stdout)

if __name__ == '__main__':
  main()
