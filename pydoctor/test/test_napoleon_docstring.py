
"""
Forked from the tests for :mod:`sphinx.ext.napoleon.docstring` module.
:copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""
import unittest
from _pytest.outcomes import xfail
import pytest
import re
import warnings
from unittest import TestCase
from textwrap import dedent
from contextlib import contextmanager

from pydoctor.napoleon.docstring import (  GoogleDocstring, NumpyDocstring, 
                                           _convert_numpy_type_spec, _recombine_set_tokens,
                                           _token_type, _tokenize_type_spec )
from pydoctor.napoleon import Config


class BaseDocstringTest(TestCase):
    maxDiff = None
class InlineAttributeTest(BaseDocstringTest):

    def test_class_data_member(self):
        docstring = """\
data member description:
- a: b
"""
        actual = str(GoogleDocstring(docstring, is_attribute=True))
        expected = """\
data member description:
- a: b"""   

        self.assertEqual(expected.rstrip(), actual)

    def test_class_data_member_inline(self):
        docstring = """b: data member description with :ref:`reference`"""
        actual = str(GoogleDocstring(docstring, is_attribute=True))
        expected = ("""\
data member description with :ref:`reference`

:type: b""")
        self.assertEqual(expected.rstrip(), actual)

    def test_class_data_member_inline_no_type(self):
        docstring = """data with ``a : in code`` and :ref:`reference` and no type"""
        actual = str(GoogleDocstring(docstring, is_attribute=True))
        expected = """data with ``a : in code`` and :ref:`reference` and no type"""

        self.assertEqual(expected.rstrip(), actual)

    def test_class_data_member_inline_ref_in_type(self):
        docstring = """:class:`int`: data member description"""
        actual = str(GoogleDocstring(docstring, is_attribute=True))
        expected = ("""\
data member description

:type: :class:`int`""")
        self.assertEqual(expected.rstrip(), actual)


class GoogleDocstringTest(BaseDocstringTest):
    docstrings = [(
        """Single line summary""",
        """Single line summary"""
    ), (
        """
Single line summary
Extended description
""",
"""
Single line summary
Extended description
"""
    ), (
        """
Single line summary
Args:
    arg1(str):Extended
        description of arg1
""",
"""
Single line summary
:param arg1: Extended
             description of arg1
:type arg1: str
"""
    ), (
        """
Single line summary
Args:
    arg1(str):Extended
        description of arg1
    arg2 ( int ) : Extended
        description of arg2
Keyword Args:
    kwarg1(str):Extended
        description of kwarg1
    kwarg2 ( int ) : Extended
        description of kwarg2""",
"""
Single line summary
:param arg1: Extended
             description of arg1
:type arg1: str
:param arg2: Extended
             description of arg2
:type arg2: int

:keyword kwarg1: Extended
                 description of kwarg1
:type kwarg1: str
:keyword kwarg2: Extended
                 description of kwarg2
:type kwarg2: int
"""
    ), (
        """
Single line summary
Arguments:
    arg1(str):Extended
        description of arg1
    arg2 ( int ) : Extended
        description of arg2
Keyword Arguments:
    kwarg1(str):Extended
        description of kwarg1
    kwarg2 ( int ) : Extended
        description of kwarg2""",
"""
Single line summary
:param arg1: Extended
             description of arg1
:type arg1: str
:param arg2: Extended
             description of arg2
:type arg2: int

:keyword kwarg1: Extended
                 description of kwarg1
:type kwarg1: str
:keyword kwarg2: Extended
                 description of kwarg2
:type kwarg2: int
        """
    ), (
        """
Single line summary
Return:
    str:Extended
    description of return value
""",
"""
Single line summary
:returns: Extended
          description of return value
:rtype: str
"""
    ), (
        """
Single line summary
Returns:
    str:Extended
    description of return value
""",
"""
Single line summary
:returns: Extended
          description of return value
:rtype: str
"""
    ), (
        """
Single line summary
Returns:
    Extended
    description of return value
""",
"""
Single line summary
:returns: Extended
          description of return value
"""
    ), (
        """
Single line summary
Args:
    arg1(str):Extended
        description of arg1
    *args: Variable length argument list.
    **kwargs: Arbitrary keyword arguments.
""",
"""
Single line summary
:param arg1: Extended
             description of arg1
:type arg1: str
:param \\*args: Variable length argument list.
:param \\*\\*kwargs: Arbitrary keyword arguments.
"""
    ), (
        """
Single line summary
Args:
    arg1 (list(int)): Description
    arg2 (list[int]): Description
    arg3 (dict(str, int)): Description
    arg4 (dict[str, int]): Description
""",
"""
Single line summary
:param arg1: Description
:type arg1: list(int)
:param arg2: Description
:type arg2: list[int]
:param arg3: Description
:type arg3: dict(str, int)
:param arg4: Description
:type arg4: dict[str, int]
"""
    ), (
        """
Single line summary
Receive:
    arg1 (list(int)): Description
    arg2 (list[int]): Description
""",
"""
Single line summary
:param arg1: Description
:type arg1: list(int)
:param arg2: Description
:type arg2: list[int]
"""
    ), (
        """
Single line summary
Receives:
    arg1 (list(int)): Description
    arg2 (list[int]): Description
""",
"""
Single line summary
:param arg1: Description
:type arg1: list(int)
:param arg2: Description
:type arg2: list[int]
"""
    ), (
        """
Single line summary
Yield:
    str:Extended
    description of yielded value
""",
"""
Single line summary
:Yields: *str* -- Extended
         description of yielded value
"""
    ), (
        """
Single line summary
Yields:
    Extended
    description of yielded value
""",
"""
Single line summary
:Yields: Extended
         description of yielded value
"""
    ), (
        """
Single line summary
Args:
    arg1 (list(int)):
        desc arg1. 
    arg2 (list[int]):
        desc arg2.
