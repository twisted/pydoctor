Reproducible builds
====================

Pydoctor supports the `SOURCE_DATE_EPOCH` environment variable and a
`--buildtime` option to allow reproducible output when building
documentation.

What SOURCE_DATE_EPOCH does
---------------------------

`SOURCE_DATE_EPOCH` is a standard used by many projects and build
systems to make builds reproducible. It should contain an integer
Unix timestamp (seconds since the epoch). When `SOURCE_DATE_EPOCH` is
set in the environment before running `pydoctor`, pydoctor will use
that time (in UTC) as the build time instead of the current time.

Example:

.. code-block:: bash

    export SOURCE_DATE_EPOCH=1600000000
    pydoctor --html-output=docs/api src/mylib

Using the `--buildtime` option
------------------------------

If you prefer to set the build time on the command line you can use
`--buildtime` with the format ``YYYY-mm-dd HH:MM:SS``. For example::

    pydoctor --buildtime="2020-09-13 12:26:40" --html-output=docs/api src/mylib

To suppress printing or embedding the build time, pass one of the
following values to `--buildtime`: ``no``, ``false``, ``off`` or
``0``. For example::

    pydoctor --buildtime=no --html-output=docs/api src/mylib

Details
-------

- The exact format accepted by `--buildtime` is ``%Y-%m-%d %H:%M:%S``.
- When both `SOURCE_DATE_EPOCH` and `--buildtime` are provided, the
  environment variable takes precedence (this follows common
  conventions for reproducible build environments).
- When a build time is set (and not suppressed), it is used in
  templates that render the generated documentation (for example the
  generated footer).

References
----------

- `SOURCE_DATE_EPOCH specification <https://reproducible-builds.org/specs/source-date-epoch/>`_
