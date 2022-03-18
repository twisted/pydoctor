"""
Provides L{configargparse.ConfigFileParser} classes to parse C{TOML} and C{INI} files with **mandatory** support for sections.
Useful to integrate configuration into project files like C{pyproject.toml} or C{setup.cfg}.

L{TomlConfigParser} usage: 

>>> TomlParser = TomlConfigParser(['tool.my_super_tool']) # Simple TOML parser.
>>> parser = ArgumentParser(..., default_config_files=['./pyproject.toml'], config_file_parser_class=TomlParser)

L{IniConfigParser} works the same way (also it optionaly convert multiline strings to list with argument C{split_ml_text_to_list}).

L{CompositeConfigParser} usage:

>>> MY_CONFIG_SECTIONS = ['tool.my_super_tool', 'tool:my_super_tool', 'my_super_tool']
>>> TomlParser =  TomlConfigParser(MY_CONFIG_SECTIONS)
>>> IniParser = IniConfigParser(MY_CONFIG_SECTIONS, split_ml_text_to_list=True)
>>> MixedParser = CompositeConfigParser([TomlParser, IniParser]) # This parser supports both TOML and INI formats.
>>> parser = ArgumentParser(..., default_config_files=['./pyproject.toml', 'setup.cfg', 'my_super_tool.ini'], config_file_parser_class=MixedParser)

"""
from collections import OrderedDict
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, TextIO, Union
import csv
import functools
import configparser
from ast import literal_eval

from configargparse import ConfigFileParserException, ConfigFileParser
import toml

# I did not invented these regex, just put together some stuff from:
# - https://stackoverflow.com/questions/11859442/how-to-match-string-in-quotes-using-regex
# - and https://stackoverflow.com/a/41005190

_QUOTED_STR_REGEX = re.compile(r'(^\"(?:\\.|[^\"\\])*\"$)|'
                               r'(^\'(?:\\.|[^\'\\])*\'$)')

_TRIPLE_QUOTED_STR_REGEX = re.compile(r'(^\"\"\"(\s+)?(([^\"]|\"([^\"]|\"[^\"]))*(\"\"?)?)?(\s+)?(?:\\.|[^\"\\])?\"\"\"$)|'
                                                                                                 # Unescaped quotes at the end of a string generates 
                                                                                                 # "SyntaxError: EOL while scanning string literal", 
                                                                                                 # so we don't account for those kind of strings as quoted.
                                      r'(^\'\'\'(\s+)?(([^\']|\'([^\']|\'[^\']))*(\'\'?)?)?(\s+)?(?:\\.|[^\'\\])?\'\'\'$)', flags=re.DOTALL)

@functools.lru_cache(maxsize=256, typed=True)
def is_quoted(text:str, triple:bool=True) -> bool:
    """
    Detect whether a string is a quoted representation. 

    @param triple: Also match tripple quoted strings.
    """
    return bool(_QUOTED_STR_REGEX.match(text)) or \
        (triple and bool(_TRIPLE_QUOTED_STR_REGEX.match(text)))

def unquote_str(text:str, triple:bool=True) -> str:
    """
    Unquote a maybe quoted string representation. 
    If the string is not detected as being a quoted representation, it returns the same string as passed.
    It supports all kinds of python quotes: C{\"\"\"}, C{'''}, C{"} and C{'}.

    @param triple: Also unquote tripple quoted strings.
    @raises ValueError: If the string is detected as beeing quoted but literal_eval() fails to evaluate it as string.
        This would be a bug in the regex. 
    """
    if is_quoted(text, triple=triple):
        try:
            s = literal_eval(text)
            assert isinstance(s, str)
        except Exception as e:
            raise ValueError(f"Error trying to unquote the quoted string: {text}: {e}") from e
        return s
    return text

def parse_toml_section_name(section_name:str) -> Tuple[str, ...]:
    """
    Parse a TOML section name to a sequence of strings.

    The following names are all valid: 

    .. python::

        "a.b.c"            # this is best practice -> returns ("a", "b", "c")
        " d.e.f "          # same as [d.e.f] -> returns ("d", "e", "f")
        " g .  h  . i "    # same as [g.h.i] -> returns ("g", "h", "i")
        ' j . "ʞ" . "l" '  # same as [j."ʞ"."l"], double or simple quotes here are supported. -> returns ("j", "ʞ", "l")
    """
    section = []
    for row in csv.reader([section_name], delimiter='.'):
        for a in row:
            section.append(unquote_str(a.strip(), triple=False))
    return tuple(section)

def get_toml_section(data:Dict[str, Any], section:Union[Tuple[str, ...], str]) -> Optional[Dict[str, Any]]:
    """
    Given some TOML data (as loaded with L{toml.load()}), returns the requested section of the data.
    Returns C{None} if the section is not found.
    """
    sections = parse_toml_section_name(section) if isinstance(section, str) else section
    itemdata = data.get(sections[0])
    if not itemdata:
        return None
    sections = sections[1:]
    if sections:
        return get_toml_section(itemdata, sections)
    else:
        if not isinstance(itemdata, dict):
            return None
        return itemdata

