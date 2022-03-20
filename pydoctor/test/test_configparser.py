from io import StringIO
from typing import Any, Dict, List
import requests

from pydoctor._configparser import parse_toml_section_name, is_quoted, unquote_str, IniConfigParser, TomlConfigParser

# Test for the unquote_str() function relies on pydoctor's colorizer because it can generate a tripple 
# quoted representation of a string. This has the benefit of testing our colorizer with naughty strings 
# as well. But the tests are de-facto coupled with pydoctor's test suite. 
from pydoctor.test.epydoc.test_pyval_repr import color2

def test_unquote_str() -> None:

    assert unquote_str('string') == 'string'
    assert unquote_str('"string') == '"string'
    assert unquote_str('string"') == 'string"'
    assert unquote_str('"string"') == 'string'
    assert unquote_str('\'string\'') == 'string'
    assert unquote_str('"""string"""') == 'string'
    assert unquote_str('\'\'\'string\'\'\'') == 'string'
    assert unquote_str('"""\nstring"""') == '\nstring'
    assert unquote_str('\'\'\'string\n\'\'\'') == 'string\n'
    assert unquote_str('"""\nstring  \n"""') == '\nstring  \n'
    assert unquote_str('\'\'\'\n  string\n\'\'\'') == '\n  string\n'
    
    assert unquote_str('\'\'\'string') == '\'\'\'string'
    assert unquote_str('string\'\'\'') == 'string\'\'\''
    assert unquote_str('"""string') == '"""string'
    assert unquote_str('string"""') == 'string"""'
    assert unquote_str('"""str"""ing"""') == '"""str"""ing"""'
    assert unquote_str('str\'ing') == 'str\'ing'
    assert unquote_str('""""value""""') == '""""value""""'

def test_unquote_naughty_quoted_strings() -> None:
    # See https://github.com/minimaxir/big-list-of-naughty-strings/blob/master/blns.txt
    res = requests.get('https://raw.githubusercontent.com/minimaxir/big-list-of-naughty-strings/master/blns.txt')
    text = res.text
    for i, string in enumerate(text.split('\n')):
        if string.strip().startswith('#'):
            continue

        # gerenerate two quoted version of the naughty string
        # simply once
        naughty_string_quoted = repr(string) 
        # quoted twice, once with repr, once with our colorizer 
        # (we insert \n such that we force the colorier to produce tripple quoted strings)
        naughty_string_quoted2 = color2(f"\n{string!r}", linelen=0) 
        assert naughty_string_quoted2.startswith("'''")

        naughty_string_quoted2_alt = repr(f"{string!r}") 
        
        # test unquote that repr
        try:
            assert unquote_str(naughty_string_quoted) == string

            assert unquote_str(unquote_str(naughty_string_quoted2).strip()) == string

            assert unquote_str(unquote_str(naughty_string_quoted2_alt)) == string

            if is_quoted(string):
                assert unquote_str(string) == string[1:-1]
            else:
                assert unquote_str(string) == string

        except Exception as e:
            raise AssertionError(f'error with naughty string at line {i}: {e}') from e

def test_parse_toml_section_keys() -> None:
    assert parse_toml_section_name('tool.pydoctor') == ('tool', 'pydoctor')
    assert parse_toml_section_name(' tool.pydoctor ') == ('tool', 'pydoctor')
    assert parse_toml_section_name(' "tool".pydoctor ') == ('tool', 'pydoctor')
    assert parse_toml_section_name(' tool."pydoctor" ') == ('tool', 'pydoctor')

INI_SIMPLE_STRINGS: List[Dict[str, Any]] = [
    {'line': 'key = value # not_a_comment # not_a_comment',   'expected': ('key', 'value # not_a_comment # not_a_comment', None)}, # that's normal behaviour for configparser
    {'line': 'key=value#not_a_comment ',                'expected': ('key', 'value#not_a_comment', None)},
    {'line': 'key=value',                         'expected': ('key', 'value', None)},
    {'line': 'key =value',                        'expected': ('key', 'value', None)},
    {'line': 'key= value',                        'expected': ('key', 'value', None)},
    {'line': 'key = value',                       'expected': ('key', 'value', None)},
    {'line': 'key  =  value',                     'expected': ('key', 'value', None)},
    {'line': ' key  =  value ',                   'expected': ('key', 'value', None)},
    {'line': 'key:value',                         'expected': ('key', 'value', None)},
    {'line': 'key :value',                        'expected': ('key', 'value', None)},
    {'line': 'key: value',                        'expected': ('key', 'value', None)},
    {'line': 'key : value',                       'expected': ('key', 'value', None)},
    {'line': 'key  :  value',                     'expected': ('key', 'value', None)},
    {'line': ' key  :  value ',                   'expected': ('key', 'value', None)},
]

