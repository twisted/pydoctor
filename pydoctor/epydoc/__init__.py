# epydoc
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""

epydoc is an automatic Python reference documentation generator.
pydoctor uses parts of the epydoc source as a library.

Package Organization
====================

Docstring markup parsing is handled by the `markup` package.
See the submodule list for more information about the submodules
and subpackages.

:group Docstring Processing: markup
:group Miscellaneous: util, test

:author: `Edward Loper <edloper@gradient.cis.upenn.edu>`__
:requires: Python 2.3+
:version: 3.0.1
:see: `The epydoc webpage <http://epydoc.sourceforge.net>`__
:see: `The epytext markup language manual <http://epydoc.sourceforge.net/epytext.html>`__

:todo: Create a better default top_page than trees.html.
:todo: Fix trees.html to work when documenting non-top-levelmodules/packages
:todo: Implement @include
:todo: Optimize epytext
:todo: More doctests
:todo: When introspecting, limit how much introspection you do (eg, don't construct docs for imported modules' vars if it's not necessary)

:bug: UserDict.* is interpreted as imported .. why??

:license: IBM Open Source License
:copyright: |copy| 2006 Edward Loper

:newfield contributor: Contributor, Contributors (Alphabetical Order)
:contributor: `Glyph Lefkowitz  <mailto:glyph@twistedmatrix.com>`__
:contributor: `Edward Loper  <mailto:edloper@gradient.cis.upenn.edu>`__
:contributor: `Bruce Mitchener  <mailto:bruce@cubik.org>`__
:contributor: `Jeff O'Halloran  <mailto:jeff@ohalloran.ca>`__
:contributor: `Simon Pamies  <mailto:spamies@bipbap.de>`__
:contributor: `Christian Reis  <mailto:kiko@async.com.br>`__
:contributor: `Daniele Varrazzo  <mailto:daniele.varrazzo@gmail.com>`__
:contributor: `Jonathan Guyer <mailto:guyer@nist.gov>`__

.. |copy| unicode:: 0xA9 .. copyright sign
"""
__docformat__ = 'restructuredtext en'

__version__ = '3.0.1'
"""The version of epydoc"""

__author__ = 'Edward Loper <edloper@gradient.cis.upenn.edu>'
"""The primary author of eypdoc"""

__url__ = 'http://epydoc.sourceforge.net'
"""The URL for epydoc's homepage"""

__license__ = 'IBM Open Source License'
"""The license governing the use and distribution of epydoc"""

# Changes needed for docs:
#   - document the method for deciding what's public/private
#   - epytext: fields are defined slightly differently (@group)
#   - new fields
#   - document __extra_epydoc_fields__ and @newfield
#   - Add a faq?
#   - @type a,b,c: ...
#   - new command line option: --command-line-order

