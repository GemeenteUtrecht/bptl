==============
Camunda Worker
==============

:Version: 0.1.0
:Source: https://github.com/GemeenteUtrecht/camunda-worker
:Keywords: bpmn, camunda, external tasks, process engine, VNG, Common Ground
:PythonVersion: 3.8

|build-status| |black|

A webapplication to configure and run workers to process Camunda `external tasks`_.

Developed by `Maykin Media B.V.`_ for Gemeente Utrecht.

Introduction
============

`Common Ground`_ zet in op een nieuwe, moderne gezamenlijke informatievoorziening. In
het 5-lagen model van Common Ground worden gegevens gescheiden van Interactie en proces,
waarbij gegevens via Services/APIs ontsloten worden.

Camunda Worker zet hierbij in op de Integratielaag. Vaak leiden stappen in een proces
(wat leeft in een proces-engine zoals Camunda) tot bepaalde taken die uitgevoerd dienen
te worden tegen deze specifieke services/APIs.

In eerste instantie focust Camunda Worker op de integratie met de
`API's voor zaakgericht werken`_ - stappen in het Camunda proces leiden tot het aanmaken
en bijwerken van Zaken, waarbij generieke bouwstenen opnieuw gebruikt kunnen worden
voor verschillende processen.

Uitbreiding met nieuwe (typen) van taken wordt eenvoudig, en het invullen van de
procestaken met Camunda is technologie-onafhankelijk door het gebruik van External Tasks.

Documentation
=============

See ``INSTALL.rst`` for installation instructions, available settings and
commands.


References
==========

* `Issues <https://github.com/GemeenteUtrecht/camunda-worker/issues>`_
* `Code <https://github.com/GemeenteUtrecht/camunda-worker>`_

.. |build-status| image:: https://travis-ci.org/GemeenteUtrecht/camunda-worker.svg?branch=master
    :alt: Build status
    :target: https://travis-ci.org/GemeenteUtrecht/camunda-worker

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. _Common Ground: https://commonground.nl/
.. _external tasks: https://docs.camunda.org/manual/7.12/user-guide/process-engine/external-tasks/
.. _Maykin Media B.V.: https://www.maykinmedia.nl
.. _API's voor zaakgericht werken: https://github.com/VNG-Realisatie/gemma-zaken
