====================================
Business Process Task Library (BPTL)
====================================

:Version: 0.7.30
:Source: https://github.com/GemeenteUtrecht/bptl
:Keywords: bpmn, camunda, external tasks, process engine, VNG, Common Ground
:PythonVersion: 3.8

|build-status| |black|

A webapplication to configure and run worker units to process tasks from external
engines. Currently it supports Camunda `external tasks`_ .

Developed by `Maykin Media B.V.`_ for Gemeente Utrecht.

.. toctree::
    :maxdepth: 3
    :caption: Contents

    introduction
    technical_requirements
    usage/index
    developers/index

.. |build-status| image:: https://travis-ci.org/GemeenteUtrecht/bptl.svg?branch=master
    :alt: Build status
    :target: https://travis-ci.org/GemeenteUtrecht/bptl

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. _external tasks: https://docs.camunda.org/manual/7.12/user-guide/process-engine/external-tasks/
.. _Maykin Media B.V.: https://www.maykinmedia.nl
