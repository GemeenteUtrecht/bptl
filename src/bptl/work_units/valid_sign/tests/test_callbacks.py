"""
Test the callback machinery from ValidSign.

Example callback:

.. code-block:: http

    POST https://webhook.site/b62b7cc0-4da5-4b0f-bbd5-880769f44d47 HTTP/1.1
    Host: webhook.site
    Accept-Encoding: gzip,deflate
    User-Agent:
    Authorization: Basic test-callback-key
    Content-Type: application/json; charset=utf-8

    {
      "@class": "com.silanis.esl.packages.event.ESLProcessEvent",
      "name": "PACKAGE_COMPLETE",
      "sessionUser": "30ba8506-9819-46aa-a22d-c0114ba34cd0",
      "packageId": "LWsUTvGgE4WpOvaQPT16idnxNj8=",
      "message": null,
      "documentId": null,
      "createdDate": "2020-08-21T14:12:34.544Z"
    }
"""