""",
"""
Single line summary
:param arg1: desc arg1.
:type arg1: list(int)
:param arg2: desc arg2.
:type arg2: list[int]
"""
    ), ]

    def test_sphinx_admonitions(self):
        admonition_map = {
            'Attention': 'attention',
            'Caution': 'caution',
            'Danger': 'danger',
            'Error': 'error',
            'Hint': 'hint',
            'Important': 'important',
            'Note': 'note',
            'Tip': 'tip',
            'Warning': 'warning',
            'Warnings': 'warning',
        }
        config = Config()
        for section, admonition in admonition_map.items():
            # Multiline
            actual = str(GoogleDocstring(("{}:\n"
                                          "    this is the first line\n"
                                          "\n"
                                          "    and this is the second line\n"
                                          ).format(section), config))
            expect = (".. {}::\n"
                      "\n"
                      "   this is the first line\n"
                      "   \n"
                      "   and this is the second line\n"
                      ).format(admonition)
            self.assertEqual(expect.rstrip(), actual)

            # Single line
            actual = str(GoogleDocstring(("{}:\n"
                                          "    this is a single line\n"
                                          ).format(section), config))
            expect = (".. {}:: this is a single line\n"
                      ).format(admonition)
            self.assertEqual(expect.rstrip(), actual)

    def test_docstrings(self):
        for docstring, expected in self.docstrings:
            actual = str(GoogleDocstring(docstring))
            expected = expected
            self.assertEqual(expected.rstrip(), actual)

    def test_parameters_with_class_reference(self):
        docstring = """\
Construct a new XBlock.
This class should only be used by runtimes.
Arguments:
    runtime (:class:`~typing.Dict`\\[:class:`int`,:class:`str`\\]): Use it to
        access the environment. It is available in XBlock code
        as ``self.runtime``.
    field_data (:class:`FieldData`): Interface used by the XBlock
        fields to access their data from wherever it is persisted.
    scope_ids (:class:`ScopeIds`): Identifiers needed to resolve scopes.
"""

        actual = str(GoogleDocstring(docstring))
        expected = """\
Construct a new XBlock.
This class should only be used by runtimes.
:param runtime: Use it to
                access the environment. It is available in XBlock code
                as ``self.runtime``.
:type runtime: :class:`~typing.Dict`\\[:class:`int`,:class:`str`\\]
:param field_data: Interface used by the XBlock
                   fields to access their data from wherever it is persisted.
:type field_data: :class:`FieldData`
:param scope_ids: Identifiers needed to resolve scopes.
:type scope_ids: :class:`ScopeIds`
"""
        self.assertEqual(expected.rstrip(), actual)

    def test_attributes_with_class_reference(self):
        docstring = """\
Attributes:
    in_attr(:class:`numpy.ndarray`): super-dooper attribute
"""

        actual = str(GoogleDocstring(docstring))
        expected = """\
:ivar in_attr: super-dooper attribute
:type in_attr: :class:`numpy.ndarray`
"""
        self.assertEqual(expected.rstrip(), actual)

        docstring = """\
Attributes:
    in_attr(numpy.ndarray): super-dooper attribute
"""

        actual = str(GoogleDocstring(docstring))
        expected = """\
:ivar in_attr: super-dooper attribute
:type in_attr: numpy.ndarray
"""
        self.assertEqual(expected.rstrip(), actual)

    def test_code_block_in_returns_section(self):
        docstring = """
Returns:
    foobar: foo::
        codecode
        codecode
"""
        expected = """
:returns:
          foo::
              codecode
              codecode
:rtype: foobar
"""
        actual = str(GoogleDocstring(docstring))
        self.assertEqual(expected.rstrip(), actual)

    def test_colon_in_return_type(self):
        docstring = """Example property.
Returns:
    :py:class:`~.module.submodule.SomeClass`: an example instance
    if available, None if not available.
"""
        expected = """Example property.
:returns: an example instance
          if available, None if not available.
:rtype: :py:class:`~.module.submodule.SomeClass`
"""
        actual = str(GoogleDocstring(docstring))
        self.assertEqual(expected.rstrip(), actual)

    def test_xrefs_in_return_type(self):
        docstring = """Example Function
Returns:
    :class:`numpy.ndarray`: A :math:`n \\times 2` array containing
    a bunch of math items
"""
        expected = """Example Function
:returns: A :math:`n \\times 2` array containing
          a bunch of math items
:rtype: :class:`numpy.ndarray`
"""
        actual = str(GoogleDocstring(docstring))
        self.assertEqual(expected.rstrip(), actual)

    def test_raises_types(self):
        docstrings = [("""
Example Function
Raises:
    RuntimeError:
        A setting wasn't specified, or was invalid.
    ValueError:
        Something something value error.
    :py:class:`AttributeError`
        errors for missing attributes.
    ~InvalidDimensionsError
        If the dimensions couldn't be parsed.
    `InvalidArgumentsError`
        If the arguments are invalid.
    :exc:`~ValueError`
        If the arguments are wrong.
""", """
Example Function
:raises RuntimeError: A setting wasn't specified, or was invalid.
:raises ValueError: Something something value error.
:raises AttributeError: errors for missing attributes.
:raises ~InvalidDimensionsError: If the dimensions couldn't be parsed.
:raises InvalidArgumentsError: If the arguments are invalid.
:raises ~ValueError: If the arguments are wrong.
"""),
                      ################################
                      ("""
Example Function
Raises:
    InvalidDimensionsError
""", """
Example Function
:raises InvalidDimensionsError:
"""),
                      ################################
                      ("""
Example Function
Raises:
    Invalid Dimensions Error
""", """
Example Function
:raises Invalid Dimensions Error:
"""),
                      ################################
                      ("""
Example Function
Raises:
    Invalid Dimensions Error: With description
""", """
Example Function
:raises Invalid Dimensions Error: With description
"""),
                      ################################
                      ("""
Example Function
Raises:
    InvalidDimensionsError: If the dimensions couldn't be parsed.
""", """
Example Function
:raises InvalidDimensionsError: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises:
    Invalid Dimensions Error: If the dimensions couldn't be parsed.
""", """
Example Function
:raises Invalid Dimensions Error: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises:
    If the dimensions couldn't be parsed.
""", """
Example Function
:raises If the dimensions couldn't be parsed.:
"""),
                      ################################
                      ("""
Example Function
Raises:
    :class:`exc.InvalidDimensionsError`
""", """
Example Function
:raises exc.InvalidDimensionsError:
"""),
                      ################################
                      ("""
Example Function
Raises:
    :class:`exc.InvalidDimensionsError`: If the dimensions couldn't be parsed.
""", """
Example Function
:raises exc.InvalidDimensionsError: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises:
    :class:`exc.InvalidDimensionsError`: If the dimensions couldn't be parsed,
       then a :class:`exc.InvalidDimensionsError` will be raised.
""", """
Example Function
:raises exc.InvalidDimensionsError: If the dimensions couldn't be parsed,
    then a :class:`exc.InvalidDimensionsError` will be raised.
"""),
                      ################################
                      ("""
Example Function
Raises:
    :class:`exc.InvalidDimensionsError`: If the dimensions couldn't be parsed.
    :class:`exc.InvalidArgumentsError`: If the arguments are invalid.
