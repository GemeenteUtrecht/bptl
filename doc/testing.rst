.. _testing:

=======
Testing
=======

This document covers the tools to run tests and how to use them.


Django tests
============

Run the project tests by executing::

    $ python src/manage.py test src --keepdb

To measure coverage, use ``coverage run``::

    $ coverage run src/manage.py test src --keepdb

It may be convenient to add some aliases::

    $ alias runtests='python src/manage.py test --keepdb'
    $ runtests src

and::

    $ alias cov_runtests='coverage run src/manage.py test --keepdb'
    $ cov_runtests src && chromium htmlcov/index.html


Jenkins
-------

Run ``./bin/jenkins_django.sh`` to execute the tests for ``develop`` and ``master``.
This script runs the tests with ``--keepdb``.

To run PR tests, run ``./bin/jenkins_django_pr.sh``. This script drops the test
database at the end, so it should be safe with different migrations between PR's.


SASS build - Jenkins
====================

There is a simple ``./bin/jenkins_sass.sh`` script that checks if the sass
compiles successfully.


Javascript tests
================

There are quite some options to run the Javascript tests. Karma is used as
test-runner, and you need to install it globally if you have never done so::

    $ sudo npm install -g karma

By default, the tests are run against PhantomJS and Chrome/Chromium. To run
the tests, execute::

    $ gulp test

If you want to target a single browser, you can run karma directly::

    $ karma start karma.conf.js --single-run --browsers=PhantomJS

Coverage reports can be found in ``build/reports/coverage``.

To trigger a test run on file change (source file or test file), run::

    $ karma start karma.conf.js --single-run=false --browsers=PhantomJS



