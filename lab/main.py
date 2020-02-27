#!/usr/bin/env python
from docutils.core import publish_doctree
from docutils.frontend import OptionParser
from docutils.io import StringOutput
from sphinx.application import Sphinx
from sphinx.util import rst
from sphinx.util.docutils import sphinx_domains
from sphinx.writers.html import HTMLWriter

DOCSTRING = """
A dummy task to demonstrate the registry machinery.

The task receives the :class:`ExternalTask` instance and logs some information,
after which it completes the task.
"""


def write_html(env, builder, document) -> str:
    destination = StringOutput(encoding="utf-8")
    docwriter = HTMLWriter(builder)
    docsettings = OptionParser(
        defaults=env.settings, components=(docwriter,), read_config_files=True
    ).get_default_values()
    docsettings.compact_lists = True

    document.settings = docsettings

    docwriter.write(document, destination)
    docwriter.assemble_parts()
    return docwriter.parts["body"]


def main(builder_alias="html"):
    print("Rendering experiments...")

    app = Sphinx(".", "../doc/", "_build", ".doctrees", builder_alias,)

    builder = app.builder
    env = builder.env

    docname = "doc"
    env.prepare_settings(docname)
    with sphinx_domains(env), rst.default_role(docname, builder.config.default_role):
        document = publish_doctree(DOCSTRING, settings_overrides=env.settings)
        env.apply_post_transforms(document, docname)

    print("\nDoctree:")
    print(document)

    output = write_html(env, builder, document)
    print(f"\nHTML output:")
    print(output)


if __name__ == "__main__":
    main()