""", """
Example Function
:raises exc.InvalidDimensionsError: If the dimensions couldn't be parsed.
:raises exc.InvalidArgumentsError: If the arguments are invalid.
"""),
                      ################################
                      ("""
Example Function
Raises:
    :class:`exc.InvalidDimensionsError`
    :class:`exc.InvalidArgumentsError`
""", """
Example Function
:raises exc.InvalidDimensionsError:
:raises exc.InvalidArgumentsError:
""")]
        for docstring, expected in docstrings:
            actual = str(GoogleDocstring(docstring))
            self.assertEqual(expected.rstrip(), actual)

    def test_kwargs_in_arguments(self):
        docstring = """Allows to create attributes binded to this device.
Some other paragraph.
Code sample for usage::
  dev.bind(loopback=Loopback)
  dev.loopback.configure()
Arguments:
  **kwargs: name/class pairs that will create resource-managers
    bound as instance attributes to this instance. See code
    example above.
"""
        expected = """Allows to create attributes binded to this device.
Some other paragraph.
Code sample for usage::
  dev.bind(loopback=Loopback)
  dev.loopback.configure()
:param \\*\\*kwargs: name/class pairs that will create resource-managers
                   bound as instance attributes to this instance. See code
                   example above.
"""
        actual = str(GoogleDocstring(docstring))
        self.assertEqual(expected.rstrip(), actual)

    def test_section_header_formatting(self):
        docstrings = [("""
Summary line
Example:
    Multiline reStructuredText
    literal code block
""", """
Summary line
.. admonition:: Example

   Multiline reStructuredText
   literal code block
"""),
                      ################################
                      ("""
Summary line
Example::
    Multiline reStructuredText
    literal code block
""", """
Summary line
Example::
    Multiline reStructuredText
    literal code block
"""),
                      ################################
                      ("""
Summary line
:Example:
    Multiline reStructuredText
    literal code block
""", """
Summary line
:Example:
    Multiline reStructuredText
    literal code block
""")]
        for docstring, expected in docstrings:
            actual = str(GoogleDocstring(docstring))
            self.assertEqual(expected.rstrip(), actual)

    def test_list_in_parameter_description(self):
        docstring = """One line summary.
Parameters:
    no_list (int):
    one_bullet_empty (int):
        *
    one_bullet_single_line (int):
        - first line
    one_bullet_two_lines (int):
        +   first line
            continued
    two_bullets_single_line (int):
        -  first line
        -  second line
    two_bullets_two_lines (int):
        * first line
          continued
        * second line
          continued
    one_enumeration_single_line (int):
        1.  first line
    one_enumeration_two_lines (int):
        1)   first line
             continued
    two_enumerations_one_line (int):
        (iii) first line
        (iv) second line
    two_enumerations_two_lines (int):
        a. first line
           continued
        b. second line
           continued
    one_definition_one_line (int):
        item 1
            first line
    one_definition_two_lines (int):
        item 1
            first line
            continued
    two_definitions_one_line (int):
        item 1
            first line
        item 2
            second line
    two_definitions_two_lines (int):
        item 1
            first line
            continued
        item 2
            second line
            continued
    one_definition_blank_line (int):
        item 1
            first line
            extra first line
    two_definitions_blank_lines (int):
        item 1
            first line
            extra first line
        item 2
            second line
            extra second line
    definition_after_inline_text (int): text line
        item 1
            first line
    definition_after_normal_text (int):
        text line
        item 1
            first line
"""

        expected = """One line summary.
:param no_list:
:type no_list: int
:param one_bullet_empty:
                         *
:type one_bullet_empty: int
:param one_bullet_single_line:
                               - first line
:type one_bullet_single_line: int
:param one_bullet_two_lines:
                             +   first line
                                 continued
:type one_bullet_two_lines: int
:param two_bullets_single_line:
                                -  first line
                                -  second line
:type two_bullets_single_line: int
:param two_bullets_two_lines:
                              * first line
                                continued
                              * second line
                                continued
:type two_bullets_two_lines: int
:param one_enumeration_single_line:
                                    1.  first line
:type one_enumeration_single_line: int
:param one_enumeration_two_lines:
                                  1)   first line
                                       continued
:type one_enumeration_two_lines: int
:param two_enumerations_one_line:
                                  (iii) first line
                                  (iv) second line
:type two_enumerations_one_line: int
:param two_enumerations_two_lines:
                                   a. first line
                                      continued
                                   b. second line
                                      continued
:type two_enumerations_two_lines: int
:param one_definition_one_line:
                                item 1
                                    first line
:type one_definition_one_line: int
:param one_definition_two_lines:
                                 item 1
                                     first line
                                     continued
:type one_definition_two_lines: int
:param two_definitions_one_line:
                                 item 1
                                     first line
                                 item 2
                                     second line
:type two_definitions_one_line: int
:param two_definitions_two_lines:
                                  item 1
                                      first line
                                      continued
                                  item 2
                                      second line
                                      continued
:type two_definitions_two_lines: int
:param one_definition_blank_line:
                                  item 1
                                      first line
                                      extra first line
:type one_definition_blank_line: int
:param two_definitions_blank_lines:
                                    item 1
                                        first line
                                        extra first line
                                    item 2
                                        second line
                                        extra second line
:type two_definitions_blank_lines: int
:param definition_after_inline_text: text line
                                     item 1
                                         first line
:type definition_after_inline_text: int
:param definition_after_normal_text: text line
                                     item 1
                                         first line
:type definition_after_normal_text: int
"""
        actual = str(GoogleDocstring(docstring))
        self.assertEqual(expected.rstrip(), actual)

    def test_custom_generic_sections(self):

        docstrings = (("""\
Really Important Details:
    You should listen to me!
""", """.. admonition:: Really Important Details

   You should listen to me!
"""),
                      ("""\
Sooper Warning:
    Stop hitting yourself!
""", """.. warning:: Stop hitting yourself!
"""))

        testConfig = Config(napoleon_custom_sections=['Really Important Details',
                                                      ('Sooper Warning', 'warning')])

        for docstring, expected in docstrings:
            actual = str(GoogleDocstring(docstring, testConfig))
            self.assertEqual(expected.rstrip(), actual)

    def test_attr_with_method(self):
        docstring = """
Attributes:
    arg : description

Methods:
    func(i, j): description
"""

        expected = """
:ivar arg: description

.. method:: func(i, j)

   description
"""  # NOQA
        config = Config()
        actual = str(GoogleDocstring(docstring, config=config))
        self.assertEqual(expected.rstrip(), actual)

    def test_return_formatting_indentation(self):

        docstring = """
