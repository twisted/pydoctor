"""
Dataclass-like libraries are all alike: 
- They transform class variables into instance variable un certain conditions.
- They automatically provides a constructor method without having to define __init__.
"""
import ast
from abc import abstractmethod, ABC
from typing import Optional, Union
from pydoctor import astutils
from pydoctor.model import Module, Attribute, Class, Documentable
from pydoctor.extensions import ModuleVisitorExt, ClassMixin

class DataclasLikeClass(ClassMixin):
    dataclassLike:Optional[object] = None

class DataclassLikeVisitor(ModuleVisitorExt, ABC):

    DATACLASS_LIKE_KIND:object = NotImplemented

    def __init__(self) -> None:
        super().__init__()
        assert self.DATACLASS_LIKE_KIND is not NotImplemented, "constant DATACLASS_LIKE_KIND should have a value"
    
    @abstractmethod
    def isDataclassLike(self, cls:ast.ClassDef, mod:Module) -> Optional[object]:
        """
        If this classdef adopts dataclass-like behaviour, returns an non-zero int, otherwise returns None.
        Returned value is directly stored in the C{dataclassLike} attribute of the visited class.
        Used to determine whether L{transformClassVar} method should be called for each class variables
        in this class.

        The int value should be a constant representing the kind of dataclass-like this class implements.
        Class decorated with @dataclass and @attr.s will have different non-zero C{dataclassLike} attribute.
        """

    @abstractmethod
    def transformClassVar(self, cls:Class, attr:Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        """
        Transform this class variable into a instance variable.
        This method is left abstract because it's not as simple as setting::
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
        """
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        cls = self.visitor.builder._stack[-1].contents.get(node.name)
        if not isinstance(cls, Class):
            return
        assert isinstance(cls, DataclasLikeClass)
        dataclassLikeKind = self.isDataclassLike(node, cls.module)
        if dataclassLikeKind:
            if not cls.dataclassLike:
                cls.dataclassLike = dataclassLikeKind
            else:
                cls.report(f'class is both {cls.dataclassLike} and {dataclassLikeKind}')
    
    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        current = self.visitor.builder.current

        for dottedname in astutils.iterassign(node):
            if dottedname and len(dottedname)==1:
                # We consider single name assignment only
                if not isinstance(current, Class):
                    continue
                assert isinstance(current, DataclasLikeClass)
                if not current.dataclassLike == self.DATACLASS_LIKE_KIND:
                    continue
                target, = dottedname
                attr: Optional[Documentable] = current.contents.get(target)
                if not isinstance(attr, Attribute) or \
                    astutils.is_using_typing_classvar(attr.annotation, current):
                    continue
                annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
                self.transformClassVar(current, attr, annotation, node.value)
    
    visit_AnnAssign = visit_Assign
