"""
Pydoctor pre-process Google-style docstrings to convert them to reStructuredText. 
**All standard reStructuredText formatting will still works as expected**. 

Please see `restructuredtext_demo <../restructuredtext/restructuredtext_demo.html>`_ 
for general reStructuredText formmating exemple. 

Example Google style docstrings.

This module demonstrates documentation as specified by the `Google Python
Style Guide`_. Docstrings may extend over multiple lines. Sections are created
with a section header and a colon followed by a block of indented text.

Example:
    Examples can be given using either the ``Example`` or ``Examples``
    sections. Sections support any reStructuredText formatting, including
    literal blocks::

        $ python example_google.py

Section breaks are created by resuming unindented text. Section breaks
are also implicitly created anytime a new section starts.

Attributes:
    module_level_variable1 (int): Module level variables may be documented in
        either the ``Attributes`` section of the module docstring, or in an
        inline docstring immediately following the variable.

        Either form is acceptable, but the two should not be mixed. Choose
        one convention to document module level variables and be consistent
        with it.

.. _Google Python Style Guide:
   https://google.github.io/styleguide/pyguide.html

"""
from datetime import timedelta
from typing import Any, Awaitable, Callable, Concatenate, List, Mapping, Optional, Sequence, Union, overload # NOQA

module_level_variable1 = 12345

module_level_variable2 = 98765
"""int: Module level variable documented inline.

The docstring may span multiple lines. The type may optionally be specified
on the first line, separated by a colon.
"""


def function_with_types_in_docstring(param1, param2):
    """Example function with types documented in the docstring.

    `PEP 484`_ type annotations are supported. If attribute, parameter, and
    return types are annotated according to `PEP 484`_, they do not need to be
    included in the docstring:

    Args:
        param1 (int): The first parameter.
        param2 (str): The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.

    .. _PEP 484:
        https://www.python.org/dev/peps/pep-0484/

    """


def function_with_pep484_type_annotations(param1: int, param2: str) -> bool:
    """Example function with PEP 484 type annotations.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    """


def module_level_function(param1, param2=None, *args, **kwargs):
    """This is an example of a module level function.

    Function parameters should be documented in the ``Args`` section. The name
    of each parameter is required. The type and description of each parameter
    is optional, but should be included if not obvious.

    If ``*args`` or ``**kwargs`` are accepted,
    they should be listed as ``*args`` and ``**kwargs``.

    The format for a parameter is::

        name (type): description
            The description may span multiple lines. Following
            lines should be indented. The "(type)" is optional.

            Multiple paragraphs are supported in parameter
            descriptions.

    Args:
        param1 (int): The first parameter.
        param2 (`str`, optional): The second parameter. Defaults to None.
            Second line of description should be indented.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

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

    Raises:
        AttributeError: The ``Raises`` section is a list of all exceptions
            that are relevant to the interface.
        ValueError: If ``param2`` is equal to ``param1``.

    """
    if param1 == param2:
        raise ValueError('param1 may not be equal to param2')
    return True


def example_generator(n):
    """Generators have a ``Yields`` section instead of a ``Returns`` section.

    Args:
        n (int): The upper limit of the range to generate, from 0 to ``n`` - 1.

    Yields:
        int: The next number in the range of 0 to ``n`` - 1.

    Examples:
        Examples should be written in doctest format, and should illustrate how
        to use the function.

        >>> print([i for i in example_generator(4)])
        [0, 1, 2, 3]

    """
    for i in range(n):
        yield i


class ExampleError(Exception):
    """Exceptions are documented in the same way as classes.

    The __init__ method should be documented as a docstring on the __init__ method.

    Note:
        Do not include the ``self`` parameter in the ``Args`` section.

    Args:
        msg (str): Human readable string describing the exception.
        code (int, optional): Error code.

    Attributes:
        msg (str): Human readable string describing the exception.
        code (int): Exception error code.

    """

    def __init__(self, msg, code):
        self.msg = msg
        self.code = code