Returns:
    bool: True if successful, False otherwise.

    The return type is optional and may be specified at the beginning of
    the ``Returns`` section followed by a colon.

    The ``Returns`` section may span multiple lines and paragraphs.
    Following lines should be indented to match the first line.

    The ``Returns`` section supports any reStructuredText formatting,
    including literal blocks::

        {
            'param1': param1,
            'param2': param2
        }
"""

        expected = """
:returns: True if successful, False otherwise.

          The return type is optional and may be specified at the beginning of
          the ``Returns`` section followed by a colon.

          The ``Returns`` section may span multiple lines and paragraphs.
          Following lines should be indented to match the first line.

          The ``Returns`` section supports any reStructuredText formatting,
          including literal blocks::

              {
                  'param1': param1,
                  'param2': param2
              }
:rtype: bool
""" 

        config = Config()
        actual = str(GoogleDocstring(docstring, config=config))
        self.assertEqual(expected.rstrip(), actual)

    def test_column_summary_lines_sphinx_issue_4016(self):
        # test https://github.com/sphinx-doc/sphinx/issues/4016

        docstring = """Get time formated as ``HH:MM:SS``."""

        expected = """Get time formated as ``HH:MM:SS``."""

        actual = str(GoogleDocstring(docstring))
        self.assertEqual(expected.rstrip(), actual)

        actual = str(GoogleDocstring(docstring, is_attribute=True))
        self.assertEqual(expected.rstrip(), actual)

        docstring2 = """Put *key* and *value* into a dictionary.

Returns:
    A dictionary ``{key: value}``
"""
        expected2 = """Put *key* and *value* into a dictionary.

:returns: A dictionary ``{key: value}``
"""

        actual = str(GoogleDocstring(docstring2))
        self.assertEqual(expected2.rstrip(), actual)

        actual = str(GoogleDocstring(docstring2, is_attribute=True))
        self.assertEqual(expected2.rstrip(), actual)

# other issues to watch for - apparently numpy docs imporse a rtype tag, this would a blocking for us
# since type annotation are verty important and they get overriden with a rtype tag
# https://github.com/sphinx-doc/sphinx/issues/5887

# also what out that the warns edits didnot break mupy docs 
# Here is the only real life exemple of warn section that I found
# https://github.com/McSinyx/palace/blob/c5861833ab55f19acffb9db76245dfe9bee439f4/src/palace.pyx#L470

class NumpyDocstringTest(BaseDocstringTest):
    docstrings = [(
        """Single line summary""",
        """Single line summary"""
    ), (
        """
        Single line summary
        Extended description
        """,
        """
        Single line summary
        Extended description
        """
    ), (
        """
        Single line summary
        Parameters
        ----------
        arg1:str
            Extended
            description of arg1
        """,
        """
        Single line summary
        :param arg1: Extended
                     description of arg1
        :type arg1: `str`
        """
    ), (
        """
        Single line summary
        Parameters
        ----------
        arg1:str
            Extended
            description of arg1
        arg2 : int
            Extended
            description of arg2
        Keyword Arguments
        -----------------
          kwarg1:str
              Extended
              description of kwarg1
          kwarg2 : int
              Extended
              description of kwarg2
        """,
        """
        Single line summary
        :param arg1: Extended
                     description of arg1
        :type arg1: `str`
        :param arg2: Extended
                     description of arg2
        :type arg2: `int`

        :keyword kwarg1: Extended
                         description of kwarg1
        :type kwarg1: `str`
        :keyword kwarg2: Extended
                         description of kwarg2
        :type kwarg2: `int`
        """
    ), (
        """
        Single line summary
        Return
        ------
        str
            Extended
            description of return value
        """,
        """
        Single line summary
        :returns: Extended
                  description of return value
        :rtype: `str`
        """
    ),(
        """
        Single line summary
        Return
        ------
        a complicated string
            Extended
            description of return value
        int 
            Extended
            description of return value
        the tuple of your life: tuple
            Extended
            description of return value
        """,
        """
        Single line summary
        :returns: * `a complicated string` -- Extended
                    description of return value
                  * `int` -- Extended
                    description of return value
                  * **the tuple of your life** (`tuple`) -- Extended
                    description of return value
        """
    ),(
        """
        Single line summary
        Return
        ------
        the string of your life
        """,
        """
        Single line summary
        :returns: the string of your life
        """
    ),(
        """
        Single line summary
        Return
        ------
        the string of your life: str
        """,
        """
        Single line summary
        :returns: **the string of your life**
        :rtype: `str`
        """
    ), (
        """
        Single line summary
        Returns
        -------
        str
            Extended
            description of return value
        """,
        """
        Single line summary
        :returns: Extended
                  description of return value
        :rtype: `str`
        """
    ), (
        """
        Single line summary
        Parameters
        ----------
        arg1:str
             Extended description of arg1
        *args:
            Variable length argument list.
        **kwargs:
            Arbitrary keyword arguments.
        """,
        """
        Single line summary
        :param arg1: Extended description of arg1
        :type arg1: `str`
        :param \\*args: Variable length argument list.
        :param \\*\\*kwargs: Arbitrary keyword arguments.
        """
    ), (
        """
        Single line summary
        Parameters
        ----------
        arg1:str
             Extended description of arg1
        *args, **kwargs:
            Variable length argument list and arbitrary keyword arguments.
        """,
        """
        Single line summary
        :param arg1: Extended description of arg1
        :type arg1: `str`
        :param \\*args: Variable length argument list and arbitrary keyword arguments.
        :param \\*\\*kwargs: Variable length argument list and arbitrary keyword arguments.
        """
    ), (
        """
        Single line summary
        Receive
        -------
        arg1:str
            Extended
            description of arg1
        arg2 : int
            Extended
            description of arg2
        """,
        """
        Single line summary
        :param arg1: Extended
                     description of arg1
        :type arg1: `str`
        :param arg2: Extended
                     description of arg2
        :type arg2: `int`
        """
    ), (
        """
        Single line summary
        Receives
        --------
        arg1:str
            Extended
            description of arg1
        arg2 : int
            Extended
            description of arg2
        """,
        """
        Single line summary
        :param arg1: Extended
                     description of arg1
        :type arg1: `str`
        :param arg2: Extended
                     description of arg2
        :type arg2: `int`
        """
    ), (
        """
        Single line summary
        Yield
        -----
        str
            Extended
            description of yielded value
        """,
        """
        Single line summary
        :Yields: `str` -- Extended
                 description of yielded value
        """
    ), (
        """
        Single line summary
        Yields
        ------
        str
            Extended
            description of yielded value
        """,
        """
        Single line summary
        :Yields: `str` -- Extended
                 description of yielded value
        """
    )]

    def test_sphinx_admonitions(self):
        admonition_map = {
            'Attention': 'attention',
            'Caution': 'caution',
            'Danger': 'danger',
            'Error': 'error',
            'Hint': 'hint',
            'Important': 'important',
            'Note': 'note',
            'Tip': 'tip',
            'Warning': 'warning',
            'Warnings': 'warning',
        }
        config = Config()
        for section, admonition in admonition_map.items():
            # Multiline
            actual = str(NumpyDocstring(("{}\n"
                                         "{}\n"
                                         "    this is the first line\n"
                                         "\n"
                                         "    and this is the second line\n"
                                         ).format(section, '-' * len(section)), config))
            expected = (".. {}::\n"
                      "\n"
                      "   this is the first line\n"
                      "   \n"
                      "   and this is the second line\n"
                      ).format(admonition)
            self.assertEqual(expected.rstrip(), actual)

            # Single line
            actual = str(NumpyDocstring(("{}\n"
                                         "{}\n"
                                         "    this is a single line\n"
                                         ).format(section, '-' * len(section)), config))
            expected = (".. {}:: this is a single line\n"
                      ).format(admonition)
            self.assertEqual(expected.rstrip(), actual)

    def test_docstrings(self):
        config = Config()
        for docstring, expected in self.docstrings:
            actual = str(NumpyDocstring(dedent(docstring), config))
            expected = dedent(expected)
            self.assertEqual(expected.rstrip(), actual)

    def test_parameters_with_class_reference(self):
        docstring = """\
