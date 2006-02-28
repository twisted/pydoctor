# this is not stolen from exarkun's sandbox; he didn't seem to write
# any tests :)

from docextractor import ast_pp
from compiler.transformer import parse

# the tests are a little bit fragile -- the result of pp() always ends
# with a new line, string literals have >1 representation, things like
# that.  a better test in some sense would be to make sure that
#
# ast -> pretty printed source -> ast
#
# is the identity but the appearance of the source is actually the
# whole point of the ast_pp module so let's live with the fragility.

def pp_test(source):
    assert ast_pp.pp(parse(source)) == source

def test_name():
    pp_test('a\n')

def test_getattr():
    pp_test('a.b.c\n')

def test_tuple():
    pp_test('()\n')
    pp_test('(1,)\n')
    pp_test('(1, 2)\n')

def test_dict():
    pp_test('{}\n')

def test_literal():
    pp_test("(2, 3.25, '')\n")

def test_call():
    pp_test("range(4)\n")
