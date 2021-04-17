from os import PathLike
from pathlib import Path
from pydoctor.templatewriter import TemplateLookup
from typing import Iterable, List, Optional, Sequence, Type
import json

from twisted.web.iweb import IRenderable, IRequest, ITemplateLoader

from pydoctor.templatewriter.pages import Page
from pydoctor import model, epydoc2stan

from twisted.web.template import Tag, renderer
from lunr import lunr

class SearchResultsPage(Page):

    filename = 'search-results.html'

    def title(self) -> str:
        return "Search"

class AllDocuments(Page):
    
    filename = 'all-documents.html'

    def title(self) -> str:
        return "All Documents"

    @renderer
    def documents(self, request: IRequest, tag: Tag) -> Iterable[IRenderable]:
        documents = [dict(id=str(i), name=ob.name, 
                          fullName=ob.fullName(), kind=str(ob.kind) or '', type=str(ob.__class__.__name__),
                          summary=epydoc2stan.format_summary(ob), url=ob.url, privacy=str(ob.privacyClass.name))   
                          for i, ob in enumerate(self.system.allobjects.values()) if ob.privacyClass != model.PrivacyClass.HIDDEN]
        for doc in documents:
            yield tag.clone().fillSlots(**doc)


# https://lunr.readthedocs.io/en/latest/
def write_lunr_index(output_dir: Path, system: model.System) -> None:
    """
    @arg output_dir: Output directory.
    @arg allobjects: All objects in the system. 
    """

    def get_ob_boost(ob) -> int:
        if isinstance(ob, (model.Class, model.Package, model.Module)):
            return 3
        elif isinstance(ob, model.Function):
            return 2
        else:
            return 1

    # TODO: sanitize docstring in a proper way to be more easily indexable by lunr.
    documents = [(dict(ref=str(i), name=ob.name, 
                        fullName=ob.fullName(), kind=ob.kind or '', type=str(ob.__class__.__name__),
                        docstring=ob.docstring, privacy=str(ob.privacyClass) ), 
                 dict(boost=get_ob_boost(ob)))   
                        for i, ob in enumerate(system.allobjects.values()) if ob.privacyClass != model.PrivacyClass.HIDDEN]

    index = lunr(
        ref='ref',
        fields=[dict(field_name='name', boost=2), 
                dict(field_name='docstring', boost=1),
                dict(field_name='fullName', boost=1) ],
        documents=documents )   
    
    serialized_index = json.dumps(index.serialize())

    with open(output_dir.joinpath('searchindex.json'), 'w', encoding='utf-8') as fobj:
        fobj.write(serialized_index)

searchpages: List[Type[Page]] = [SearchResultsPage, AllDocuments]