Parameters
----------
param1 : :class:`MyClass <name.space.MyClass>` instance
"""

        config = Config()
        actual = str(NumpyDocstring(docstring, config))
        expected = """\
:param param1:
:type param1: :class:`MyClass <name.space.MyClass>` instance
"""
        self.assertEqual(expected.rstrip(), actual)

    def test_multiple_parameters(self):
        docstring = """\
Parameters
----------
x1, x2 : array_like
    Input arrays, description of ``x1``, ``x2``.
"""

        config = Config()
        actual = str(NumpyDocstring(dedent(docstring), config))
        expected = """\
:param x1: Input arrays, description of ``x1``, ``x2``.
:type x1: `array_like`
:param x2: Input arrays, description of ``x1``, ``x2``.
:type x2: `array_like`
"""
        self.assertEqual(expected.rstrip(), actual)

    def test_parameters_without_class_reference(self):
        docstring = """\
Parameters
----------
param1 : MyClass instance
"""

        config = Config()
        actual = str(NumpyDocstring(dedent(docstring), config))
        expected = """\
:param param1:
:type param1: `MyClass instance`
"""
        self.assertEqual(expected.rstrip(), actual)

    def test_see_also_refs(self):
        docstring = """\
numpy.multivariate_normal(mean, cov, shape=None, spam=None)
See Also
--------
some, other, funcs
otherfunc : relationship
"""

        actual = str(NumpyDocstring(docstring))

        expected = """\
numpy.multivariate_normal(mean, cov, shape=None, spam=None)
.. seealso::

   `some`, `other`, `funcs`
   
   `otherfunc`
       relationship
"""
        self.assertEqual(expected.rstrip(), actual)

        docstring = """\
numpy.multivariate_normal(mean, cov, shape=None, spam=None)
See Also
--------
some, other, funcs
otherfunc : relationship
"""

        config = Config()
        actual = str(NumpyDocstring(docstring, config))

        expected = """\
numpy.multivariate_normal(mean, cov, shape=None, spam=None)
.. seealso::

   `some`, `other`, `funcs`
   
   `otherfunc`
       relationship
"""
        self.assertEqual(expected.rstrip(), actual)

        docstring = """\
numpy.multivariate_normal(mean, cov, shape=None, spam=None)
See Also
--------
some, other, :func:`funcs`
otherfunc : relationship
"""
        translations = {
            "other": "MyClass.other",
            "otherfunc": ":anyroleherewillbescraped:`my_package.otherfunc`",
        }
        config = Config(napoleon_type_aliases=translations)

        actual = str(NumpyDocstring(docstring, config))

        expected = """\
numpy.multivariate_normal(mean, cov, shape=None, spam=None)
.. seealso::

   `some`, `MyClass.other`, `funcs`
   
   `my_package.otherfunc`
       relationship
"""
        self.assertEqual(expected.rstrip(), actual)

    def test_colon_in_return_type(self):
        docstring = """
Summary
Returns
-------
:py:class:`~my_mod.my_class`
    an instance of :py:class:`~my_mod.my_class`
"""

        expected = """
Summary
:returns: an instance of :py:class:`~my_mod.my_class`
:rtype: :py:class:`~my_mod.my_class`
"""

        config = Config()

        actual = str(NumpyDocstring(docstring, config))

        self.assertEqual(expected.rstrip(), actual)

    def test_underscore_in_attribute(self):
        docstring = """
Attributes
----------
arg_ : type
    some description
"""

        expected = """
:ivar arg_: some description
:type arg_: `type`
"""

        config = Config()

        actual = str(NumpyDocstring(docstring, config))

        self.assertEqual(expected.rstrip(), actual)

    def test_return_types(self):
        docstring = dedent("""
            Returns
            -------
            df
                a dataframe
        """)
        expected = dedent("""
           :returns: a dataframe
           :rtype: `pandas.DataFrame`
        """)
        translations = {
            "df": "pandas.DataFrame",
        }
        config = Config(
            napoleon_type_aliases=translations,
        )
        actual = str(NumpyDocstring(docstring, config))
        self.assertEqual(expected.rstrip(), actual)

    def test_yield_types(self):
        docstring = dedent("""
            Example Function
            Yields
            ------
            scalar or array-like
                The result of the computation
        """)
        expected = dedent("""
            Example Function
            :Yields: :term:`scalar` or :class:`array-like <numpy.ndarray>` -- The result of the computation
        """)
        translations = {
            "scalar": ":term:`scalar`",
            "array-like": ":class:`array-like <numpy.ndarray>`",
        }
        config = Config(napoleon_type_aliases=translations)

        actual = str(NumpyDocstring(docstring, config))
        self.assertEqual(expected.rstrip(), actual)

    def test_raises_types(self):
        docstrings = [("""
Example Function
Raises
------
  RuntimeError
      A setting wasn't specified, or was invalid.
  ValueError
      Something something value error.