INI_QUOTES_CORNER_CASES: List[Dict[str, Any]] = [
    {'line': 'key="',                             'expected': ('key', '"', None)},
    {'line': 'key  =  "',                         'expected': ('key', '"', None)},
    {'line': ' key  =  " ',                       'expected': ('key', '"', None)},
    {'line': 'key = ""value""',                   'expected': ('key', '""value""', None)}, # Not a valid python, so we get the original value, which is normal
    {'line': 'key = \'\'value\'\'',               'expected': ('key', "''value''", None)}, # Idem
]

INI_QUOTED_STRINGS: List[Dict[str, Any]] = [
    {'line': 'key="value"',                       'expected': ('key', 'value', None)},
    {'line': 'key  =  "value"',                   'expected': ('key', 'value', None)},
    {'line': ' key  =  "value" ',                 'expected': ('key', 'value', None)},
    {'line': 'key=" value "',                     'expected': ('key', ' value ', None)},
    {'line': 'key  =  " value "',                 'expected': ('key', ' value ', None)},
    {'line': ' key  =  " value " ',               'expected': ('key', ' value ', None)},
    {'line': "key='value'",                       'expected': ('key', 'value', None)},
    {'line': "key  =  'value'",                   'expected': ('key', 'value', None)},
    {'line': " key  =  'value' ",                 'expected': ('key', 'value', None)},
    {'line': "key=' value '",                     'expected': ('key', ' value ', None)},
    {'line': "key  =  ' value '",                 'expected': ('key', ' value ', None)},
    {'line': " key  =  ' value ' ",               'expected': ('key', ' value ', None)},
    {'line': 'key = \'"value"\'',                 'expected': ('key', '"value"', None)},
    {'line': 'key = "\'value\'"',                 'expected': ('key', "'value'", None)},
]

INI_LOOKS_LIKE_QUOTED_STRINGS: List[Dict[str, Any]] = [
    {'line': 'key="value',                        'expected': ('key', '"value', None)},
    {'line': 'key  =  "value',                    'expected': ('key', '"value', None)},
    {'line': ' key  =  "value ',                  'expected': ('key', '"value', None)},
    {'line': 'key=value"',                        'expected': ('key', 'value"', None)},
    {'line': 'key  =  value"',                    'expected': ('key', 'value"', None)},
    {'line': ' key  =  value " ',                 'expected': ('key', 'value "', None)},
    {'line': "key='value",                        'expected': ('key', "'value", None)},
    {'line': "key  =  'value",                    'expected': ('key', "'value", None)},
    {'line': " key  =  'value ",                  'expected': ('key', "'value", None)},
    {'line': "key=value'",                        'expected': ('key', "value'", None)},
    {'line': "key  =  value'",                    'expected': ('key', "value'", None)},
    {'line': " key  =  value ' ",                 'expected': ('key', "value '", None)},
]

INI_BLANK_LINES: List[Dict[str, Any]] = [
    {'line': 'key=',                              'expected': ('key', '', None)},
    {'line': 'key =',                             'expected': ('key', '', None)},
    {'line': 'key= ',                             'expected': ('key', '', None)},
    {'line': 'key = ',                            'expected': ('key', '', None)},
    {'line': 'key  =  ',                          'expected': ('key', '', None)},
    {'line': ' key  =   ',                        'expected': ('key', '', None)},
    {'line': 'key:',                              'expected': ('key', '', None)},
    {'line': 'key :',                             'expected': ('key', '', None)},
    {'line': 'key: ',                             'expected': ('key', '', None)},
    {'line': 'key : ',                            'expected': ('key', '', None)},
    {'line': 'key  :  ',                          'expected': ('key', '', None)},
    {'line': ' key  :   ',                        'expected': ('key', '', None)},
]

