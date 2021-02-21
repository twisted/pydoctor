:orphan:

Simple GitHub Action to publish API docs
----------------------------------------

Here is an example of a simple GitHub Action to automatically 
generate your documentation with Pydoctor
and publish it to your default GitHub Pages website. 

Just substitute `(projectname)` and `(packagedirectory)` 
with the appropriate information. 

::

    name: apidocs
    on:
    - push

    jobs:
      deploy:
        runs-on: ubuntu-latest

        steps:
        - uses: actions/checkout@master
        - name: Set up Python 3.8
          uses: actions/setup-python@v2
          with:
            python-version: 3.8

        - name: Install package
          run: |
            python -m pip install --upgrade pip setuptools wheel
            python -m pip install .
            python -m pip install pydoctor

        - name: Generate documentation with pydoctor
          run: |

            # Run pydoctor build
            pydoctor \
                --project-name=(projectname) \
                --project-url=https://github.com/$GITHUB_REPOSITORY \
                --html-viewsource-base=https://github.com/$GITHUB_REPOSITORY/tree/$GITHUB_SHA \
                --make-html \
                --html-output=./apidocs \
                --project-base-dir="$(pwd)" \
                --docformat=restructuredtext \
                --intersphinx=https://docs.python.org/3/objects.inv \
                ./(packagedirectory)

        - name: Publish pydoctor documentation to the gh-pages branch
          uses: peaceiris/actions-gh-pages@v3
          with:
            github_token: ${{ secrets.GITHUB_TOKEN }}
            publish_dir: ./apidocs
            commit_message: "Generate pydoctor documentation"

.. note:: As mentioned in the ``actions-gh-pages`` `documentation`__, the first workflow run won't actually publish the documentation to GitHub Pages.
    GitHub Pages needs to be enabled afterwards in the repository settings, select ``gh-pages`` branch, then re-run your workflow.

    The website will be located at `https://(user).github.io/(repo)/`.

    __ https://github.com/peaceiris/actions-gh-pages
