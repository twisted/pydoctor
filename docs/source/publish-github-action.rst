:orphan:

Simple GitHub Action to publish API docs
----------------------------------------

Here is an example of a simple GitHub Action to automatically
generate your documentation with Pydoctor
and publish it to your default GitHub Pages website when there is a push on the ``main`` branch.

Just substitute `(projectname)` and `(packagedirectory)`
with the appropriate information.

::

    name: apidocs
    on:
      push:
        branches: [main]

    jobs:
      deploy:
        runs-on: ubuntu-latest

        steps:
        - uses: actions/checkout@master
        - name: Set up Python 3.12
          uses: actions/setup-python@v2
          with:
            python-version: 3.12

        - name: Install requirements for documentation generation
          run: |
            python -m pip install --upgrade pip setuptools wheel
            python -m pip install pydoctor

        - name: Generate API documentation with pydoctor
          run: |

            # Run pydoctor build
            pydoctor \
                --project-name=(projectname) \
                --project-url=https://github.com/$GITHUB_REPOSITORY \
                --html-viewsource-base=https://github.com/$GITHUB_REPOSITORY/tree/$GITHUB_SHA \
                --html-base-url=https://$GITHUB_REPOSITORY_OWNER.github.io/${GITHUB_REPOSITORY#*/} \
                --html-output=./apidocs \
                --docformat=restructuredtext \
                --intersphinx=https://docs.python.org/3/objects.inv \
                ./(packagedirectory)

        - name: Push API documentation to Github Pages
          uses: peaceiris/actions-gh-pages@v3
          with:
            github_token: ${{ secrets.GITHUB_TOKEN }}
            publish_dir: ./apidocs
            commit_message: "Generate API documentation"

.. note:: As mentioned in the ``actions-gh-pages`` `documentation`__, the first workflow run won't actually publish the documentation to GitHub Pages.
    GitHub Pages needs to be enabled afterwards in the repository settings, select ``gh-pages`` branch, then re-run your workflow.

    The website will be located at `https://(user).github.io/(repo)/`.

    __ https://github.com/peaceiris/actions-gh-pages
