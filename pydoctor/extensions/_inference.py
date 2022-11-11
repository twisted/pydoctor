"""
Support for stuff like type inference and recognition of complex C{__all__} variables.
"""

from typing import Any, Callable, Iterable, Iterator, List, Optional, Sequence, Tuple, TypeVar, Union
import ast
import re

from pydoctor import astbuilder, astutils, extensions, visitor
from pydoctor import model
from pydoctor.epydoc.markup._pyval_repr import colorize_inline_pyval

import astroid.nodes
import astroid.util
import astroid.inference
import astroid.helpers
import astroid.manager
import astroid.const
import astroid.exceptions


SUPPORTED_ALL_OPERATIONS = ('append', 'extend')

# 1 declare an astroid transform that converts __all__.append/extend to augmented assignements. 

def get_all_oprerations_transform(system:model.System) -> Callable[[astroid.nodes.Expr], Union[astroid.nodes.Expr, astroid.nodes.AugAssign]]:
    def transform(node:astroid.nodes.Expr) -> Union[astroid.nodes.Expr, astroid.nodes.AugAssign]:
        v = node.value
        
        assert isinstance(v, astroid.nodes.Call) and isinstance(v.func, astroid.nodes.Attribute)
        
        o = v.func.expr
        a = v.func.attrname

        if len(v.args)==1 and len(v.keywords)==0:
            # We can safely apply this transformation because we know __all__ should be a list or tuple.
            assert isinstance(o, astroid.nodes.Name) and o.name == '__all__'
            
            aug = None
            arg = v.args[0]

            aug = astroid.nodes.AugAssign(op='+=', parent=node.parent)
            target = astroid.nodes.AssignName(o.name, parent=aug)

            if a == 'extend':
                arg.parent = aug
                value = arg
            elif a == 'append':
                value = astroid.nodes.List(ctx=astroid.const.Context.Load, parent=aug)
                arg.parent = value
                value.postinit(elts=[arg])
            else:
                raise AssertionError('bogus astroid predicate')

            aug.postinit(target=target, value=value)
            node.parent.set_local('__all__', target)
            return fix_missing_locations(copy_location(aug, node))
        
        return node

    return transform

def get_all_oprerations_predicate(system:model.System) -> Callable[[astroid.nodes.Expr], bool]:
    def predicate(node:astroid.nodes.Expr) -> bool:
        """
        Is this expression a call to __all__.extend() or __all__.append() that happens in the scope of pydoctor ?
        """

        v = node.value
        if isinstance(v, astroid.nodes.Call) and isinstance(v.func, astroid.nodes.Attribute):
            o = v.func.expr
            a = v.func.attrname
            
            # a call to __all__.extend() or __all__.append() ?
            if isinstance(o, astroid.nodes.Name) and o.name == '__all__' and a in SUPPORTED_ALL_OPERATIONS:

                # not in the scope of pydoctor?
                modname = node.root().qname()
                if modname not in system.allobjects:
                    system.msg('__all__ transform', f'not transforming {node.as_string()} into an augmented assigment because {modname} not found in {list(system.allobjects)}')
                    return False

                return True
        
        return False
    

    return predicate

# 1.5 Declare the module visitor

class ModuleVisitor(extensions.ModuleVisitorExt):
    
    def visit_Module(self, _: ast.Module) -> None:
        mod = self.visitor.builder.current
        assert isinstance(mod, model.Module)

        astrmod = mod.nodes.astroid
        if astrmod:
            inferAll(mod, astrmod)

