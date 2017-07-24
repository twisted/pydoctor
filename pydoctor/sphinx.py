"""
Support for Sphinx compatibility.
"""
from __future__ import absolute_import
from __future__ import print_function

from six.moves.urllib.request import urlopen

import os
import zlib


class SphinxInventory(object):
    """
    Sphinx inventory handler.
    """

    version = (2, 0)

    def __init__(self, logger, project_name):
        self.project_name = project_name
        self.info = logger
        self._links = {}
        self.error = lambda where, message: logger(where, message, thresh=-1)

    def generate(self, subjects, basepath):
        """
        Generate Sphinx objects inventory version 2 at `basepath`/objects.inv.
        """
        path = os.path.join(basepath, 'objects.inv')
        self.info('sphinx', 'Generating objects inventory at %s' % (path,))

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
            if not obj.isVisible:
                continue
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
        # Avoid circular import.
        from pydoctor import model

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
            self.error(
                'sphinx', "Unknown type %r for %s." % (type(obj), full_name,))

        return '%s py:%s -1 %s %s\n' % (full_name, domainname, url, display)

    def update(self, url):
        """
        Update inventory from URL.
        """
        parts = url.rsplit('/', 1)
        if len(parts) != 2:
            self.error(
                'sphinx', 'Failed to get remote base url for %s' % (url,))
            return

        base_url = parts[0]

        data = self._getURL(url)

        if not data:
            self.error(
                'sphinx', 'Failed to get object inventory from %s' % (url, ))
            return

        payload = self._getPayload(base_url, data)
        self._links.update(self._parseInventory(base_url, payload))

    def _getURL(self, url):
        """
        Get content of URL.

        This is a helper for testing.
        """
        try:
            response = urlopen(url)
            return response.read()
        except:
            return None

    def _getPayload(self, base_url, data):
        """
        Parse inventory and return clear text payload without comments.
        """
        payload = ''
        while True:
            parts = data.split('\n', 1)
            if len(parts) != 2:
                payload = data
                break
            if not parts[0].startswith('#'):
                payload = data
                break
            data = parts[1]
        try:
            return zlib.decompress(payload)
        except:
            self.error(
                'sphinx',
                'Failed to uncompress inventory from %s' % (base_url,))
            return ''

    def _parseInventory(self, base_url, payload):
        """
        Parse clear text payload and return a dict with module to link mapping.
        """
        result = {}
        for line in payload.splitlines():
            parts = line.split(' ', 4)
            if len(parts) != 5:
                self.error(
                    'sphinx',
                    'Failed to parse line "%s" for %s' % (line, base_url),
                    )
                continue
            result[parts[0]] = (base_url, parts[3])
        return result

    def getLink(self, name):
        """
        Return link for `name` or None if no link is found.
        """
        base_url, relative_link = self._links.get(name, (None, None))
        if not relative_link:
            return None

        # For links ending with $, replace it with full name.
        if relative_link.endswith('$'):
            relative_link = relative_link[:-1] + name

        return '%s/%s' % (base_url, relative_link)
