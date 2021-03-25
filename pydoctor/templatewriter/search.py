from pathlib import Path
from typing import Iterable
import json

from pydoctor.templatewriter.pages import Page
from pydoctor import model

class SearchResultsPage(Page):

    filename = 'search-results.html'

    def title(self) -> str:
        return "Search"

class IndexWriter:

    def __init__(self, output_dir: str):
        """
        @arg output_dir: Output directory.
        """
        self.output_dir: Path = Path(output_dir)

    def write_lunr_index(self, allobjects: Iterable[model.Documentable]) -> None:
        index = json.dumps([dict(name=ob.name, fullName=ob.fullName(), kind=ob.kind, docstring=ob.docstring, url=ob.url) 
                            for ob in allobjects], indent=0, separators=(',', ':'))
        
        js_index = f"INDEX={index};"

        with open(self.output_dir.joinpath('index.js'), 'w', encoding='utf-8') as fobj:
            fobj.write(js_index)
            
    def write_fjson_files(self, allobjects: Iterable[model.Documentable]) -> None:
        pass
