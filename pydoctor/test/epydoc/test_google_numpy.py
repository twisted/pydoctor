from unittest import TestCase
from pydoctor.model import Attribute, System, Function
from pydoctor.epydoc.markup.google import get_parser as get_google_parser
from pydoctor.epydoc.markup.numpy import get_parser as get_numpy_parser


class TestGetParser(TestCase):

    def test_get_google_parser_attribute(self) -> None:

        obj = Attribute(system = System(), name='attr1')

        parse_docstring = get_google_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors = []

        actual = parse_docstring(docstring, errors)._napoleon_processed_docstring
        
        expected = """\
super-dooper attribute

:type: `numpy.ndarray`"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])

    def test_get_google_parser_other(self) -> None:

        obj = Function(system = System(), name='whatever')

        parse_docstring = get_google_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors = []

        actual = parse_docstring(docstring, errors)._napoleon_processed_docstring
        
        expected = """\
numpy.ndarray: super-dooper attribute"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])

    def test_get_numpy_parser_attribute(self) -> None:

        obj = Attribute(system = System(), name='attr1')

        parse_docstring = get_numpy_parser(obj)

        docstring = """\
numpy.ndarray
        super-dooper attribute"""

        errors = []

        actual = parse_docstring(docstring, errors)._napoleon_processed_docstring
        
        expected = """\
super-dooper attribute

:type: `numpy.ndarray`"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])

    def test_get_numpy_parser_other(self) -> None:

        obj = Function(system = System(), name='whatever')

        parse_docstring = get_numpy_parser(obj)

        docstring = """\
numpy.ndarray: super-dooper attribute"""

        errors = []

        actual = parse_docstring(docstring, errors)._napoleon_processed_docstring
        
        expected = """\
numpy.ndarray: super-dooper attribute"""

        self.assertEqual(expected, actual)
        self.assertEqual(errors, [])


class TestWarnings(TestCase):

    def test_warnings(self) -> None:
        
        obj = Function(system = System(), name='func')

        parse_docstring = get_numpy_parser(obj)

        docstring = """
Description of the function. 

Args
----
my attr: hey"
        super-dooper attribute"""

        errors = []

        parse_docstring(docstring, errors)
        
        self.assertEqual(len(errors), 1)

        error = errors.pop()

        self.assertEqual(error.linenum(), 6)
        self.assertIn("malformed string literal (missing opening quote)", error.descr())