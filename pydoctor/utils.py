"""General purpose utility functions."""
from pathlib import Path
import sys
import functools
from typing import Any, Type, TypeVar, Tuple, Union, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from pydoctor import model
    from typing_extensions import NoReturn
else:
    NoReturn = None

T = TypeVar('T')

def error(msg: str, *args: object) -> NoReturn:
    if args:
        msg = msg%args
    print(msg, file=sys.stderr)
    sys.exit(1)

def findClassFromDottedName(
        dottedname: str,
        optionname: str,
        base_class: Union[str, Type[T]]
        ) -> Type[T]:
    """
    Looks up a class by full name.
    
    @raises ValueError: If can't find the class.
    """
    if '.' not in dottedname:
        raise ValueError(f"{optionname} takes a dotted name")
    parts = dottedname.rsplit('.', 1)
    try:
        mod = __import__(parts[0], globals(), locals(), parts[1])
    except ImportError:
        raise ValueError(f"could not import module {parts[0]}")
    try:
        cls = getattr(mod, parts[1])
    except AttributeError:
        raise ValueError(f"did not find {parts[1]} in module {parts[0]}")
    if isinstance(base_class, str):
        base_class = findClassFromDottedName(base_class, optionname, object) # type:ignore[arg-type]
    assert isinstance(base_class, type)
    if not issubclass(cls, base_class):
        raise ValueError(f"{cls} is not a subclass of {base_class}")
    return cast(Type[T], cls)

def resolve_path(path: str) -> Path:
    """
    Parse a given path string to a L{Path} object.

    The path is converted to an absolute path, as required by
    L{System.setSourceHref()}.
    The path does not need to exist.

    Watch out, prints a message and SystemExits on error!
    """

    # We explicitly make the path relative to the current working dir
    # because on Windows resolve() does not produce an absolute path
    # when operating on a non-existing path.
    return Path(Path.cwd(), path).resolve()

def parse_path(value: str, opt: str) -> Path:
    """
    Parse a str path to a L{Path} object
    using L{resolve_path()}.

    Watch out, prints a message and SystemExits on error!
    """
    try:
        return resolve_path(value)
    except Exception as ex:
        error(f"{opt}: invalid path, {ex}.")

def parse_privacy_tuple(value:str, opt: str) -> Tuple['model.PrivacyClass', str]:
    """
    Parse string like 'public:match*' to a tuple (PrivacyClass.PUBLIC, 'match*').

    Watch out, prints a message and SystemExits on error!
    """
    parts = value.split(':')
    if len(parts)!=2:
        error(f"{opt}: malformatted value {value!r} should be like '<privacy>:<PATTERN>'.")
    # Late import to avoid cyclic import error
    from pydoctor import model
    try:
        priv = model.PrivacyClass[parts[0].strip().upper()]
    except:
        error(f"{opt}: unknown privacy value {parts[0]!r} should be one of {', '.join(repr(m.name) for m in model.PrivacyClass)}")
    else:
        return (priv, parts[1].strip())

def partialclass(cls: Type[Any], *args: Any, **kwds: Any) -> Type[Any]:
    """
    Bind a class to be created with some predefined __init__ arguments.
    """
    # mypy gets errors: - Variable "cls" is not valid as a type
    #                   - Invalid base class "cls" 
    class NewPartialCls(cls): #type: ignore
        __init__ = functools.partialmethod(cls.__init__, *args, **kwds) #type: ignore
        __class__ = cls
    assert isinstance(NewPartialCls, type)
    return NewPartialCls
