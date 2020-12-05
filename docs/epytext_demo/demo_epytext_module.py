"""
This is a module demonstrating Epydoc code documentation features.
"""

def demo_fields_docstring_arguments(m, b):
    """
    Fields are used to describe specific properties of a documented object.

    This function can be used in conjuction with L{demo_typing_arguments} to
    find an arbitrary function's zeros.

    @type  m: number
    @param m: The slope of the line.
    @type  b: number
    @param b: The y intercept of the line..
    @rtype:   number
    @return:  the x intercept of the line M{y=m*x+b}.
    """
    return -b/m


def demo_typing_arguments(m: str, b: bytes) -> bool:
    """
    Type documentation can be extracting from Python standard type hinging.

    @param m: The slope of the line.
    @param b: The y intercept of the line.
    @return:  the x intercept of the line M{y=m*x+b}.
    """
    return bool(-b / m)


def demo_cross_reference():
    """

    The inline markup construct LE{lb}text<object>E{rb} is used to create links to the documentation for other Python objects.
    'text' is the text that should be displayed for the link, and 'object' is the name of the Python object that should be linked to.

    If you wish to use the name of the Python object as the text for the link, you can simply write L{object}``.

        - L{demo_typing_arguments}
        - L{Custom name <demo_typing_arguments>}
    """
