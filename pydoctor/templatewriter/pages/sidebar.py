from twisted.web.template import renderer, Tag
from twisted.web.iweb import IRequest

from pydoctor import model
from pydoctor.templatewriter.pages import TemplateElement

class SideBar(TemplateElement):
    """
    Sidebar
    """

    filename = 'sidebar.html'

    obj: model.Documentable
