
from typing import Iterable
from pydoctor.test import CapSys
from pydoctor.test.epydoc.test_restructuredtext import parse_rst
from pydoctor import visitor
from docutils import nodes

def dump(node: nodes.Node, text:str='') -> None:
    print('{}{:<15} line: {}, rawsource: {}'.format(
        text,
        type(node).__name__, 
        node.line,
        node.rawsource.replace('\n', '\\n')))  

class DocutilsNodeVisitor(visitor.Visitor[nodes.Node]):
    def unknown_visit(self, ob: nodes.Node) -> None:
        pass
    
    @classmethod
    def get_children(cls, ob:nodes.Node) -> Iterable[nodes.Node]:
        if isinstance(ob, nodes.Element):
            return ob.children # type:ignore[no-any-return]
        return []

class MainVisitor(DocutilsNodeVisitor):
    def visit_title_reference(self, node: nodes.Node) -> None:
        raise self.SkipNode()

class ParagraphDump(visitor.VisitorExt[nodes.Node]):
    when = visitor.When.AFTER
    def visit_paragraph(self, node: nodes.Node) -> None:
        dump(node)

class TitleReferenceDumpAfter(visitor.VisitorExt[nodes.Node]):
    when = visitor.When.AFTER
    def visit_title_reference(self, node: nodes.Node) -> None:
        dump(node)

class GenericDump(DocutilsNodeVisitor):
    def unknown_visit(self, node: nodes.Node) -> None:
        dump(node, '[visit-main] ')
    def unknown_departure(self, node: nodes.Node) -> None:
        dump(node, '[depart-main] ')

class GenericDumpAfter(visitor.VisitorExt[nodes.Node]):
    when = visitor.When.INNER
    def unknown_visit(self, node: nodes.Node) -> None:
        dump(node, '[visit-inner] ')
    def unknown_departure(self, node: nodes.Node) -> None:
        dump(node, '[depart-inner] ')

class GenericDumpBefore(visitor.VisitorExt[nodes.Node]):
    when = visitor.When.OUTTER
    def unknown_visit(self, node: nodes.Node) -> None:
        dump(node, '[visit-outter] ')
    def unknown_departure(self, node: nodes.Node) -> None:
        dump(node, '[depart-outter] ')


def test_visitor_ext(capsys:CapSys) -> None:

    parsed_doc = parse_rst('''
Hello
=====

Dolor sit amet
''')
    doc = parsed_doc.to_node()

    vis = GenericDump()
    vis.extensions.add(GenericDumpAfter, GenericDumpBefore)
    vis.walkabout(doc)
    assert capsys.readouterr().out == r'''[visit-outter] document        line: None, rawsource: 
[visit-main] document        line: None, rawsource: 
[visit-inner] document        line: None, rawsource: 
[visit-outter] title           line: 3, rawsource: Hello
[visit-main] title           line: 3, rawsource: Hello
[visit-inner] title           line: 3, rawsource: Hello
[visit-outter] Text            line: None, rawsource: Hello
[visit-main] Text            line: None, rawsource: Hello
[visit-inner] Text            line: None, rawsource: Hello
[depart-inner] Text            line: None, rawsource: Hello
[depart-main] Text            line: None, rawsource: Hello
[depart-outter] Text            line: None, rawsource: Hello
[depart-inner] title           line: 3, rawsource: Hello
[depart-main] title           line: 3, rawsource: Hello
[depart-outter] title           line: 3, rawsource: Hello
[visit-outter] paragraph       line: 5, rawsource: Dolor sit amet
[visit-main] paragraph       line: 5, rawsource: Dolor sit amet
[visit-inner] paragraph       line: 5, rawsource: Dolor sit amet
[visit-outter] Text            line: None, rawsource: Dolor sit amet
[visit-main] Text            line: None, rawsource: Dolor sit amet
[visit-inner] Text            line: None, rawsource: Dolor sit amet
[depart-inner] Text            line: None, rawsource: Dolor sit amet
[depart-main] Text            line: None, rawsource: Dolor sit amet
[depart-outter] Text            line: None, rawsource: Dolor sit amet
[depart-inner] paragraph       line: 5, rawsource: Dolor sit amet
[depart-main] paragraph       line: 5, rawsource: Dolor sit amet
[depart-outter] paragraph       line: 5, rawsource: Dolor sit amet
[depart-inner] document        line: None, rawsource: 
[depart-main] document        line: None, rawsource: 
[depart-outter] document        line: None, rawsource: 
'''


def test_visitor(capsys:CapSys) -> None:

    parsed_doc = parse_rst('''
Fizz
====
Lorem ipsum `notfound`.

Buzz
****

Lorem ``ipsum``

.. code-block:: python

   x = 0

.. note::

   Dolor sit amet
   `notfound`.

   .. code-block:: python

      y = 1

Dolor sit amet `another link <notfound>`.
Dolor sit amet `link <notfound>`.
bla blab balba.
''')
    doc = parsed_doc.to_node()

    MainVisitor(visitor.ExtList(TitleReferenceDumpAfter)).walk(doc)
    assert capsys.readouterr().out == r'''title_reference line: None, rawsource: `notfound`
title_reference line: None, rawsource: `notfound`
title_reference line: None, rawsource: `another link <notfound>`
title_reference line: None, rawsource: `link <notfound>`
'''
    
    vis = MainVisitor()
    vis.extensions.add(ParagraphDump, TitleReferenceDumpAfter)
    vis.walk(doc)
    assert capsys.readouterr().out == r'''paragraph       line: 4, rawsource: Lorem ipsum `notfound`.
title_reference line: None, rawsource: `notfound`
paragraph       line: 9, rawsource: Lorem ``ipsum``
paragraph       line: 17, rawsource: Dolor sit amet\n`notfound`.
title_reference line: None, rawsource: `notfound`
paragraph       line: 24, rawsource: Dolor sit amet `another link <notfound>`.\nDolor sit amet `link <notfound>`.\nbla blab balba.
title_reference line: None, rawsource: `another link <notfound>`
title_reference line: None, rawsource: `link <notfound>`
'''
