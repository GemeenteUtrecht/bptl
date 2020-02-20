====================================
Business Process Task Library (BPTL)
====================================

:Version: 0.1.0
:Source: https://github.com/GemeenteUtrecht/bptl
:Keywords: bpmn, camunda, external tasks, process engine, VNG, Common Ground
:PythonVersion: 3.8

|build-status| |black| |docs|

A webapplication to configure and run workers to process external tasks of business
process engines. Currently BPTL supports Camunda `external tasks`_ .

Developed by `Maykin Media B.V.`_ for Gemeente Utrecht.

Introduction
============

`Common Ground`_ zet in op een nieuwe, moderne gezamenlijke informatievoorziening. In
het 5-lagen model van Common Ground worden gegevens gescheiden van Interactie en proces,
waarbij gegevens via Services/APIs ontsloten worden.

BP Task Library zet hierbij in op de Integratielaag. Vaak leiden stappen in een proces
(wat leeft in een proces-engine zoals Camunda) tot bepaalde taken die uitgevoerd dienen
te worden tegen deze specifieke services/APIs.

In eerste instantie focust BP Task Library op de integratie met de
`API's voor zaakgericht werken`_ - stappen in het bedrijfsproces leiden tot het aanmaken
en bijwerken van Zaken, waarbij generieke bouwstenen opnieuw gebruikt kunnen worden
voor verschillende processen.


Documentation
=============

See ``INSTALL.rst`` for installation instructions, available settings and
commands.


References
==========

* `Issues <https://github.com/GemeenteUtrecht/bptl/issues>`_
* `Code <https://github.com/GemeenteUtrecht/bptl>`_

.. |build-status| image:: https://travis-ci.org/GemeenteUtrecht/bptl.svg?branch=master
    :alt: Build status
    :target: https://travis-ci.org/GemeenteUtrecht/bptl

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |docs| image:: https://readthedocs.org/projects/business-process-task-library/badge/?version=latest
    :target: https://business-process-task-library.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. _Common Ground: https://commonground.nl/
.. _external tasks: https://docs.camunda.org/manual/7.12/user-guide/process-engine/external-tasks/
.. _Maykin Media B.V.: https://www.maykinmedia.nl
.. _API's voor zaakgericht werken: https://github.com/VNG-Realisatie/gemma-zaken
