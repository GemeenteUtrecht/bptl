#!/usr/bin/env python
from docutils.core import publish_doctree
from sphinx.application import Sphinx
from sphinx.util import rst
from sphinx.util.docutils import sphinx_domains

DOCSTRING = """
A dummy task to demonstrate the registry machinery.

The task receives the :class:`ExternalTask` instance and logs some information,
after which it completes the task.
"""


def main(builder_alias="html"):
    print("Rendering experiments...")

    app = Sphinx(".", "../doc/", "_build", ".doctrees", builder_alias,)

    builder = app.builder
    env = builder.env

    docname = "doc"
    env.prepare_settings(docname)
    with sphinx_domains(env), rst.default_role(docname, builder.config.default_role):
        document = publish_doctree(DOCSTRING, settings_overrides=env.settings)

    print(document)


if __name__ == "__main__":
    main()
