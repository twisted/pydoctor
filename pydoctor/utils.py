"""General purpose utility functions."""
from pathlib import Path
import sys
from typing import Type, TypeVar, cast, NoReturn

T = TypeVar('T')

def error(msg: str, *args: object) -> NoReturn:
    if args:
        msg = msg%args
    print(msg, file=sys.stderr)
    sys.exit(1)

def findClassFromDottedName(
        dottedname: str,
        optionname: str,
        base_class: Type[T]
        ) -> Type[T]:
    """
    Looks up a class by full name.
    Watch out, prints a message and SystemExits on error!
    """
    if '.' not in dottedname:
        error("%stakes a dotted name", optionname)
    parts = dottedname.rsplit('.', 1)
    try:
        mod = __import__(parts[0], globals(), locals(), parts[1])
    except ImportError:
        error("could not import module %s", parts[0])
    try:
        cls = getattr(mod, parts[1])
    except AttributeError:
        error("did not find %s in module %s", parts[1], parts[0])
    if not issubclass(cls, base_class):
        error("%s is not a subclass of %s", cls, base_class)
    return cast(Type[T], cls)

def resolve_path(path: str) -> Path:
    """Parse a given path string to a L{Path} object.

    The path is converted to an absolute path, as required by
    L{System.setSourceHref()}.
    The path does not need to exist.
    """

    # We explicitly make the path relative to the current working dir
    # because on Windows resolve() does not produce an absolute path
    # when operating on a non-existing path.
    return Path(Path.cwd(), path).resolve()

def parse_path(value: str, opt: str) -> Path:
    """Parse a str path to a L{Path} object
    using L{resolve_path()}.
    """
    try:
        return resolve_path(value)
    except Exception as ex:
        raise error(f"invalid path: {ex} in option {opt}.")