class TomlConfigParser(ConfigFileParser):
    """
    Create a TOML parser bounded to the list of provided sections.
    """

    def __init__(self, sections: List[str]) -> None:
        super().__init__()
        self.sections = sections
    
    def __call__(self) -> ConfigFileParser:
        return self

    def parse(self, stream:TextIO) -> Dict[str, Any]:
        """Parses the keys and values from a TOML config file."""
        # parse with configparser to allow multi-line values
        try:
            config = toml.load(stream)
        except Exception as e:
            raise ConfigFileParserException("Couldn't parse TOML file: %s" % e)

        # convert to dict and filter based on section names
        result: Dict[str, Any] = OrderedDict()

        for section in self.sections:
            data = get_toml_section(config, section)
            if data:
                # Seems a little weird, but anything that is not a list is converted to string, 
                # It will be converted back to boolean, int or whatever after.
                # Because config values are still passed to argparser for computation.
                for key, value in data.items():
                    if isinstance(value, list):
                        result[key] = value
                    elif value is None:
                        pass
                    else:
                        result[key] = str(value)
                break
        
        return result

    def get_syntax_description(self) -> str:
        return ("Config file syntax is Tom's Obvious, Minimal Language. "
                "See https://github.com/toml-lang/toml/blob/v0.5.0/README.md for details.")

class IniConfigParser(ConfigFileParser):
    """
    Create a INI parser bounded to the list of provided sections.
    Optionaly convert multiline strings to list.
    """

    def __init__(self, sections:List[str], split_ml_text_to_list:bool) -> None:
        super().__init__()
        self.sections = sections
        self.split_ml_text_to_list = split_ml_text_to_list

    def __call__(self) -> ConfigFileParser:
        return self

    def parse(self, stream:TextIO) -> Dict[str, Any]:
        """Parses the keys and values from an INI config file."""
        # parse with configparser to allow multi-line values
        config = configparser.ConfigParser()
        try:
            config.read_string(stream.read())
        except Exception as e:
            raise ConfigFileParserException("Couldn't parse INI file: %s" % e)

        # convert to dict and filter based on INI section names
        result = OrderedDict()
        for section in config.sections() + [configparser.DEFAULTSECT]:
            if section not in self.sections:
                continue
            for k,v in config[section].items():
                strip_v = v.strip()
                if not strip_v:
                    # ignores empty values, anyway allow_no_value=False by default so this should not happend.
                    continue
                # evaluate lists
                if strip_v.startswith('[') and strip_v.endswith(']'):
                    try:
                        result[k] = literal_eval(strip_v)
                    except ValueError as e:
                        # error evaluating object
                        raise ConfigFileParserException("Error evaluating list: " + str(e) + ". Put quotes around your text if it's meant to be a string.") from e
                else:
                    if is_quoted(strip_v):
                        # evaluate quoted string
                        try:
                            result[k] = unquote_str(strip_v)
                        except ValueError as e:
                            # error unquoting string
                            raise ConfigFileParserException(str(e)) from e
                    # split multi-line text into list of strings if split_ml_text_to_list is enabled.
                    elif self.split_ml_text_to_list and '\n' in v.rstrip('\n'):
                        try:
                            result[k] = [unquote_str(i) for i in strip_v.split('\n') if i]
                        except ValueError as e:
                            # error unquoting string
                            raise ConfigFileParserException(str(e)) from e
                    else:
                        result[k] = v
        return result

    def get_syntax_description(self) -> str:
        msg = ("Uses configparser module to parse an INI file which allows multi-line values. "
                "See https://docs.python.org/3/library/configparser.html for details. "
                "This parser includes support for quoting strings literal as well as python list syntax evaluation. ")
        if self.split_ml_text_to_list:
            msg += ("Alternatively lists can be constructed with a plain multiline string, "
                "each non-empty line will be converted to a list item.")
        return msg

class CompositeConfigParser(ConfigFileParser):
    """
    Createa a config parser composed by others L{ConfigFileParser}s.  

    The composite parser will successively try to parse the file with each parser, 
    until it succeeds, else raise execption with all encountered errors. 
    """

    def __init__(self, config_parser_types: List[Callable[[], ConfigFileParser]]) -> None:
        super().__init__()
        self.parsers = [p() for p in config_parser_types]

    def __call__(self) -> ConfigFileParser:
        return self

    def parse(self, stream:TextIO) -> Dict[str, Any]:
        errors = []
        for p in self.parsers:
            try:
                return p.parse(stream) # type: ignore[no-any-return]
            except Exception as e:
                stream.seek(0)
                errors.append(e)
        raise ConfigFileParserException(
                f"Error parsing config: {', '.join(repr(str(e)) for e in errors)}")
    
    def get_syntax_description(self) -> str:
        def guess_format_name(classname:str) -> str:
            return classname.strip('_').replace('Parser', 
                '').replace('Config', '').replace('File', '').upper()
        
        msg = "Uses multiple config parser settings (in order): \n"
        for i, parser in enumerate(self.parsers): 
            msg += f"[{i+1}] {guess_format_name(parser.__class__.__name__)}: {parser.get_syntax_description()} \n"
        return msg
