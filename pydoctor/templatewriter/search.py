"""
Code building ``all-documents.html`` and ``searchindex.json``.
"""

from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple, Type, Dict, TYPE_CHECKING
import json

import attr

from pydoctor.templatewriter.pages import Page
from pydoctor import model, epydoc2stan, node2stan

from twisted.web.template import Tag, renderer
from lunr import lunr, get_default_builder, stop_word_filter

if TYPE_CHECKING:
    from twisted.web.template import Flattenable

def get_all_documents_flattenable(system: model.System) -> List[Dict[str, "Flattenable"]]:
    """
    Get the all data to be writen into ``all-documents.html`` file.
    """
    documents: List[Dict[str, "Flattenable"]] = [dict(
                          id=ob.fullName(), 
                          name=epydoc2stan.insert_break_points(ob.name), 
                          fullName=epydoc2stan.insert_break_points(ob.fullName()), 
                          kind=epydoc2stan.format_kind(ob.kind) if ob.kind else '', 
                          type=str(ob.__class__.__name__),
                          summary=epydoc2stan.format_summary(ob),
                          url=ob.url, 
                          privacy=str(ob.privacyClass.name))   

                          for ob in system.allobjects.values() if ob.isVisible]
    return documents

class AllDocuments(Page):
    
    filename = 'all-documents.html'

    def title(self) -> str:
        return "All Documents"

    @renderer
    def documents(self, request: None, tag: Tag) -> Iterable[Tag]:        
        for doc in get_all_documents_flattenable(self.system):
            yield tag.clone().fillSlots(**doc)

@attr.s(auto_attribs=True)
class LunrIndexWriter:
    """
    Class to write lunr indexes with configurable fields. 
    """
    
    output_file: Path
    system: model.System
    fields: List[str]

    _BOOSTS = {
                'name':4,
                'names': 2,
                'qname':1,
                'docstring':1,
                'kind':-1
              }

    @staticmethod
    def get_ob_boost(ob: model.Documentable) -> int:
        if isinstance(ob, (model.Class, model.Package, model.Module)):
            return 3
        elif isinstance(ob, model.Function):
            return 2
        else:
            return 1
    
    def format(self, ob: model.Documentable, field:str) -> Optional[str]:
        try:
            return getattr(self, f'format_{field}')(ob)
        except AttributeError as e:
            raise AssertionError() from e
    
    def format_name(self, ob: model.Documentable) -> str:
        return ob.name
    
    def format_names(self, ob: model.Documentable) -> str:
        return ' '.join(stem_identifier(ob.name))
    
    def format_qname(self, ob: model.Documentable) -> str:
        return ob.fullName()
    
    def format_docstring(self, ob: model.Documentable) -> Optional[str]:
        # sanitize docstring in a proper way to be more easily indexable by lunr.
        doc = None
        source = epydoc2stan.ensure_parsed_docstring(ob)
        if source is not None:
            assert ob.parsed_docstring is not None
            try:
                doc = ' '.join(node2stan.gettext(ob.parsed_docstring.to_node()))
            except NotImplementedError:
                # some ParsedDocstring subclass raises NotImplementedError on calling to_node()
                # Like ParsedPlaintextDocstring.
                doc = source.docstring
        return doc

    def format_kind(self, ob:model.Documentable) -> str:
        return epydoc2stan.format_kind(ob.kind) if ob.kind else ''

    def get_corpus(self) -> List[Tuple[Dict[str, Optional[str]], Dict[str, int]]]:

        documents: List[Tuple[Dict[str, Optional[str]], Dict[str, int]]] = []

        for ob in (o for o in self.system.allobjects.values() if o.isVisible):

            documents.append(
                        (
                            {
                                f:self.format(ob, f) for f in self.fields
                            }, 
                            {
                                "boost": self.get_ob_boost(ob)
                            }
                        )
            )   
        
        return documents

    def write(self) -> None:
        # Disable the stop-word filter for some fields
        # https://lunr.readthedocs.io/en/latest/customisation.html#skip-a-pipeline-function-for-specific-field-names
        
        builder = get_default_builder()
        builder.pipeline.skip(stop_word_filter.stop_word_filter, ["qname", "name", "kind", "names"])  

        index = lunr(
            ref='fullName',
            fields=[{'field_name':name, 'boost':self._BOOSTS[name]} for name in self.fields],
            documents=self.get_corpus(), 
            builder=builder)   
        
        serialized_index = json.dumps(index.serialize())

        with self.output_file.open('w', encoding='utf-8') as fobj:
            fobj.write(serialized_index)

# https://lunr.readthedocs.io/en/latest/
def write_lunr_index(output_dir: Path, system: model.System) -> None:
    """
    Write ``searchindex.json`` and ``fullsearchindex.json`` to the output directory.

    @arg output_dir: Output directory.
    @arg system: System. 
    """
    LunrIndexWriter(output_dir / "searchindex.json", system, ["name", "names", "qname"]).write()
    LunrIndexWriter(output_dir / "fullsearchindex.json", system, ["name", "names", "qname", "docstring", "kind"]).write()

def stem_identifier(_t: str) -> Iterator[str]:
    parts = epydoc2stan._split_indentifier_parts_on_case(_t)
    for p in parts:
        p = p.strip('_')
        if p and p.lower() not in stop_word_filter.WORDS and p!=_t: 
            yield p

searchpages: List[Type[Page]] = [AllDocuments]