INI_EQUAL_SIGN_VALUE: List[Dict[str, Any]] = [
    {'line': 'key=:',                             'expected': ('key', ':', None)},
    {'line': 'key =:',                            'expected': ('key', ':', None)},
    {'line': 'key= :',                            'expected': ('key', ':', None)},
    {'line': 'key = :',                           'expected': ('key', ':', None)},
    {'line': 'key  =  :',                         'expected': ('key', ':', None)},
    {'line': ' key  =  : ',                       'expected': ('key', ':', None)},
    {'line': 'key:=',                             'expected': ('key', '=', None)},
    {'line': 'key :=',                            'expected': ('key', '=', None)},
    {'line': 'key: =',                            'expected': ('key', '=', None)},
    {'line': 'key : =',                           'expected': ('key', '=', None)},
    {'line': 'key  :  =',                         'expected': ('key', '=', None)},
    {'line': ' key  :  = ',                       'expected': ('key', '=', None)},
    {'line': 'key==',                             'expected': ('key', '=', None)},
    {'line': 'key ==',                            'expected': ('key', '=', None)},
    {'line': 'key= =',                            'expected': ('key', '=', None)},
    {'line': 'key = =',                           'expected': ('key', '=', None)},
    {'line': 'key  =  =',                         'expected': ('key', '=', None)},
    {'line': ' key  =  = ',                       'expected': ('key', '=', None)},
    {'line': 'key::',                             'expected': ('key', ':', None)},
    {'line': 'key ::',                            'expected': ('key', ':', None)},
    {'line': 'key: :',                            'expected': ('key', ':', None)},
    {'line': 'key : :',                           'expected': ('key', ':', None)},
    {'line': 'key  :  :',                         'expected': ('key', ':', None)},
    {'line': ' key  :  : ',                       'expected': ('key', ':', None)},
]

INI_NEGATIVE_VALUES: List[Dict[str, Any]] = [
    {'line': 'key = -10',                       'expected': ('key', '-10', None)},
    {'line': 'key : -10',                       'expected': ('key', '-10', None)},
    # {'line': 'key -10',                         'expected': ('key', '-10', None)}, # Not supported
    {'line': 'key = "-10"',                     'expected': ('key', '-10', None)},
    {'line': "key  =  '-10'",                   'expected': ('key', '-10', None)},
    {'line': 'key=-10',                         'expected': ('key', '-10', None)},
]

INI_KEY_SYNTAX_EMPTY: List[Dict[str, Any]] = [
    {'line': 'key_underscore=',                   'expected': ('key_underscore', '', None)},
    {'line': '_key_underscore=',                  'expected': ('_key_underscore', '', None)},
    {'line': 'key_underscore_=',                  'expected': ('key_underscore_', '', None)},
    {'line': 'key-dash=',                         'expected': ('key-dash', '', None)},
    {'line': 'key@word=',                         'expected': ('key@word', '', None)},
    {'line': 'key$word=',                         'expected': ('key$word', '', None)},
    {'line': 'key.word=',                         'expected': ('key.word', '', None)},
]

INI_KEY_SYNTAX: List[Dict[str, Any]] = [
    {'line': 'key_underscore = value',            'expected': ('key_underscore', 'value', None)},
    # {'line': 'key_underscore',                    'expected': ('key_underscore', 'true', None)}, # Not supported
    {'line': '_key_underscore = value',           'expected': ('_key_underscore', 'value', None)},
    # {'line': '_key_underscore',                   'expected': ('_key_underscore', 'true', None)}, # Idem
    {'line': 'key_underscore_ = value',           'expected': ('key_underscore_', 'value', None)},
    # {'line': 'key_underscore_',                   'expected': ('key_underscore_', 'true', None)}, Idem
    {'line': 'key-dash = value',                  'expected': ('key-dash', 'value', None)},
    # {'line': 'key-dash',                          'expected': ('key-dash', 'true', None)}, # Idem
    {'line': 'key@word = value',                  'expected': ('key@word', 'value', None)},
    # {'line': 'key@word',                          'expected': ('key@word', 'true', None)}, Idem
    {'line': 'key$word = value',                  'expected': ('key$word', 'value', None)},
    # {'line': 'key$word',                          'expected': ('key$word', 'true', None)}, Idem
    {'line': 'key.word = value',                  'expected': ('key.word', 'value', None)},
    # {'line': 'key.word',                          'expected': ('key.word', 'true', None)}, Idem
]

