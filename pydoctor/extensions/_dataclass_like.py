"""
Dataclass-like libraries are all alike: 
- They transform class variables into instance variable un certain conditions.
- They autoamtically provides a constructor method without having to define __init__.

More specifically
"""
import ast
from abc import abstractmethod, ABC
from typing import Optional, Union
from pydoctor import astutils
from pydoctor.model import Module, Attribute, Class, Documentable
from pydoctor.extensions import ModuleVisitorExt, ClassMixin

class DataclasLikeClass(ClassMixin):
    isDataclassLike:bool = False

class DataclassLikeVisitor(ModuleVisitorExt, ABC):
    
    @abstractmethod
    def isDataclassLike(self, cls:ast.ClassDef, mod:Module) -> bool:
        """
        Whether L{transformClassVar} method should be called for each class variables
        in this class.
        """

    @abstractmethod
    def transformClassVar(self, cls:Class, attr:Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        """
        Transform this class variable into a instance variable.
        This method is left abstract because it might not be as simple as setting::
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
        (but it also might be just that for the simpler cases)
        """
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        cls = self.visitor.builder._stack[-1].contents.get(node.name)
        if not isinstance(cls, Class):
            return
        assert isinstance(cls, DataclasLikeClass)
        cls.isDataclassLike = self.isDataclassLike(node, cls.module)
    
    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        current = self.visitor.builder.current

        for dottedname in astutils.iterassign(node):
            if dottedname and len(dottedname)==1:
                # We consider single name assignment only
                if not isinstance(current, Class):
                    continue
                assert isinstance(current, DataclasLikeClass)
                if not current.isDataclassLike:
                    continue
                target, = dottedname
                attr: Optional[Documentable] = current.contents.get(target)
                if not isinstance(attr, Attribute) or \
                    astutils.is_using_typing_classvar(attr.annotation, current):
                    continue
                annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
                self.transformClassVar(current, attr, annotation, node.value)
    
    visit_AnnAssign = visit_Assign
