ValidSign
=========

Configuration
-------------

BPTL needs to receive callbacks from ValidSign.

1. Navigate to the admin > **ValidSign configuration**
2. There is a generated authentication key, and the callback URL you will need in
   ValidSign
3. Navigate to the ValidSign `dashboard`_. From there, navigate to the **admin**
4. Click **Integration**
5. Enter the callback URL and authentication key in the relevant fields
6. Select the **Transaction completed** event

You also need to configure the ValidSign API key with the service in BPTL:

1. See the `integrator guide`_ (page 10) on where you can find your API key
2. In BPTL, navigate to the admin > **Services**
3. Add a service, with the following fields:

    - Label: *ValidSign* (for example)
    - Type: ORC (Overige)
    - API root URL: ``https://try.validsign.nl/`` (sandbox) or
      ``https://my.validsign.nl/`` (production)
    - Authorization type: API key
    - Header key: ``Authorization``
    - Header value: ``Basic <api key>``
    - OAS: ``https://apidocs.validsign.nl/validsign_openapi.yaml``

Connecting to a topic
---------------------

When you connect a topic name and the valid sign task(s), you must add the ValidSign
service with the alias ``ValidSignAPI``.

Integration
-----------

BPTL can automate ValidSign package/transaction creation and configuration.

The :class:`bptl.work_units.valid_sign.tasks.CreateValidSignPackageTask` takes
documents and signer information as input, and performs the following actions:

1. A package is created. The signers specified in the task process variables are
   included in the package when it is created.
2. The documents are added to the package. All documents specified in the process
   variables are retrieved from their respective API. For each document, an 'approval'
   is created. This is a field where a signer will be able to sign. The approval is a
   field of dimensions 50x150 (px?) placed by the bottom left corner of the first
   occurrence of the string ``Capture Signature``.
3. The package status is changed to SENT. This automatically sends an email to the
   signers with links to where they can sign the documents.
4. Once everyone has signed the package, ValidSign sends a callback to BPTL
5. BPTL processes the callback, and if configured, sends a BPMN message back to the
   process instance (Camunda only).

.. _ValidSign: https://www.validsign.nl/
.. _dashboard: https://my.validsign.nl/a/dashboard
.. _integrator guide: https://apidocs.validsign.nl/validsign_integrator_guide.pdf
