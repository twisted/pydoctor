"""
Provides L{configargparse.ConfigFileParser} classes to parse C{TOML} and C{INI} files with **mandatory** support for sections.
Useful to integrate configuration into project files like C{pyproject.toml} or C{setup.cfg}.

L{TomlConfigParser} usage: 

>>> TomlParser = TomlConfigParser(['tool.my_super_tool']) # Simple TOML parser.
>>> parser = ArgumentParser(..., default_config_files=['./pyproject.toml'], config_file_parser_class=TomlParser)

L{IniConfigParser} works exactly the same. 

L{CompositeConfigParser} usage:

>>> TomlParser =  TomlConfigParser(['tool.my_super_tool'])
>>> IniParser = IniConfigParser(['tool:my_super_tool', 'my_super_tool'])
>>> MixedParser = CompositeConfigParser([TomlParser, IniParser]) # This parser supports both TOML and INI formats.
>>> parser = ArgumentParser(..., default_config_files=['./pyproject.toml', 'setup.cfg', 'my_super_tool.ini'], config_file_parser_class=MixedParser)

"""
from collections import OrderedDict
import re
from typing import Any, Dict, List, Optional, Type, Tuple, TextIO
import csv
import functools
import configparser
from ast import literal_eval

from configargparse import ConfigFileParserException, ConfigFileParser
import toml

def partialclass(cls: Type[Any], *args: Any, **kwds: Any) -> Type[Any]:
    """
    Bind a class to be created with some predefined __init__ arguments.
    """
    # mypy gets errors: - Variable "cls" is not valid as a type
    #                   - Invalid base class "cls" 
    class NewCls(cls): #type: ignore
        __init__ = functools.partialmethod(cls.__init__, *args, **kwds) #type: ignore
        __class__ = cls
    assert isinstance(NewCls, type)
    return NewCls

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

def _is_quoted(text:str) -> bool:
    return bool(_QUOTED_STR_REGEX.match(text)) or \
        bool(_TRIPLE_QUOTED_STR_REGEX.match(text))

def unquote_str(text:str) -> str:
    """
    Unquote a maybe quoted string representation. 
    If the string is not detected as being a quoted representation, it returns the same string as passed.
    It supports all kinds of python quotes: C{\"\"\"}, C{'''}, C{"} and C{'}.
    """
    if _is_quoted(text):
        s = literal_eval(text)
        assert isinstance(s, str)
        return s
    return text

def parse_toml_section_name(section_name:str) -> Tuple[str, ...]:
    section = []
    for row in csv.reader([section_name], delimiter='.'):
        for a in row:
            section.append(unquote_str(a.strip()))
    return tuple(section)

def get_toml_section(tomldata:Dict[str, Any], section:Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    itemdata = tomldata.get(section[0])
    if not itemdata:
        return None
    section = section[1:]
    if section:
        return get_toml_section(itemdata, section)
    else:
        assert isinstance(itemdata, dict), f"No section named {'.'.join(repr(section))}. Got field value instead."
        return itemdata

class _TomlConfigParser(ConfigFileParser):

    def __init__(self, sections:List[str]) -> None:
        super().__init__()
        self.sections = sections

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
            data = get_toml_section(config, parse_toml_section_name(section))
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

class _IniConfigParser(ConfigFileParser):
    
    def __init__(self, sections:List[str]) -> None:
        super().__init__()
        self.sections = sections

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
                sv = v.strip()
                # evaluate lists
                if sv.startswith('[') and sv.endswith(']'):
                    try:
                        result[k] = literal_eval(sv)
                    except ValueError:
                        # error evaluating object
                        result[k] = v
                else:
                    # evaluate quoted string
                    try:
                        result[k] = unquote_str(sv)
                    except ValueError:
                        # error evaluating string
                        result[k] = v
        return result

    def get_syntax_description(self) -> str:
        return ("Uses configparser module to parse an INI file which allows multi-line values. "
                "See https://docs.python.org/3/library/configparser.html for details. "
                "This parser includes support for quoting strings literal as well as python list syntax evaluation. ")

class _CompositeConfigParser(ConfigFileParser):
    """
    A config parser that is composed by others L{ConfigFileParser}s.  

    Successively tries to parse the file with each parser, until it succeeds, else raise execption with all encountered errors. 
    """

    def __init__(self, config_parser_types: List[Type[ConfigFileParser]]) -> None:
        super().__init__()
        self.parsers = [p() for p in config_parser_types]

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
        msg = "Uses multiple config parser settings (in order): \n"
        for parser in self.parsers: 
            msg += f"- {parser.__class__.__name__}: {parser.get_syntax_description()} \n"
        return msg

def TomlConfigParser(sections:List[str]) -> Type[ConfigFileParser]:
    """Create a TOML parser class bounded to the list of provided sections."""
    return partialclass(_TomlConfigParser, sections=sections)

def IniConfigParser(sections:List[str]) -> Type[ConfigFileParser]:
    """Create a INI parser class bounded to the list of provided sections."""
    return partialclass(_IniConfigParser, sections=sections)

def CompositeConfigParser(config_parser_types: List[Type[ConfigFileParser]]) -> Type[ConfigFileParser]:
    """
    Create a composite parser: it will successively try to parse the file with each parser, 
    until it succeeds, else raise execption with all encountered errors. 
    """
    return partialclass(_CompositeConfigParser, config_parser_types=config_parser_types)
