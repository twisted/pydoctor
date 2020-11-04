
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

.. Releasing a new package
   -----------------------

    Releasing a new version is done via GitHub Actions.
    First commit the version update to master and wait for tests to pass.
    Create a tag on local branch and then push it::

        git tag 1.2.3
        git push --tags
