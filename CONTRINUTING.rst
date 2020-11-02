
Releasing a new package
-----------------------

Releasing a new version is done via Travis-CI.
First commit the version update to master and wait for tests to pass.
Create a tag on local branch and then push it::

    git tag 1.2.3
    git push --tags