INI_LITERAL_LIST: List[Dict[str, Any]] = [
    {'line': 'key = [1,2,3]',                       'expected': ('key', ['1','2','3'], None)},
    {'line': 'key = []',                       'expected': ('key', [], None)},
    {'line': 'key = ["hello", "world", ]',                       'expected': ('key', ["hello", "world"], None)},
    {'line': 'key = [\'hello\', \'world\', ]',                       'expected': ('key', ["hello", "world"], None)},
    {'line': 'key =    [1,2,3]      ',                       'expected': ('key', ['1','2','3'], None)},
    {'line': 'key = [\n   ]    \n',                       'expected': ('key', [], None)},
    {'line': 'key = [\n    "hello", "world", ]    \n\n\n\n',                       'expected': ('key', ["hello", "world"], None)},
    {'line': 'key = [\n\n    \'hello\', \n    \'world\', ]',                       'expected': ('key', ["hello", "world"], None)},
    {'line': r'key = "[\"hello\", \"world\", ]"',                     'expected': ('key', "[\"hello\", \"world\", ]", None)},
]

INI_TRIPPLE_QUOTED_STRINGS: List[Dict[str, Any]] = [
    {'line': 'key="""value"""',                       'expected': ('key', 'value', None)},
    {'line': 'key  =  """value"""',                   'expected': ('key', 'value', None)},
    {'line': ' key  =  """value""" ',                 'expected': ('key', 'value', None)},
    {'line': 'key=""" value """',                     'expected': ('key', ' value ', None)},
    {'line': 'key  =  """ value """',                 'expected': ('key', ' value ', None)},
    {'line': ' key  =  """ value """ ',               'expected': ('key', ' value ', None)},
    {'line': "key='''value'''",                       'expected': ('key', 'value', None)},
    {'line': "key  =  '''value'''",                   'expected': ('key', 'value', None)},
    {'line': " key  =  '''value''' ",                 'expected': ('key', 'value', None)},
    {'line': "key=''' value '''",                     'expected': ('key', ' value ', None)},
    {'line': "key  =  ''' value '''",                 'expected': ('key', ' value ', None)},
    {'line': " key  =  ''' value ''' ",               'expected': ('key', ' value ', None)},
    {'line': 'key = \'\'\'"value"\'\'\'',                 'expected': ('key', '"value"', None)},
    {'line': 'key = """\'value\'"""',                 'expected': ('key', "'value'", None)},
    {'line': 'key = """\\"value\\""""',                   'expected': ('key', '"value"', None)}, 
]

# These test does not pass with TOML (even if toml support tripple quoted strings) because indentation 
# is lost while parsing the config with configparser. The bahaviour is basically the same as
# running textwrap.dedent() on the text.
INI_TRIPPLE_QUOTED_STRINGS_NOT_COMPATIABLE_WITH_TOML: List[Dict[str, Any]] = [ 
    {'line': 'key = """"value\\""""',                   'expected': ('key', '"value"', None)}, # This is valid for ast.literal_eval but not for TOML.
    {'line': 'key = """"value" """',                   'expected': ('key', '"value" ', None)}, # Idem.

    {'line': 'key = \'\'\'\'value\\\'\'\'\'',               'expected': ('key', "'value'", None)}, # The rest of the test cases are not passing for TOML,
                                                                                                   # we get the indented string instead, anyway, it's not onus to test TOML.
    {'line': 'key="""\n    value\n    """',                       'expected': ('key', '\nvalue\n', None)},
    {'line': 'key  =  """\n    value\n    """',                   'expected': ('key', '\nvalue\n', None)},
    {'line': ' key  =  """\n    value\n    """ ',                 'expected': ('key', '\nvalue\n', None)},
    {'line': "key='''\n    value\n    '''",                       'expected': ('key', '\nvalue\n', None)},
    {'line': "key  =  '''\n    value\n    '''",                   'expected': ('key', '\nvalue\n', None)},
    {'line': " key  =  '''\n    value\n    ''' ",                 'expected': ('key', '\nvalue\n', None)},
    {'line': 'key= \'\'\'\n    """\n    \'\'\'',                             'expected': ('key', '\n"""\n', None)},
    {'line': 'key  =  \'\'\'\n    """""\n    \'\'\'',                         'expected': ('key', '\n"""""\n', None)},
    {'line': ' key  =  \'\'\'\n    ""\n    \'\'\' ',                        'expected': ('key', '\n""\n', None)},
    {'line': 'key = \'\'\'\n    "value"\n    \'\'\'',                 'expected': ('key', '\n"value"\n', None)},
    {'line': 'key = """\n    \'value\'\n    """',                 'expected': ('key', "\n'value'\n", None)},
    {'line': 'key = """"\n    value\\"\n    """',                   'expected': ('key', '"\nvalue"\n', None)}, 
    {'line': 'key = """\n    \\"value\\"\n    """',                   'expected': ('key', '\n"value"\n', None)}, 
    {'line': 'key = """\n    "value"    \n     """',                   'expected': ('key', '\n"value"\n', None)},  # trailling white spaces are removed by configparser
    {'line': 'key = \'\'\'\n    \'value\\\'\n    \'\'\'',               'expected': ('key', "\n'value'\n", None)}, 

]