class ExampleClass:
    """The summary line for a class docstring should fit on one line.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (List[Union[str, bytes, int]], optional): Description of `attr2`.

    Methods:
        example_method: Quick example
        __special__: Dunder methods are considered public
        __special_without_docstring__: *Undocumented* text will appear. 
    
    Note:
        The "Methods" section is supported only as a "best effort" basis.

    See:
        Google style "See Also" section is just like any admonition. 
    
    """

    def __init__(self, param1, param2, param3):
        """Example of docstring on the __init__ method.

        The __init__ method should be documented as a docstring on the __init__ method.

        Note:
            Do not include the ``self`` parameter in the ``Args`` section.

        Args:
            param1 (str): Description of ``param1``.
            param2 (`int`, optional): Description of ``param2``. Multiple
                lines are supported.
            param3 (list(str)): Description of ``param3``.

        """
        self.attr1 = param1
        self.attr2 = param2
        self.attr3 = param3  #: Doc comment *inline* with attribute

        #: list(str): Doc comment *before* attribute, with type specified
        self.attr4 = ['attr4']

        self.attr5 = None
        """str: Docstring *after* attribute, with type specified."""

    @property
    def readonly_property(self):
        """str: Properties should be documented in their getter method."""
        return 'readonly_property'

    @property
    def readwrite_property(self):
        """list(str): Properties with both a getter and setter
        should only be documented in their getter method.

        If the setter method contains notable behavior, it should be
        mentioned here.
        """
        return ['readwrite_property']

    @readwrite_property.setter
    def readwrite_property(self, value):
        value

    def example_method(self, param1, param2):
        """Class methods are similar to regular functions.

        Note:
            Do not include the ``self`` parameter in the ``Args`` section.

        Args:
            param1: The first parameter.
            param2: The second parameter.

        Returns:
            tuple(str, str, int, tuple(str, str)): A complicated result. 
        """
        return tuple('string', 'foo', -1, tuple('cool', 'right'))

    def __special__(self):
        """Dunder methods are considered public and will be included in the output. """
        pass

    def __special_without_docstring__(self):
        pass

    def _private(self):
        """
        Private members are any methods or attributes that start with an
        underscore and are *not* special. 
        
        By default they are hidden, they can be displayed
        with the "Show Private API" button. 
        """
        pass

    def _private_without_docstring(self):
        pass

class ExamplePEP526Class:
    """The summary line for a class docstring should fit on one line.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. If ``napoleon_attr_annotations``
    is True, types can be specified in the class body using ``PEP 526``
    annotations.

    Attributes:
        attr1: Description of `attr1`.
        attr2: Description of `attr2`.

    """

    attr1: str
    attr2: int


_not_in_the_demo = object()

@overload
async def overwhelming_overload(
    workflow: tuple[Any, Any],
    *,
    id: str,
    task_queue: str,
    execution_timeout: Optional[timedelta] = None,
    run_timeout: Optional[timedelta] = None,
    task_timeout: Optional[timedelta] = None,
    id_reuse_policy: _not_in_the_demo = '_not_in_the_demo.WorkflowIDReusePolicy.ALLOW_DUPLICATE',
    id_conflict_policy: _not_in_the_demo = '_not_in_the_demo.WorkflowIDConflictPolicy.UNSPECIFIED',
    retry_policy: Optional[_not_in_the_demo.RetryPolicy] = None,
    cron_schedule: str = "",
    memo: Optional[Mapping[str, Any]] = None,
    search_attributes: Optional[
        Union[
            _not_in_the_demo.TypedSearchAttributes,
            _not_in_the_demo.SearchAttributes,
        ]
    ] = None,
    start_delay: Optional[timedelta] = None,
    start_signal: Optional[str] = None,
    start_signal_args: Sequence[Any] = [],
    rpc_metadata: Mapping[str, str] = {},
    rpc_timeout: Optional[timedelta] = None,
    request_eager_start: bool = False,
) -> tuple[Any, Any]: ...