""", """
Example Function
:raises RuntimeError: A setting wasn't specified, or was invalid.
:raises ValueError: Something something value error.
"""),
                      ################################
                      ("""
Example Function
Raises
------
InvalidDimensionsError
""", """
Example Function
:raises InvalidDimensionsError:
"""),
                      ################################
                      ("""
Example Function
Raises
------
Invalid Dimensions Error
""", """
Example Function
:raises Invalid Dimensions Error:
"""),
                      ################################
                      ("""
Example Function
Raises
------
Invalid Dimensions Error
    With description
""", """
Example Function
:raises Invalid Dimensions Error: With description
"""),
                      ################################
                      ("""
Example Function
Raises
------
InvalidDimensionsError
    If the dimensions couldn't be parsed.
""", """
Example Function
:raises InvalidDimensionsError: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises
------
Invalid Dimensions Error
    If the dimensions couldn't be parsed.
""", """
Example Function
:raises Invalid Dimensions Error: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises
------
If the dimensions couldn't be parsed.
""", """
Example Function
:raises If the dimensions couldn't be parsed.:
"""),
                      ################################
                      ("""
Example Function
Raises
------
:class:`exc.InvalidDimensionsError`
""", """
Example Function
:raises exc.InvalidDimensionsError:
"""),
                      ################################
                      ("""
Example Function
Raises
------
:class:`exc.InvalidDimensionsError`
    If the dimensions couldn't be parsed.
""", """
Example Function
:raises exc.InvalidDimensionsError: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises
------
:class:`exc.InvalidDimensionsError`
    If the dimensions couldn't be parsed,
    then a :class:`exc.InvalidDimensionsError` will be raised.
""", """
Example Function
:raises exc.InvalidDimensionsError: If the dimensions couldn't be parsed,
    then a :class:`exc.InvalidDimensionsError` will be raised.
"""),
                      ################################
                      ("""
Example Function
Raises
------
:class:`exc.InvalidDimensionsError`
    If the dimensions couldn't be parsed.
:class:`exc.InvalidArgumentsError`
    If the arguments are invalid.
""", """
Example Function
:raises exc.InvalidDimensionsError: If the dimensions couldn't be parsed.
:raises exc.InvalidArgumentsError: If the arguments are invalid.
"""),
                      ################################
                      ("""
Example Function
Raises
------
CustomError
    If the dimensions couldn't be parsed.
""", """
Example Function
:raises package.CustomError: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises
------
AnotherError
    If the dimensions couldn't be parsed.
""", """
Example Function
:raises ~package.AnotherError: If the dimensions couldn't be parsed.
"""),
                      ################################
                      ("""
Example Function
Raises
------
:class:`exc.InvalidDimensionsError`
:class:`exc.InvalidArgumentsError`
""", """
Example Function
:raises exc.InvalidDimensionsError:
:raises exc.InvalidArgumentsError:
""")]
        for docstring, expected in docstrings:
            translations = {
                "CustomError": "package.CustomError",
                "AnotherError": ":py:exc:`~package.AnotherError`",
            }
            config = Config(napoleon_type_aliases=translations)

            actual = str(NumpyDocstring(docstring, config))
            self.assertEqual(expected.rstrip(), actual)

    def test_xrefs_in_return_type(self):
        docstring = """
Example Function
Returns
-------
:class:`numpy.ndarray`
    A :math:`n \\times 2` array containing
    a bunch of math items
"""
        expected = """
Example Function
:returns: A :math:`n \\times 2` array containing
          a bunch of math items
:rtype: :class:`numpy.ndarray`
"""
        config = Config()

        actual = str(NumpyDocstring(docstring, config))
        self.assertEqual(expected.rstrip(), actual)

    def test_section_header_underline_length(self):
        docstrings = [("""
Summary line
Example
-
Multiline example
body
""", """
Summary line
Example
-
Multiline example
body
"""),
                      ################################
                      ("""
Summary line
Example
--
Multiline example
body
""", """
Summary line
.. admonition:: Example

   Multiline example
   body
"""),
                      ################################
                      ("""
Summary line
Example
-------
Multiline example
body
""", """
Summary line
.. admonition:: Example

   Multiline example
   body
"""),
                      ################################
                      ("""
Summary line
Example
------------
Multiline example
body
""", """
Summary line
.. admonition:: Example

   Multiline example
   body
""")]
        for docstring, expected in docstrings:
            actual = str(NumpyDocstring(docstring))
            self.assertEqual(expected.rstrip(), actual)

    def test_list_in_parameter_description(self):
        docstring = """One line summary.
Parameters
----------
no_list : int
one_bullet_empty : int
    *
one_bullet_single_line : int
    - first line
one_bullet_two_lines : int
    +   first line
        continued
two_bullets_single_line : int
    -  first line
    -  second line
two_bullets_two_lines : int
    * first line
      continued
    * second line
      continued
one_enumeration_single_line : int
    1.  first line
one_enumeration_two_lines : int
    1)   first line
         continued
two_enumerations_one_line : int
    (iii) first line
    (iv) second line
two_enumerations_two_lines : int
    a. first line
       continued
    b. second line
       continued
one_definition_one_line : int
    item 1
        first line
one_definition_two_lines : int
    item 1
        first line
        continued
two_definitions_one_line : int
    item 1
        first line
    item 2
        second line
two_definitions_two_lines : int
    item 1
        first line
        continued
    item 2
        second line
        continued
one_definition_blank_line : int
    item 1
        first line
        extra first line
two_definitions_blank_lines : int
    item 1
        first line
        extra first line
    item 2
        second line
        extra second line
definition_after_normal_text : int
    text line
    item 1
        first line
"""

        expected = """One line summary.
:param no_list:
:type no_list: `int`
:param one_bullet_empty:
                         *
:type one_bullet_empty: `int`
:param one_bullet_single_line:
                               - first line
:type one_bullet_single_line: `int`
:param one_bullet_two_lines:
                             +   first line
                                 continued
:type one_bullet_two_lines: `int`
:param two_bullets_single_line:
                                -  first line
                                -  second line
:type two_bullets_single_line: `int`
:param two_bullets_two_lines:
                              * first line
                                continued
                              * second line
                                continued
:type two_bullets_two_lines: `int`
:param one_enumeration_single_line:
                                    1.  first line
:type one_enumeration_single_line: `int`
:param one_enumeration_two_lines:
                                  1)   first line
                                       continued
:type one_enumeration_two_lines: `int`
:param two_enumerations_one_line:
                                  (iii) first line
                                  (iv) second line
