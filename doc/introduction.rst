.. _introduction:

Introduction
============

`Common Ground`_ zet in op een nieuwe, moderne gezamenlijke informatievoorziening. In
het 5-lagen model van Common Ground worden gegevens gescheiden van Interactie en proces,
waarbij gegevens via Services/APIs ontsloten worden.

BPTL zet hierbij in op de Integratielaag. Vaak leiden stappen in een proces
(wat leeft in een proces-engine zoals Camunda) tot bepaalde taken die uitgevoerd dienen
te worden tegen deze specifieke services/APIs.

In eerste instantie focust BPTL op de integratie met de
`API's voor zaakgericht werken`_ - stappen in het Camunda proces leiden tot het aanmaken
en bijwerken van Zaken, waarbij generieke bouwstenen opnieuw gebruikt kunnen worden
voor verschillende processen.

Uitbreiding met nieuwe (typen) van taken wordt eenvoudig, en het invullen van de
procestaken met Camunda is technologie-onafhankelijk door het gebruik van External Tasks.

Zie :ref:`architecture` (EN) voor een overzicht van de architectuur.

.. _Common Ground: https://commonground.nl/
.. _API's voor zaakgericht werken: https://github.com/VNG-Realisatie/gemma-zaken