# Overload for single-param workflow
@overload
async def overwhelming_overload(
    workflow: tuple[Any, Any, Any],
    arg: Any,
    *,
    id: str,
    task_queue: str,
    execution_timeout: Optional[timedelta] = None,
    run_timeout: Optional[timedelta] = None,
    task_timeout: Optional[timedelta] = None,
    id_reuse_policy: _not_in_the_demo.WorkflowIDReusePolicy = '_not_in_the_demo.WorkflowIDReusePolicy.ALLOW_DUPLICATE',
    id_conflict_policy: _not_in_the_demo.WorkflowIDConflictPolicy = '_not_in_the_demo.WorkflowIDConflictPolicy.UNSPECIFIED',
    retry_policy: Optional[_not_in_the_demo.RetryPolicy] = None,
    cron_schedule: str = "",
    memo: Optional[Mapping[str, Any]] = None,
    search_attributes: Optional[
        Union[
            _not_in_the_demo.TypedSearchAttributes,
            _not_in_the_demo.SearchAttributes,
        ]
    ] = None,
    start_delay: Optional[timedelta] = None,
    start_signal: Optional[str] = None,
    start_signal_args: Sequence[Any] = [],
    rpc_metadata: Mapping[str, str] = {},
    rpc_timeout: Optional[timedelta] = None,
    request_eager_start: bool = False,
) -> tuple[Any, Any]: ...

# Overload for multi-param workflow
@overload
async def overwhelming_overload(
    workflow: Callable[
        Concatenate[Any, Any], Awaitable[Any]
    ],
    *,
    args: Sequence[Any],
    id: str,
    task_queue: str,
    execution_timeout: Optional[timedelta] = None,
    run_timeout: Optional[timedelta] = None,
    task_timeout: Optional[timedelta] = None,
    id_reuse_policy: _not_in_the_demo.WorkflowIDReusePolicy = '_not_in_the_demo.WorkflowIDReusePolicy.ALLOW_DUPLICATE',
    id_conflict_policy: _not_in_the_demo.WorkflowIDConflictPolicy = '_not_in_the_demo.WorkflowIDConflictPolicy.UNSPECIFIED',
    retry_policy: Optional[_not_in_the_demo.RetryPolicy] = None,
    cron_schedule: str = "",
    memo: Optional[Mapping[str, Any]] = None,
    search_attributes: Optional[
        Union[
            _not_in_the_demo.TypedSearchAttributes,
            _not_in_the_demo.SearchAttributes,
        ]
    ] = None,
    start_delay: Optional[timedelta] = None,
    start_signal: Optional[str] = None,
    start_signal_args: Sequence[Any] = [],
    rpc_metadata: Mapping[str, str] = {},
    rpc_timeout: Optional[timedelta] = None,
    request_eager_start: bool = False,
) -> tuple[Any, Any]: ...

# Overload for string-name workflow
@overload
async def overwhelming_overload(
    workflow: str,
    arg: Any = _not_in_the_demo._arg_unset,
    *,
    args: Sequence[Any] = [],
    id: str,
    task_queue: str,
    result_type: Optional[type] = None,
    execution_timeout: Optional[timedelta] = None,
    run_timeout: Optional[timedelta] = None,
    task_timeout: Optional[timedelta] = None,
    id_reuse_policy: _not_in_the_demo.WorkflowIDReusePolicy = '_not_in_the_demo.WorkflowIDReusePolicy.ALLOW_DUPLICATE',
    id_conflict_policy: _not_in_the_demo.WorkflowIDConflictPolicy = '_not_in_the_demo.WorkflowIDConflictPolicy.UNSPECIFIED',
    retry_policy: Optional[_not_in_the_demo.RetryPolicy] = None,
    cron_schedule: str = "",
    memo: Optional[Mapping[str, Any]] = None,
    search_attributes: Optional[
        Union[
            _not_in_the_demo.TypedSearchAttributes,
            _not_in_the_demo.SearchAttributes,
        ]
    ] = None,
    start_delay: Optional[timedelta] = None,
    start_signal: Optional[str] = None,
    start_signal_args: Sequence[Any] = [],
    rpc_metadata: Mapping[str, str] = {},
    rpc_timeout: Optional[timedelta] = None,
    request_eager_start: bool = False,
) -> tuple[Any, Any]: ...

