"""
The credentials app acts as a credential store for applications using BPTL.

BPTL stores the data for every application to be able to generate credentials to be
used with the external services, for example:

.. code-block:: yaml

    app FOO:
      service X: client ID + secret
      service Y: client ID + secret
      service Z: API key
    app BAR:
      service A: API key
      service X: client ID + secret

The process definition or end-user application is responsible for setting the bptlAppId
variable, which allows BPTL to infer the correct credentials for the services that are
used.
"""
