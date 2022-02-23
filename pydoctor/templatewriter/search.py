from pathlib import Path
from typing import Iterable, List, Type, Dict, TYPE_CHECKING
import json

from pydoctor.templatewriter.pages import Page
from pydoctor import model, epydoc2stan

from twisted.web.iweb import IRenderable, IRequest
from twisted.web.template import Tag, renderer
from lunr import lunr

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
    def documents(self, request: IRequest, tag: Tag) -> Iterable[Tag]:        
        for doc in get_all_documents_struct(self.system):
            yield tag.clone().fillSlots(**doc)

# https://lunr.readthedocs.io/en/latest/

# TODO: Disable the stop-word filter: https://github.com/yeraydiazdiaz/lunr.py/blob/master/lunr/stop_word_filter.py 
# for the fields name and fullName, see https://github.com/yeraydiazdiaz/lunr.py/issues/108

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

    # TODO: sanitize docstring in a proper way to be more easily indexable by lunr.
    # Once https://github.com/twisted/pydoctor/pull/386 is merged, use node2stan.gettext() to index the docstring text only.

    documents = [(dict(name=ob.name, 
                        fullName=ob.fullName(), 
                        docstring=ob.docstring,), 
                 dict(boost=get_ob_boost(ob)))   
                        
                 for ob in system.allobjects.values() if ob.isVisible]

    index = lunr(
        ref='fullName',
        fields=[dict(field_name='name', boost=2), 
                dict(field_name='docstring', boost=1),
                dict(field_name='fullName', boost=1) ],
        documents=documents )   
    
    serialized_index = json.dumps(index.serialize())

    with output_dir.joinpath('searchindex.json').open('w', encoding='utf-8') as fobj:
        fobj.write(serialized_index)

searchpages: List[Type[Page]] = [AllDocuments]
