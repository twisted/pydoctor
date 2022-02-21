from pathlib import Path
from typing import Iterable, List, Type, Dict
import json

from pydoctor.templatewriter.pages import Page
from pydoctor import model, epydoc2stan

from twisted.web.iweb import IRenderable, IRequest
from twisted.web.template import Tag, renderer
from lunr import lunr

def get_all_documents_struct(system: model.System) -> List[Dict[str, str]]:
    documents = [dict(id=ob.fullName(), 
                          name=ob.name, 
                          fullName=ob.fullName(), 
                          kind=epydoc2stan.format_kind(ob.kind) if ob.kind else '', 
                          type=str(ob.__class__.__name__),
                          summary='',
                          url=ob.url, 
                          privacy=str(ob.privacyClass.name))   

                          for ob in system.allobjects.values() if ob.isVisible]
    return documents

class AllDocuments(Page):
    
    filename = 'all-documents.html'

    def title(self) -> str:
        return "All Documents"

    @renderer
    def documents(self, request: IRequest, tag: Tag) -> Iterable[IRenderable]:        
        for doc in get_all_documents_struct(self.system):
            doc['summary'] = epydoc2stan.format_summary(self.system.allobjects[doc.get('fullName')])
            yield tag.clone().fillSlots(**doc)


def write_all_documents_json(output_dir: Path, system: model.System) -> None:
    with output_dir.joinpath('all-documents.json').open('w', encoding='utf-8') as fobj:
        json.dump(get_all_documents_struct(system), fobj)

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