:type two_enumerations_one_line: `int`
:param two_enumerations_two_lines:
                                   a. first line
                                      continued
                                   b. second line
                                      continued
:type two_enumerations_two_lines: `int`
:param one_definition_one_line:
                                item 1
                                    first line
:type one_definition_one_line: `int`
:param one_definition_two_lines:
                                 item 1
                                     first line
                                     continued
:type one_definition_two_lines: `int`
:param two_definitions_one_line:
                                 item 1
                                     first line
                                 item 2
                                     second line
:type two_definitions_one_line: `int`
:param two_definitions_two_lines:
                                  item 1
                                      first line
                                      continued
                                  item 2
                                      second line
                                      continued
:type two_definitions_two_lines: `int`
:param one_definition_blank_line:
                                  item 1
                                      first line
                                      extra first line
:type one_definition_blank_line: `int`
:param two_definitions_blank_lines:
                                    item 1
                                        first line
                                        extra first line
                                    item 2
                                        second line
                                        extra second line
:type two_definitions_blank_lines: `int`
:param definition_after_normal_text: text line
                                     item 1
                                         first line
:type definition_after_normal_text: `int`
"""
        config = Config()
        actual = str(NumpyDocstring(docstring, config))
        self.assertEqual(expected.rstrip(), actual)

    def test_token_type(self):
        tokens = (
            ("1", "literal"),
            ("-4.6", "literal"),
            ("2j", "literal"),
            ("'string'", "literal"),
            ('"another_string"', "literal"),
            ("{1, 2}", "literal"),
            ("{'va{ue', 'set'}", "literal"),
            ("optional", "control"),
            ("default", "control"),
            (", ", "delimiter"),
            (" of ", "delimiter"),
            (" or ", "delimiter"),
            (": ", "delimiter"),
            ("True", "obj"),
            ("None", "obj"),
            ("name", "obj"),
            (":py:class:`Enum`", "reference"),
        )

        for token, expected in tokens:
            actual = _token_type(token)
            self.assertEqual(expected.rstrip(), actual)

    def test_tokenize_type_spec(self):
        specs = (
            "str",
            "defaultdict",
            "int, float, or complex",
            "int or float or None, optional",
            '{"F", "C", "N"}',
            "{'F', 'C', 'N'}, default: 'F'",
            "{'F', 'C', 'N or C'}, default 'F'",
            "str, default: 'F or C'",
            "int, default: None",
            "int, default None",
            "int, default :obj:`None`",
            '"ma{icious"',
            r"'with \'quotes\''",
        )

        tokens = (
            ["str"],
            ["defaultdict"],
            ["int", ", ", "float", ", or ", "complex"],
            ["int", " or ", "float", " or ", "None", ", ", "optional"],
            ["{", '"F"', ", ", '"C"', ", ", '"N"', "}"],
            ["{", "'F'", ", ", "'C'", ", ", "'N'", "}", ", ", "default", ": ", "'F'"],
            ["{", "'F'", ", ", "'C'", ", ", "'N or C'", "}", ", ", "default", " ", "'F'"],
            ["str", ", ", "default", ": ", "'F or C'"],
            ["int", ", ", "default", ": ", "None"],
            ["int", ", ", "default", " ", "None"],
            ["int", ", ", "default", " ", ":obj:`None`"],
            ['"ma{icious"'],
            [r"'with \'quotes\''"],
        )

        for spec, expected in zip(specs, tokens):
            actual = _tokenize_type_spec(spec)
            self.assertEqual(expected, actual)

    def test_recombine_set_tokens(self):
        tokens = (
            ["{", "1", ", ", "2", "}"],
            ["{", '"F"', ", ", '"C"', ", ", '"N"', "}", ", ", "optional"],
            ["{", "'F'", ", ", "'C'", ", ", "'N'", "}", ", ", "default", ": ", "None"],
            ["{", "'F'", ", ", "'C'", ", ", "'N'", "}", ", ", "default", " ", "None"],
        )

        combined_tokens = (
            ["{1, 2}"],
            ['{"F", "C", "N"}', ", ", "optional"],
            ["{'F', 'C', 'N'}", ", ", "default", ": ", "None"],
            ["{'F', 'C', 'N'}", ", ", "default", " ", "None"],
        )

        for tokens_, expected in zip(tokens, combined_tokens):
            actual = _recombine_set_tokens(tokens_)
            self.assertEqual(expected, actual)

    def test_recombine_set_tokens_invalid(self):
        tokens = (
            ["{", "1", ", ", "2"],
            ['"F"', ", ", '"C"', ", ", '"N"', "}", ", ", "optional"],
            ["{", "1", ", ", "2", ", ", "default", ": ", "None"],
        )
        combined_tokens = (
            ["{1, 2"],
            ['"F"', ", ", '"C"', ", ", '"N"', "}", ", ", "optional"],
            ["{1, 2", ", ", "default", ": ", "None"],
        )

        for tokens_, expected in zip(tokens, combined_tokens):
            actual = _recombine_set_tokens(tokens_)
            self.assertEqual(expected, actual)

    def test_convert_numpy_type_spec(self):
        translations = {
            "DataFrame": "pandas.DataFrame",
        }

        specs = (
            "",
            "optional",
            "str, optional",
            "int or float or None, default: None",
            "int, default None",
            '{"F", "C", "N"}',
            "{'F', 'C', 'N'}, default: 'N'",
            "{'F', 'C', 'N'}, default 'N'",
            "DataFrame, optional",
        )

        converted = (
            "",
            "*optional*",
            "`str`, *optional*",
            "`int` or `float` or `None`, *default*: `None`",
            "`int`, *default* `None`",
            '``{"F", "C", "N"}``',
            "``{'F', 'C', 'N'}``, *default*: ``'N'``",
            "``{'F', 'C', 'N'}``, *default* ``'N'``",
            "`pandas.DataFrame`, *optional*",
        )

        for spec, expected in zip(specs, converted):
            actual = _convert_numpy_type_spec(spec, translations=translations)
            self.assertEqual(expected.rstrip(), actual)

    def test_parameter_types(self):
        docstring = dedent("""\
            Parameters
            ----------
            param1 : DataFrame
                the data to work on
            param2 : int or float or None, optional
                a parameter with different types
            param3 : dict-like, optional
                a optional mapping
            param4 : int or float or None, optional
                a optional parameter with different types
            param5 : {"F", "C", "N"}, optional
                a optional parameter with fixed values
            param6 : int, default None
                different default format
            param7 : mapping of hashable to str, optional
                a optional mapping
            param8 : ... or Ellipsis
                ellipsis
        """)
        expected = dedent("""\
            :param param1: the data to work on
            :type param1: `DataFrame`
            :param param2: a parameter with different types
            :type param2: `int` or `float` or `None`, *optional*
            :param param3: a optional mapping
            :type param3: :term:`dict-like <mapping>`, *optional*
            :param param4: a optional parameter with different types
            :type param4: `int` or `float` or `None`, *optional*
            :param param5: a optional parameter with fixed values
            :type param5: ``{"F", "C", "N"}``, *optional*
            :param param6: different default format
            :type param6: `int`, *default* `None`
            :param param7: a optional mapping
            :type param7: :term:`mapping` of :term:`hashable` to `str`, *optional*
            :param param8: ellipsis
            :type param8: `...` or `Ellipsis`
        """)
        translations = {
            "dict-like": ":term:`dict-like <mapping>`",
            "mapping": ":term:`mapping`",
            "hashable": ":term:`hashable`",
        }
        config = Config(
            napoleon_type_aliases=translations,
        )
        actual = str(NumpyDocstring(docstring, config))
        self.assertEqual(expected.rstrip(), actual)

    def test_token_type_invalid(self):
        tokens = (
            "{1, 2",
            "}",
            "'abc",
            "def'",
            '"ghi',
            'jkl"',
        )
        errors = (
            r".+: invalid value set \(missing closing brace\):",
            r".+: invalid value set \(missing opening brace\):",
            r".+: malformed string literal \(missing closing quote\):",
            r".+: malformed string literal \(missing opening quote\):",
            r".+: malformed string literal \(missing closing quote\):",
            r".+: malformed string literal \(missing opening quote\):",
        )
        for token, error in zip(tokens, errors):
            
             with warnings.catch_warnings(record=True) as catch_warnings:
                warnings.simplefilter("always", )
                _token_type(token)
                match_re = re.compile(error)
                assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
                assert match_re.match(str(catch_warnings.pop().message))

                

    
    # name, expected
    escape_kwargs_tests_cases = [("x, y, z", "x, y, z"),
            ("*args, **kwargs", r"\*args, \*\*kwargs"),
            ("*x, **y", r"\*x, \*\*y") ]

    def test_escape_args_and_kwargs(self):
        
        for name, expected in self.escape_kwargs_tests_cases:

            numpy_docstring = NumpyDocstring("")
            actual = numpy_docstring._escape_args_and_kwargs(name)

            assert actual == expected

    docstrings_returns = [(
        """
