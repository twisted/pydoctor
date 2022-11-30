from typing import List
from pydoctor.epydoc.markup import ParseError
from unittest import TestCase
from pydoctor.test import NotFoundLinker
from pydoctor.model import Attribute, System, Function
from pydoctor.stanutils import flatten
from pydoctor.epydoc.markup.google import get_parser as get_google_parser
from pydoctor.epydoc.markup.numpy import get_parser as get_numpy_parser


class TestGetParser(TestCase):

    def test_get_google_parser_attribute(self) -> None:

        obj = Attribute(system = System(), name='attr1')

        parse_docstring = get_google_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors: List[ParseError] = []

        parsed_doc = parse_docstring(docstring, errors)

        actual = flatten(parsed_doc.fields[-1].body().to_stan(NotFoundLinker()))
        
        expected = """<code>numpy.ndarray</code>"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])

    def test_get_google_parser_not_attribute(self) -> None:

        obj = Function(system = System(), name='whatever')

        parse_docstring = get_google_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors: List[ParseError] = []

        assert not parse_docstring(docstring, errors).fields

    # the numpy inline attribute parsing is the same as google-style
    # as shown in the example_numpy.py from Sphinx docs
    def test_get_numpy_parser_attribute(self) -> None:

        obj = Attribute(system = System(), name='attr1')

        parse_docstring = get_numpy_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors: List[ParseError] = []
        
        parsed_doc = parse_docstring(docstring, errors)

        actual = flatten(parsed_doc.fields[-1].body().to_stan(NotFoundLinker()))

        expected = """<code>numpy.ndarray</code>"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])

    def test_get_numpy_parser_not_attribute(self) -> None:

        obj = Function(system = System(), name='whatever')

        parse_docstring = get_numpy_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors: List[ParseError] = []

        assert not parse_docstring(docstring, errors).fields


class TestWarnings(TestCase):

    def test_warnings(self) -> None:
        
        obj = Function(system = System(), name='func')

        parse_docstring = get_numpy_parser(obj)

        docstring = """
Description of the function. 

Some more text.

Some more text.

Some more text.

Some more text.

Args
----
my attr: 'bar or 'foo'
        super-dooper attribute
a valid typed param: List[Union[str, bytes]]
        Description.
other: {hello
        Choices.

Returns
-------
'spam' or 'baz, optional
        A string.

Note
----
Some more text.
"""

        errors: List[ParseError] = []

        parse_docstring(docstring, errors)
        
        self.assertEqual(len(errors), 3)
        
        self.assertIn("malformed string literal (missing closing quote)", errors[2].descr())
        self.assertIn("invalid value set (missing closing brace)", errors[1].descr())
        self.assertIn("malformed string literal (missing opening quote)", errors[0].descr())
        
        self.assertEqual(errors[2].linenum(), 21) # #FIXME: It should be 23 actually...
        self.assertEqual(errors[1].linenum(), 18)
        self.assertEqual(errors[0].linenum(), 14)

        
