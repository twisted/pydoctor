from pathlib import Path
from pydoctor.templatewriter import TemplateLookup
from typing import Iterable, Optional, Type
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
    def documents(self, request: IRequest, tag: Tag) -> IRenderable:
        documents = [dict(id=str(i), name=ob.name, 
                          fullName=ob.fullName(), kind=ob.kind or '', 
                          summary=epydoc2stan.format_summary(ob), url=ob.url)   
                          for i, ob in enumerate(self.system.allobjects.values())]
        for doc in documents:
            yield tag.clone().fillSlots(**doc)


# https://lunr.readthedocs.io/en/latest/
def write_lunr_index(output_dir: str, allobjects: Iterable[model.Documentable]) -> None:
    """
    @arg output_dir: Output directory.
    @arg allobjects: All objects in the system. 
    """
    output_dir_path = Path(output_dir)
    # TODO: sanitize docstring in a proper way. 
    documents = [dict(ref=i, name=ob.name, 
                        fullName=ob.fullName(), kind=ob.kind or '', 
                        docstring=ob.docstring )   
                        for i, ob in enumerate(allobjects)]

    index = lunr(
        ref='ref',
        fields=[dict(field_name='name', boost=10), 
                dict(field_name='fullName', boost=5),
                dict(field_name='docstring', boost=2), ],
        documents=documents )
    
    serialized_index = json.dumps(index.serialize())

    with open(output_dir_path.joinpath('searchindex.json'), 'w', encoding='utf-8') as fobj:
        fobj.write(serialized_index)

searchpages: Iterable[Type[Page]] = [SearchResultsPage, AllDocuments]