async def overwhelming_overload(
    workflow: Union[str, Callable[..., Awaitable[Any]]],
    arg: Any = _not_in_the_demo,
    *,
    args: Sequence[Any] = [],
    id: str,
    task_queue: str,
    result_type: Optional[type] = None,
    execution_timeout: Optional[timedelta] = None,
    run_timeout: Optional[timedelta] = None,
    task_timeout: Optional[timedelta] = None,
    id_reuse_policy: _not_in_the_demo.WorkflowIDReusePolicy = '_not_in_the_demo.WorkflowIDReusePolicy.ALLOW_DUPLICATE',
    id_conflict_policy: _not_in_the_demo.WorkflowIDConflictPolicy = '_not_in_the_demo.WorkflowIDConflictPolicy.UNSPECIFIED',
    retry_policy: Optional[_not_in_the_demo.RetryPolicy] = None,
    cron_schedule: str = "",
    memo: Optional[Mapping[str, Any]] = None,
    search_attributes: Optional[
        Union[
            _not_in_the_demo.TypedSearchAttributes,
            _not_in_the_demo.SearchAttributes,
        ]
    ] = None,
    start_delay: Optional[timedelta] = None,
    start_signal: Optional[str] = None,
    start_signal_args: Sequence[Any] = [],
    rpc_metadata: Mapping[str, str] = {},
    rpc_timeout: Optional[timedelta] = None,
    request_eager_start: bool = False,
    stack_level: int = 2,
) -> tuple[Any, Any]:
    """
    This is a big overload taken from the source code of temporalio sdk for Python.
    The types don't make sens: it's only to showcase bigger overload.
    
    Start a workflow and return its handle.

    Args:
        workflow: String name or class method decorated with
            ``@workflow.run`` for the workflow to start.
        arg: Single argument to the workflow.
        args: Multiple arguments to the workflow. Cannot be set if arg is.
        id: Unique identifier for the workflow execution.
        task_queue: Task queue to run the workflow on.
        result_type: For string workflows, this can set the specific result
            type hint to deserialize into.
        execution_timeout: Total workflow execution timeout including
            retries and continue as new.
        run_timeout: Timeout of a single workflow run.
        task_timeout: Timeout of a single workflow task.
        id_reuse_policy: How already-existing IDs are treated.
        id_conflict_policy: How already-running workflows of the same ID are
            treated. Default is unspecified which effectively means fail the
            start attempt. This cannot be set if ``id_reuse_policy`` is set
            to terminate if running.
        retry_policy: Retry policy for the workflow.
        cron_schedule: See https://docs.temporal.io/docs/content/what-is-a-temporal-cron-job/
        memo: Memo for the workflow.
        search_attributes: Search attributes for the workflow. The
            dictionary form of this is deprecated, use
            :py:class:`_not_in_the_demo.TypedSearchAttributes`.
        start_delay: Amount of time to wait before starting the workflow.
            This does not work with ``cron_schedule``.
        start_signal: If present, this signal is sent as signal-with-start
            instead of traditional workflow start.
        start_signal_args: Arguments for start_signal if start_signal
            present.
        rpc_metadata: Headers used on the RPC call. Keys here override
            client-level RPC metadata keys.
        rpc_timeout: Optional RPC deadline to set for the RPC call.
        request_eager_start: Potentially reduce the latency to start this workflow by
            encouraging the server to start it on a local worker running with
            this same client.
            This is currently experimental.

    Returns:
        A workflow handle to the started workflow.

    Raises:
        temporalio.exceptions.WorkflowAlreadyStartedError: Workflow has
            already been started.
        RPCError: Workflow could not be started for some other reason.
    """
    ...