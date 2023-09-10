Contribute
==========


What can you do
---------------

If you like the project and think you could help with making it better, there are many ways you can do it:

- Create a new issue for new feature proposal or a bug
- Triage old issues that needs a refresh
- Implement existing issues (there are quite some of them, choose whatever you like)
- Help with improving the documentation (We still have work to do!)
- Spread a word about the project to your colleagues, friends, blogs or any other channels
- Any other things you could imagine

Any contribution would be of great help and I will highly appreciate it! If you have any questions, please create a new issue.


Pre-commit checks
-----------------

Make sure all the tests pass and the code pass the coding standard checks::

    tox -p all

That should be the minimum check to run on your local system.
A pull request will trigger more tests and most probably there is a tox
environment dedicated to that extra test.


Review process and requirements
-------------------------------

- Code changes and code added should have tests: untested code is buggy code. Except special cases, overall test coverage should be increased.
- If your pull request is a work in progress, please mark it as draft such that reviewers do not loose time on a PR that is not ready yet.
- All code changes must be reviewed by at least one person who is not an author of the code being added. 
  This helps prevent bugs from slipping through the net and gives another source for improvements.
  If the author of the PR is one of the core developers of pydoctor* and no one has reviewed their PR after 9 calendar days, they can review the code changes themselves and proceed with next steps. 
- When one is done with the review, always say what the next step should be: for example, if the author is a core developer, can they merge the PR after making a few minor fixes? 
  If your review feedback is more substantial, should they ask for another review?


\* A core developer is anyone with a write access to the repository that have an intimate knowledge of pydoctor internals, or, 
alternatively the specific aspect in which they are contributing to (i.e. Sphinx docs, setup, pytest, etc.). 

Read more about reviewing:

- `How to be a good reviewer <https://twistedmatrix.com/trac/wiki/ReviewProcess#Howtobeagoodreviewer>`_.
- `Leave well enough alone <https://mail.python.org/archives/list/twisted@python.org/thread/53LZTRNRYLZJ4QLEF3YPAE53CWSL6LXD/>`_.

Releasing and publishing a new package
--------------------------------------

Publishing to PyPI is done via a GitHub Actions workflow that is triggered when a tag is pushed. Version is configured in the ``setup.cfg``. 

The following process ensures correct version management: 

 - Create a branch: name it by the name of the new major ``pydoctor`` version, i.e. ``21.9.x``, re-use that same branch for bug-fixes.
 - On the branch, update the version and release notes.
 - Update the HTML templates version (meta tag ``pydoctor-template-version``) when there is a change from a version to another. 
   For instance, check the diff of the HTML templates since version ``21.9.1`` with the following git command::

       git diff 21.9.1 pydoctor/themes/*/*.html
       
   .. note:: The HTML template version can also be updated in the PR in which the actual HTML template change is done.
 - Create a PR for that branch, wait for tests to pass and get an approval.
 - Create a tag based on the ``HEAD`` of the release branch, name it by the full version number of the ``pydoctor`` version, i.e. ``21.9.1``, this will trigger the release. For instance::

        git tag 21.9.1
        git push --tags

 - Update the version on the branch and append ``.dev0`` to the current version number. In this way, stable versions only exist for a brief period of time (if someone tries to do a ``pip install`` from the git source, they will get a ``.dev0`` version instead of a misleading stable version number.
 - Update the README file and add an empty placeholder for unreleased changes.
 - Merge the branch

Updating pydoctor for Linux distributions
-----------------------------------------

The information below covers Debian and its derivative distributions.
The same principles should be applied for Fedora, Arch, Alpine or any other
Linux distribution.

There shouldn't be any additional steps needed to get pydoctor updated in
Debian (and its downstream distributions like Ubuntu).
As pydoctor is a Python based package the `Debian Python Team
<https://wiki.debian.org/Teams/PythonTeam>`_ is usually taking care about
updating pydoctor in Debian. The DPT is available through the team mailing
list (``Debian Python List <debian-python@lists.debian.org>``) there everyone
can get in contact by email. If you just want to ask something quickly please
use this option.

Debian uses a separate, non GitHub, BTS (Bug Tracking System) to keep track
of issues. The package maintainers like to use this system in case of more
specific requests or problems. The preferred and suggested way to open up
new issues within the Debian BTS is to use the tool `reportbug
<https://wiki.debian.org/reportbug>`_ that will do some additional magic
while collecting the data for the bug report like collecting installed
packages and there versions. ``reportbug`` should be used if you are working
on a Debian based system.

But you can also use any email client to open up bug reports on the Debian
BTS by simply writing an email to the address ``submit@bugs.debian.org``.

If you want to help to keep the pydoctor package up to date in Debian the
DPT is happy to take your help! Helping out can be done in various ways.

* Keep an eye on `reported issues <https://bugs.debian.org/cgi-bin/pkgreport.cgi?repeatmerged=yes&src=pydoctor>`_
  for the pydoctor package and forward them upstream if needed.
* Have also a look at cross connected packages and possible build issues
  there regarding the build dependency onpydoctor. These packages are mostly
  `twisted <https://tracker.debian.org/pkg/twisted>`_ or
  `git-buildpackage <https://tracker.debian.org/pkg/git-buildpackage>`_.
* Ideally taking over some maintainer responsibilities for pydoctor in Debian.

pydoctor and new depending packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It might happen that pydoctor is requiring new additional Python libraries
due to new wanted features or to enhance the internal test suite.

Such new packages shouldn't get vendored. They need to be packaged in
Debian. Best is to get in contact with the DPT to talk about about new
requirements and the best way to get things done.

Profiling pydoctor with austin and speedscope
---------------------------------------------

1. Install austin (https://github.com/P403n1x87/austin)
2. Install austin-python (https://pypi.org/project/austin-python/)
3. Run program under austin 

   .. code::

      $ sudo austin -i 1ms -C -o pydoctor.austin pydoctor <pydoctor args>

4. Convert .austin to .speedscope (austin2speedscope comes from austin-python)

   .. code::
  
    $ austin2speedscope pydoctor.austin pydoctor.speedscope


5. Open https://speedscope.app and load pydoctor.speedscope into it.

Note on sampling interval
~~~~~~~~~~~~~~~~~~~~~~~~~

On our large repo I turn down the sampling interval from 100us to 1ms to make 
the resulting ``.speedscope`` file a manageable size (15MB instead of 158MB which is too large to put into a gist.)

Author Design Notes
-------------------

I guess I've always been interested in more-or-less static analysis of
Python code and have over time developed some fairly strong opinions
on the Right Way\ |trade| to do it.

The first of these is that pydoctor works on an entire *system* of
packages and modules, not just a ``.py`` file at a time.

The second, and this only struck me with full force as I have written
pydoctor, is that it's much the best approach to proceed
incrementally, and outside-in.  First, you scan the directory
structure to and compute the package/module structure, then parse each
module, then do some analysis on what you've found, then generate
html.

Finally, pydoctor should never crash, no matter what code you feed it
(this seems a basic idea for a documentation generator, but it's not
that universally applied, it seems).  Missing information is OK,
crashing out is not.  This probably isn't as true as it should be at
the moment.
