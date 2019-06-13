import ast


class ASTVisitor:
    VERBOSE = 0

    def __init__(self):
        self.node = None
        self._cache = {}

    def default(self, node, *args):
        for child in ast.iter_child_nodes(node):
            self.dispatch(child, *args)

    def dispatch(self, node, *args):
        self.node = node
        klass = node.__class__
        meth = self._cache.get(klass, None)
        if meth is None:
            className = klass.__name__
            meth = getattr(self.visitor, "visit" + className, None)
            if meth is None:
                meth = self.default
            self._cache[klass] = meth
        return meth(node, *args)

    def preorder(self, tree, visitor, *args):
        """Do preorder walk of tree using visitor"""
        self.visitor = visitor
        visitor.visit = self.dispatch
        self.dispatch(tree, *args)  # XXX *args make sense?


def walk(tree, visitor):
    ASTVisitor().preorder(tree, visitor)
