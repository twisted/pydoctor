"""
Support for Sphinx compatibility.
"""
from __future__ import absolute_import

import os
import zlib

from pydoctor import model


class SphinxInventory(object):
    """
    Sphinx inventory handler.
    """

    version = (2, 0)

    def __init__(self, logger, project_name):
        self.project_name = project_name
        self.msg = logger

    def generate(self, subjects, basepath):
        """
        Generate Sphinx objects inventory version 2 at `basepath`/objects.inv.
        """
        path = os.path.join(basepath, 'objects.inv')
        self.msg('sphinx', 'Generating objects inventory at %s' % (path,))

        with self._openFileForWriting(path) as target:
            target.write(self._generateHeader())
            content = self._generateContent(subjects)
            target.write(zlib.compress(content))

    def _openFileForWriting(self, path):
        """
        Helper for testing.
        """
        return open(path, 'w')

    def _generateHeader(self):
        """
        Return header for project  with name.
        """
        version = [str(part) for part in self.version]
        return """# Sphinx inventory version 2
# Project: %s
# Version: %s
# The rest of this file is compressed with zlib.
""" % (self.project_name, '.'.join(version))

    def _generateContent(self, subjects):
        """
        Write inventory for all `subjects`.
        """
        content = []
        for obj in subjects:
            content.append(self._generateLine(obj))
            content.append(self._generateContent(obj.orderedcontents))

        return ''.join(content)

    def _generateLine(self, obj):
        """
        Return inventory line for object.

        name domain_name:type priority URL display_name

        Domain name is always: py
        Priority is always: -1
        Display name is always: -
        """
        full_name = obj.fullName()

        if obj.documentation_location == model.DocLocation.OWN_PAGE:
            url = obj.fullName() + '.html'
        else:
            url = obj.parent.fullName() + '.html#' + obj.name

        display = '-'
        if isinstance(obj, (model.Package, model.Module)):
            domainname = 'module'
        elif isinstance(obj, model.Class):
            domainname = 'class'
        elif isinstance(obj, model.Function):
            if obj.kind == 'Function':
                domainname = 'function'
            else:
                domainname = 'method'
        elif isinstance(obj, model.Attribute):
            domainname = 'attribute'
        else:
            domainname = 'obj'
            self.msg('sphinx', "Unknown type %r for %s." % (type(obj), full_name,))

        return '%s py:%s -1 %s %s\n' % (full_name, domainname, url, display)
