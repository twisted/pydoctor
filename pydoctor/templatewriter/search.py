from pathlib import Path
from typing import Any, Iterable, List, Tuple, Type, Dict, TYPE_CHECKING
import json

from pydoctor.templatewriter.pages import Page
from pydoctor import model, epydoc2stan, node2stan

from twisted.web.template import Tag, renderer
from lunr import lunr, get_default_builder, stop_word_filter

if TYPE_CHECKING:
    from twisted.web.template import Flattenable

def get_all_documents_struct(system: model.System) -> List[Dict[str, "Flattenable"]]:
    documents: List[Dict[str, "Flattenable"]] = [dict(
                          id=ob.fullName(), 
                          name=ob.name, 
                          fullName=ob.fullName(), 
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
        for doc in get_all_documents_struct(self.system):
            yield tag.clone().fillSlots(**doc)

# https://lunr.readthedocs.io/en/latest/
def write_lunr_index(output_dir: Path, system: model.System) -> None:
    """
    @arg output_dir: Output directory.
    @arg system: System. 
    """

    def get_ob_boost(ob: model.Documentable) -> int:
        if isinstance(ob, (model.Class, model.Package, model.Module)):
            return 3
        elif isinstance(ob, model.Function):
            return 2
        else:
            return 1

    documents: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for ob in (o for o in system.allobjects.values() if o.isVisible):
        
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

        documents.append(
                    (
                        {
                            "name": ob.name, 
                            "fullName": ob.fullName(), 
                            "docstring": doc
                        }, 
                        {
                            "boost": get_ob_boost(ob)
                        }
                    )
        )   

    # Disable the stop-word filter for fields fullName and name. 
    # https://lunr.readthedocs.io/en/latest/customisation.html#skip-a-pipeline-function-for-specific-field-names
    
    builder = get_default_builder()
    builder.pipeline.skip(stop_word_filter.stop_word_filter, ["fullName", "name"])  
    index = lunr(
        ref='fullName',
        fields=[{'field_name':'name', 'boost':2}, 
                {'field_name':'docstring', 'boost':1},
                {'field_name':'fullName', 'boost':1} ],
        documents=documents, 
        builder=builder)   
    
    serialized_index = json.dumps(index.serialize())

    with output_dir.joinpath('searchindex.json').open('w', encoding='utf-8') as fobj:
        fobj.write(serialized_index)

searchpages: List[Type[Page]] = [AllDocuments]
