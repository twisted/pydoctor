from io import StringIO
from typing import Any, Dict, List
import requests

from pydoctor._configparser import parse_toml_section_name, is_quoted, unquote_str, IniConfigParser
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
    {'line': 'key="',                             'expected': ('key', '"', None)},
    {'line': 'key  =  "',                         'expected': ('key', '"', None)},
    {'line': ' key  =  " ',                       'expected': ('key', '"', None)},
    {'line': 'key = \'"value"\'',                 'expected': ('key', '"value"', None)},
    {'line': 'key = "\'value\'"',                 'expected': ('key', "'value'", None)},
    {'line': 'key = ""value""',                   'expected': ('key', '""value""', None)}, # Not a valid python, so we get the original value, which is normal
    {'line': 'key = \'\'value\'\'',               'expected': ('key', "''value''", None)}, # Idem
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
    {'line': 'key : ["hello", "world", ]',                       'expected': ('key', ["hello", "world"], None)},
    {'line': 'key : [\'hello\', \'world\', ]',                       'expected': ('key', ["hello", "world"], None)},
    {'line': r'key = "[\"hello\", \"world\", ]"',                     'expected': ('key', "[\"hello\", \"world\", ]", None)},
]

# TODO: test tripple quotes.

def test_IniConfigParser() -> None:
    # Not supported by configparser (currently raises error)
    # {'line': 'key value',                         'expected': ('key', 'value', None)},
    # {'line': 'key  value',                        'expected': ('key', 'value', None)},
    # {'line': ' key    value ',                    'expected': ('key', 'value', None)}
    # {'line': 'key ',                              'expected': ('key', 'true', None)},
    # {'line': 'key',                               'expected': ('key', 'true', None)},
    # {'line': 'key  ',                             'expected': ('key', 'true', None)},
    # {'line': ' key     ',                         'expected': ('key', 'true', None)},
    
    p = IniConfigParser(['soft'], False)

    config_lines: List[Dict[str, Any]] = INI_SIMPLE_STRINGS + \
            INI_QUOTED_STRINGS + \
            INI_BLANK_LINES + \
            INI_EQUAL_SIGN_VALUE + \
            INI_NEGATIVE_VALUES + INI_BLANK_LINES_QUOTED + \
            INI_KEY_SYNTAX + INI_KEY_SYNTAX_EMPTY + INI_LITERAL_LIST

    for test in config_lines:
        parsed_obj = p.parse(StringIO('[soft]\n'+test['line']))
        parsed_obj = dict(parsed_obj)
        expected = {test['expected'][0]: test['expected'][1]}
        assert parsed_obj==expected, "Line %r" % (test['line'])

INI_BLANK_LINES_QUOTED: List[Dict[str, Any]] = [
    {'line': 'key=""',                              'expected': ('key', '', None)},
    {'line': 'key =""',                             'expected': ('key', '', None)},
    {'line': 'key= ""',                             'expected': ('key', '', None)},
    {'line': 'key = ""',                            'expected': ('key', '', None)},
    {'line': 'key  =  \'\'',                          'expected': ('key', '', None)},
    {'line': ' key  =\'\'   ',                        'expected': ('key', '', None)},
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
    {'line': 'key : "hello"\n \'hoho\'',                       'expected': ('key', ["hello", "hoho"], None)},
    {'line': 'key : \n hello\n hoho\n',                       'expected': ('key', ["hello", "hoho"], None)},
    {'line': 'key = \n hello\n hoho\n \n\n ',                     'expected': ('key', ["hello", "hoho"], None)},
]

def test_IniConfigParser_multiline_text_to_list() -> None:
    
    p = IniConfigParser(['soft'], True)

    config_lines = INI_SIMPLE_STRINGS + \
            INI_QUOTED_STRINGS + \
            INI_EQUAL_SIGN_VALUE + \
            INI_NEGATIVE_VALUES + \
            INI_BLANK_LINES_QUOTED + \
            INI_MULTILINE_STRING_LIST + \
            INI_KEY_SYNTAX + \
            INI_LITERAL_LIST

    for test in config_lines:
        try:
            parsed_obj = p.parse(StringIO('[soft]\n'+test['line']))
        except Exception as e:
            raise AssertionError("Line %r, error: %r" % (test['line'], str(e))) from e
        else:
            parsed_obj = dict(parsed_obj)
            expected = {test['expected'][0]: test['expected'][1]}
            assert parsed_obj==expected, "Line %r" % (test['line'])