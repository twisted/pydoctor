from unittest import TestCase
from pydoctor.model import Attribute, System, Function
from pydoctor.epydoc.markup.googlestyle import get_parser

class TestGetParser(TestCase):

    def test_get_parser_attribute(self):

        obj = Attribute(system = System(), name='attr1')

        parse_docstring = get_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors = []

        actual = parse_docstring(docstring, errors)._napoleon_processed_docstring
        
        expected = """\
super-dooper attribute

:type: numpy.ndarray"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])

    def test_get_parser_other(self):

        obj = Function(system = System(), name='whatever')

        parse_docstring = get_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors = []

        actual = parse_docstring(docstring, errors)._napoleon_processed_docstring
        
        expected = """\
numpy.ndarray: super-dooper attribute"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])
