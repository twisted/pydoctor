import ast
from typing import Any, List, Type
from pydoctor import astutils, extensions,  model

class ModVisitor(extensions.ModuleVisitorExt):

    def depart_AnnAssign(self, node: ast.AnnAssign) -> None:
        """
        Called after an annotated assignment definition is visited.
        """
        ctx = self.visitor.builder.current
        if not isinstance(ctx, model.Class):
            # check if the current context object is a class
            return

        if not any(ctx.expandName(b) == 'pydantic.BaseModel' for b in ctx.bases):
            # check if the current context object if a class derived from ``pydantic.BaseModel``
            return

        dottedname = astutils.node2dottedname(node.target)
        if not dottedname or len(dottedname)!=1:
            # check if the assignment is a simple name, otherwise ignore it
            return
        
        # Get the attribute from current context
        attr = ctx.contents[dottedname[0]]

        assert isinstance(attr, model.Attribute)

        # All class variables that are not annotated with ClassVar will be transformed to instance variables.
        if astutils.is_using_typing_classvar(attr.annotation, attr):
            return

        if attr.kind == model.DocumentableKind.CLASS_VARIABLE:
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitors(ModVisitor)

class PydanticSystem2(model.System):
    # Add our custom extension
    extensions: List[str] = []
    custom_extensions = ['pydoctor.test.test_pydantic_fields']

## Testing code

import pytest
from pydoctor.test.test_astbuilder import fromText, PydanticSystem

pydantic_systemcls_param = pytest.mark.parametrize('systemcls', (PydanticSystem, PydanticSystem2))

@pydantic_systemcls_param
def test_pydantic_fields(systemcls: Type[model.System]) -> None:
    src = '''
    from typing import ClassVar
    from pydantic import BaseModel, Field
    class Model(BaseModel):
        a: int
        b: int = Field(...)
        name:str = 'Jane Doe'
        kind:ClassVar = 'person'
    '''

    mod = fromText(src, modname='mod', systemcls=systemcls)

    assert mod.contents['Model'].contents['a'].kind == model.DocumentableKind.INSTANCE_VARIABLE
    assert mod.contents['Model'].contents['b'].kind == model.DocumentableKind.INSTANCE_VARIABLE
    assert mod.contents['Model'].contents['name'].kind == model.DocumentableKind.INSTANCE_VARIABLE
    assert mod.contents['Model'].contents['kind'].kind == model.DocumentableKind.CLASS_VARIABLE