INI_LOOKS_LIKE_TRIPPLE_QUOTED_STRINGS: List[Dict[str, Any]] = [
    {'line': 'key= """',                             'expected': ('key', '"""', None)},
    {'line': 'key  =  """""',                         'expected': ('key', '"""""', None)},
    {'line': ' key  =  """" ',                        'expected': ('key', '""""', None)},
    {'line': 'key = """"value""""',                   'expected': ('key', '""""value""""', None)}, # Not a valid python, so we get the original value, which is normal
    {'line': 'key = \'\'\'\'value\'\'\'\'',               'expected': ('key', "''''value''''", None)}, # Idem
    {'line': 'key="""value',                        'expected': ('key', '"""value', None)},
    {'line': 'key  =  """value',                    'expected': ('key', '"""value', None)},
    {'line': ' key  =  """value ',                  'expected': ('key', '"""value', None)},
    {'line': 'key=value"""',                        'expected': ('key', 'value"""', None)},
    {'line': 'key  =  value"""',                    'expected': ('key', 'value"""', None)},
    {'line': ' key  =  value """ ',                 'expected': ('key', 'value """', None)},
    {'line': "key='''value",                        'expected': ('key', "'''value", None)},
    {'line': "key  =  '''value",                    'expected': ('key', "'''value", None)},
    {'line': " key  =  '''value ",                  'expected': ('key', "'''value", None)},
    {'line': "key=value'''",                        'expected': ('key', "value'''", None)},
    {'line': "key  =  value'''",                    'expected': ('key', "value'''", None)},
    {'line': " key  =  value ''' ",                 'expected': ('key', "value '''", None)},
]

INI_BLANK_LINES_QUOTED: List[Dict[str, Any]] = [
    {'line': 'key=""',                              'expected': ('key', '', None)},
    {'line': 'key =""',                             'expected': ('key', '', None)},
    {'line': 'key= ""',                             'expected': ('key', '', None)},
    {'line': 'key = ""',                            'expected': ('key', '', None)},
    {'line': 'key  =  \'\'',                          'expected': ('key', '', None)},
    {'line': ' key  =\'\'   ',                        'expected': ('key', '', None)},
]

INI_BLANK_LINES_QUOTED_COLONS: List[Dict[str, Any]] = [
    {'line': 'key:\'\'',                              'expected': ('key', '', None)},
    {'line': 'key :\'\'',                             'expected': ('key', '', None)},
    {'line': 'key: \'\'',                             'expected': ('key', '', None)},
    {'line': 'key : \'\'',                            'expected': ('key', '', None)},
    {'line': 'key  :\'\'  ',                          'expected': ('key', '', None)},
    {'line': ' key  :  "" ',                        'expected': ('key', '', None)},
]