Single line summary
Return
------
the string of your life: `a complicated string`
the str of your life: {"foo", "bob", "bar"}
the int of your life: int
the tuple of your life: tuple
""",

# FIXME: In the case of natural language type expression 
# It needs to have a followup description to be parsed as tokenized type
# The "workaround" is to use backticks to tell napoleon to consider this string as the type. 
"""
Single line summary
:returns: * **the string of your life** (`a complicated string`)
          * **the str of your life** (``{"foo", "bob", "bar"}``)
          * **the int of your life** (`int`)
          * **the tuple of your life** (`tuple`)
        """
    ),
    
    ("""
Summary line.

Returns
-------
list of strings
    Sequence of arguments, in the order in
    which they should be called.
""",
"""
Summary line.

:returns: Sequence of arguments, in the order in
          which they should be called.
:rtype: `list` of `strings`
        """),
        
        ("""
Summary line.

Returns
-------
Sequence of arguments, in the order in
which they should be called.
""", 
"""
Summary line.

:returns: Sequence of arguments, in the order in
          which they should be called.
        """), 
        ("""
Summary line.

Returns
-------
str
""", 
"""
Summary line.

:rtype: `str`
        """),(
"""
Summary line.

Returns
-------
str
    A URL string
""",
"""
Summary line.

:returns: A URL string
:rtype: `str`
        """
        ), (
        """
Summary line.

Returns
-------
a string, can you believe it?
""",
"""
Summary line.

:returns: a string, can you believe it?
        """
        ), (
        """
Summary line.

Returns
-------
a string, can you believe it?

Raises
--
UserError
        """,
        """
Summary line.

:returns: a string, can you believe it?

:raises UserError: 
        """
        ),(
        """
Summary line.

Returns
-------
str

Raises
--
UserError

Warns
---
RuntimeWarning
        """,
        """
Summary line.

:rtype: `str`

:raises UserError:

:warns: RuntimeWarning
        """
        ),(
        """
Summary line.

Returns
-------
str
    Description of return value

Raises
--
UserError
    Description of raised exception

Warns
--------
RuntimeWarning
    Description of raised warnings
        """,
        """
Summary line.

:returns: Description of return value
:rtype: `str`

:raises UserError: Description of raised exception

:warns RuntimeWarning: Description of raised warnings
        """
        ), (
        """
Summary line.

Returns
-------
list(str)
    The lines of the docstring in a list.
    Note
    ----
    Nested markup works.
        """,
        """
Summary line.

:returns: The lines of the docstring in a list.
          .. note:: Nested markup works.
:rtype: `list(str)`
        """
        ), (
        """
Summary line.

Returns
-------
List[str]
    The lines of the docstring in a list.
    Note
    ----
    Nested markup works.
        """,
        """
Summary line.

:returns: The lines of the docstring in a list.
          .. note:: Nested markup works.
:rtype: `List[str]`
        """
        ), (
        """
Summary line.

Methods
-------
__str__()
    Returns
    -------
    The lines of the docstring in a list.
    Note
    ----
    Nested markup works.
        """,
        """
Summary line.

.. method:: __str__()

   :returns: The lines of the docstring in a list.
   
   .. note:: Nested markup works.
        """
        )] 
    
    # https://github.com/sphinx-contrib/napoleon/issues/12
    # https://github.com/sphinx-doc/sphinx/issues/7077
    def test_return_no_type_sphinx_issue_7077(self):
        
        for docstring, expected in self.docstrings_returns:

            actual = str(NumpyDocstring(docstring, ))
            self.assertEqual(expected.rstrip(), actual)
        
    @pytest.mark.xfail
    def test_return_type_annotation_style(self):
        # FIXME: 
        # the code needs a update to 
        # understand square braquets : [ ]
        docstring = dedent("""
        Summary line.

        Returns
        -------
        List[Union[str, bytes, typing.Pattern]]
        """)

        expected = dedent("""
        Summary line.

        :rtype: `List`[`Union`[`str`, `bytes`, `typing.Pattern`]]
        """)
        actual = str(NumpyDocstring(docstring, ))
        self.assertEqual(expected.rstrip(), actual)