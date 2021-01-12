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


Releasing and publishing a new package
--------------------------------------

Publishing to PyPI is done via a GitHub Actions workflow that is triggered when a tag is pushed.

First commit the version update to master and wait for tests to pass.

You can push a tag by creating a `GitHub release <https://github.com/twisted/pydoctor/releases/new>`.

You can also create a tag on local branch then push it::

        git tag 1.2.3
        git push --tags


Design Notes
------------

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

It's extremely handy to be able to pickle a system in between each
step.

Finally, pydoctor should never crash, no matter what code you feed it
(this seems a basic idea for a documentation generator, but it's not
that universally applied, it seems).  Missing information is OK,
crashing out is not.  This probably isn't as true as it should be at
the moment.