def inferAll(mod:model.Module, astrmod:astroid.nodes.Module) -> None:
    """
    Augmented version of L{pydoctor.astbuilder.parseAll}.
    """
    try:
        assignments = astrmod.getattr('__all__')
    except astroid.exceptions.AttributeInferenceError:
        assignments = []
    
    if not assignments:
        return
    
    assignment = assignments[-1]
    
    ivalue = _infer_last(assignment, typecheck=(astroid.nodes.Tuple, astroid.nodes.List))
    if ivalue is None:
        mod.report(f'Cannot infer "__all__". Node infers to: {list(assignment.infer())}', lineno_offset=assignment.lineno or 0)
        return
        # should fallback to default behaviour!
    
    names = []
    for idx, item in enumerate(ivalue.elts):
        
        if isinstance(item, astroid.nodes.Const):
            name = item.value
        else:
            mod.report(
                f'Cannot infer element {idx} of "__all__", got {item.__class__.__name__} instead of constant',
                section='all', lineno_offset=assignment.lineno or 0)
            continue

        if isinstance(name, str):
            names.append(name)
        else:
            mod.report(
                f'Element {idx} of "__all__" has '
                f'type "{type(name).__name__}", expected "str"',
                section='all', lineno_offset=assignment.lineno or 0)
    
    mod.all = names

# 2 register the tranform as well as the module visitor externsion that sets the value of Module.all thanks to astroid inference. 

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    
    r.register_astbuilder_visitor(ModuleVisitor)

    # Register the transform with astroid, unfortunately, the astroid manager is a singleton
    # so this setting affect all other uses of astroid in the same environment. 
    astroid.manager.AstroidManager().register_transform(
                astroid.nodes.Expr, 
                get_all_oprerations_transform(r.system), 
                get_all_oprerations_predicate(r.system))

# utility function to work with astroid

_T = TypeVar('_T')
def _infer_last(node:astroid.nodes.NodeNG, typecheck:Tuple[_T, ...]=(astroid.nodes.NodeNG,)) -> Optional[_T]:
    # we want to get the last value from astroid
    # https://github.com/PyCQA/astroid/pull/1612
    i = [e for e in _infer(node) if isinstance(e, typecheck)]
    if len(i)==0:
        return None
    else:
        return i[-1]

def _infer(node:astroid.nodes.NodeNG) -> List[astroid.nodes.NodeNG]:
    r = []
    gen = node.infer()
    while True:
        try:
            v = next(gen)
            if v is astroid.util.Uninferable:
                continue
            r.append(v)
        except StopIteration:
            return r
        except astroid.exceptions.InferenceError:
            continue

# utility functions (adjusted from cpython)

def copy_location(new_node:astroid.nodes.NodeNG, old_node:astroid.nodes.NodeNG) -> astroid.nodes.NodeNG:
    """
    Copy source location (`lineno`, `col_offset`, `end_lineno`, and `end_col_offset`
    attributes) from *old_node* to *new_node* if possible, and return *new_node*.
    """
    for attr in 'lineno', 'col_offset', 'end_lineno', 'end_col_offset':
        value = getattr(old_node, attr, None)
        if value is not None:
            setattr(new_node, attr, value)
    return new_node

def fix_missing_locations(node:astroid.nodes.NodeNG) -> astroid.nodes.NodeNG:
    """
    When you compile a node tree with compile(), the compiler expects lineno and
    col_offset attributes for every node that supports them.  This is rather
    tedious to fill in for generated nodes, so this helper adds these attributes
    recursively where not already set, by setting them to the values of the
    parent node.  It works recursively starting at *node*.
    """
    def _fix(node:astroid.nodes.NodeNG, lineno:int, col_offset:int, end_lineno:int, end_col_offset:int) -> None:
        
        # a particularity in astroid is that Module instances are initiated with a linenumber of 0,
        # so we don't store linenumbers if equal to zero, we use default value which is 1.
        if node.lineno is None:
            node.lineno = lineno
        elif node.lineno!=0:
            lineno = node.lineno
    
        if node.end_lineno is None:
            node.end_lineno = end_lineno
        elif node.end_lineno!=0:
            end_lineno = node.end_lineno
    
        if node.col_offset is None:
            node.col_offset = col_offset
        else:
            col_offset = node.col_offset
    
        if node.end_col_offset is None:
            node.end_col_offset = end_col_offset
        else:
            end_col_offset = node.end_col_offset
            
        for child in node.get_children():
            _fix(child, lineno, col_offset, end_lineno, end_col_offset)
    _fix(node, 1, 0, 1, 0)
    return node