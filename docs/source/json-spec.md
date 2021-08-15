# JSON object specification

Dump and load packages to JSON with options ``--dumpjson <file>`` and ``--loadjson <file>``. 

__Table of Contents__

* [Location](#location)
* [Module](#module)
* [Class](#class)
* [Data](#data)
* [Function](#function)
* [Argument](#drgument)
* [Decoration](#decoration)

## Object Types

### System

The system containing the root modules. 

_Fields_

* `projectname` (str)
* `buildtime` (str)
* `options` (Dict[str, Any])
* `rootobjects` (List[Module])
* `sourcebase` (Optional[str])

### Location

The location object describes where the an API object was extracted from a
file. Usually this points to the source file and a line number. The filename
should always be relative to the root of a project or source control repository.

_Fields_

* `filename` (str) &ndash; A relative filename.
* `lineno` (int): &ndash; The line number from which the API object was parsed.

### Module

A module represents a collection of data, function and classes. In the Python
language, it represents a module or package. 

_Fields_

* `kind` (ApiObject.Kind) &ndash; "MODULE" or "PACKAGE"
* `name` (str) &ndash; The full name of the module.
* `location` (Location)
* `docstring` (Optional[str]) &ndash; The docstring for the module as parsed
  from the source.
* `all` (Optional[List[str]]): Value of the `__all__` module variable.
* `docformat` (Optional[str]): Value of the `__docformat__` module variable.
* `members` (array) &ndash; An array of `Data`, `Function`` or `Class` objects.

### Class

Represents a class definition.

_Fields_

* `type` (str) &ndash; Value is `class`
* `kind` (ApiObject.Kind) &ndash; "CLASS"
* `name` (str)
* `location` (Location)
* `docstring` (Optional[str])
* `metaclass` (Optional[str]) &ndash; A string representing the metaclass.
* `bases` (Optional[array]) &ndash; An array of `str` representing the base classes.
* `members` (array) &ndash; An array of `Data`, `Function` or `Class` objects.
* `decorators` (Optional[array]) &ndash; An array of `str`.

### Data

A `Data` object represents a static value that is assigned to a name. 
Data entry may represent an indirecton (import) or an actual attribute! 

_Fields_

* `type` (str) &ndash; Value is `data`.
* `kind` (ApiObject.Kind) &ndash; "VARIABLE", "INSTANCE_VARIABLE", "CLASS_VARIABLE" or "PROPERTY".
* `name` (str) &ndash; The name for the value.
* `location` (Location)
* `docstring` (Optional[str])
* `datatype` (Optional[str]) &ndash; The datatype of the value.
* `value` (Optional[str]) &ndash; The value in the form of the definition
  in the source.

### Function

Represents a function definition in a module or class.

_Fields_

* `type` (str) &ndash; Value is `function`
* `kind` (ApiObject.Kind) &ndash; "FUNCTION", "METHOD", "STATIC_METHOD" or "CLASS_METHOD".
* `name` (str)
* `location` (str)
* `docstring` (Optional[str])
* `modifiers` (Optional[array]) &ndash; An array of `str` representing the modifers
  of this function (e.g. `async`, `classmethod`, etc.).
* `args` (array) &ndash; An array of `Argument` objects.
* `return_type` (Optional[str]) &ndash; The return type of the function.
* `decorators` (Optional[array]) &ndash; An array of `str` objects.

### Argument

Represents a function argument.

_Fields_

* `type` (str) &ndash; One of `POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`,
  `VAR_POSITIONAL`, `KEYWORD_ONLY` or `VAR_KEYWORD`.
* `name` (str)
* `datatype` (Optional[str])
* `default_value` (Optional[str])

---

<p align="center">Copyright &copy; 2021, Pydoctor contributors</p>
<p align="center">Copyright &copy; 2020, Niklas Rosenstein</p>