INI_MULTILINE_STRING_LIST: List[Dict[str, Any]] = [
    {'line': 'key = \n hello\n hoho',                       'expected': ('key', ["hello", "hoho"], None)},
    {'line': 'key = hello\n hoho',                       'expected': ('key', ["hello", "hoho"], None)},
    {'line': 'key : "hello"\n \'hoho\'',                       'expected': ('key', ["\"hello\"", "'hoho'"], None)}, # quotes are kept when converting multine strings to list.
    {'line': 'key : \n hello\n hoho\n',                       'expected': ('key', ["hello", "hoho"], None)},
    {'line': 'key = \n hello\n hoho\n \n\n ',                     'expected': ('key', ["hello", "hoho"], None)},
    {'line': 'key = \n hello\n;comment\n\n hoho\n \n\n ',                     'expected': ('key', ["hello", "hoho"], None)},
]

def get_IniConfigParser_cases() -> List[Dict[str, Any]]:
    return (INI_SIMPLE_STRINGS + 
            INI_QUOTED_STRINGS + 
            INI_BLANK_LINES + 
            INI_NEGATIVE_VALUES + 
            INI_BLANK_LINES_QUOTED + 
            INI_BLANK_LINES_QUOTED_COLONS + 
            INI_KEY_SYNTAX + 
            INI_KEY_SYNTAX_EMPTY + 
            INI_LITERAL_LIST + 
            INI_TRIPPLE_QUOTED_STRINGS + 
            INI_LOOKS_LIKE_TRIPPLE_QUOTED_STRINGS +
            INI_QUOTES_CORNER_CASES + 
            INI_LOOKS_LIKE_QUOTED_STRINGS)

def get_IniConfigParser_multiline_text_to_list_cases() -> List[Dict[str, Any]]:
    cases = get_IniConfigParser_cases()
    for case in INI_BLANK_LINES + INI_KEY_SYNTAX_EMPTY: # when multiline_text_to_list is enabled blank lines are simply ignored.
        cases.remove(case)
    cases.extend(INI_MULTILINE_STRING_LIST)
    return cases

def get_TomlConfigParser_cases() -> List[Dict[str, Any]]:
    return (INI_QUOTED_STRINGS + 
            INI_BLANK_LINES_QUOTED + 
            INI_LITERAL_LIST + 
            INI_TRIPPLE_QUOTED_STRINGS)

def test_IniConfigParser() -> None:
    # Not supported by configparser (currently raises error)
    # {'line': 'key value',                         'expected': ('key', 'value', None)},
    # {'line': 'key  value',                        'expected': ('key', 'value', None)},
    # {'line': ' key    value ',                     'expected': ('key', 'value', None)}
    # {'line': 'key ',                              'expected': ('key', 'true', None)},
    # {'line': 'key',                               'expected': ('key', 'true', None)},
    # {'line': 'key  ',                             'expected': ('key', 'true', None)},
    # {'line': ' key     ',                         'expected': ('key', 'true', None)},
    
    p = IniConfigParser(['soft'], False)

    for test in get_IniConfigParser_cases():
        try:
            parsed_obj = p.parse(StringIO('[soft]\n'+test['line']))
        except Exception as e:
            raise AssertionError("Line %r, error: %s" % (test['line'], str(e))) from e
        else:
            parsed_obj = dict(parsed_obj)
            expected = {test['expected'][0]: test['expected'][1]}
            assert parsed_obj==expected, "Line %r" % (test['line'])


def test_IniConfigParser_multiline_text_to_list() -> None:
    
    p = IniConfigParser(['soft'], True)
    
    for test in get_IniConfigParser_multiline_text_to_list_cases():
        try:
            parsed_obj = p.parse(StringIO('[soft]\n'+test['line']))
        except Exception as e:
            raise AssertionError("Line %r, error: %s" % (test['line'], str(e))) from e
        else:
            parsed_obj = dict(parsed_obj)
            expected = {test['expected'][0]: test['expected'][1]}
            assert parsed_obj==expected, "Line %r" % (test['line'])

def test_TomlConfigParser() -> None:

    p = TomlConfigParser(['soft'])
    
    for test in get_TomlConfigParser_cases():
        try:
            parsed_obj = p.parse(StringIO('[soft]\n'+test['line']))
        except Exception as e:
            raise AssertionError("Line %r, error: %s" % (test['line'], str(e))) from e
        else:
            parsed_obj = dict(parsed_obj)
            expected = {test['expected'][0]: test['expected'][1]}
            assert parsed_obj==expected, "Line %r" % (test['line'])
