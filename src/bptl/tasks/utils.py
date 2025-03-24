import functools
import tempfile
import uuid

from docutils.core import publish_doctree
from docutils.frontend import OptionParser
from docutils.io import StringOutput
from sphinx.application import Sphinx
from sphinx.util import rst
from sphinx.util.docutils import sphinx_domains
from sphinx.writers.html import HTMLWriter

__all__ = ["render_docstring"]


def render_docstring(docstring: str) -> str:
    """
    Render a docstring to HTML with Sphinx.
    """
    document = _get_doctree(docstring)
    return _write_html(document)


@functools.lru_cache()
def _get_builder():
    _tmpdir = tempfile.mkdtemp()
    app = Sphinx(
        srcdir=".",
        confdir=None,
        outdir=_tmpdir,
        doctreedir=_tmpdir,
        buildername="html",
        confoverrides={
            "project": "Business Process Task Library",
            "extensions": ["sphinx.ext.autodoc"],
        },
        verbosity=0,
        status=None,
    )
    return app.builder


def _get_doctree(docstring: str):
    docname = "_docstring"
    builder = _get_builder()
    env = builder.env

    env.prepare_settings(docname)
    with sphinx_domains(env), rst.default_role(docname, builder.config.default_role):
        document = publish_doctree(docstring, settings_overrides=env.settings)
        env.apply_post_transforms(document, docname)

    return document


def _write_html(document) -> str:
    builder = _get_builder()

    destination = StringOutput(encoding="utf-8")
    docwriter = HTMLWriter(builder)
    docsettings = OptionParser(
        defaults=builder.env.settings, components=(docwriter,), read_config_files=True
    ).get_default_values()
    docsettings.compact_lists = True

    document.settings = docsettings

    docwriter.write(document, destination)
    docwriter.assemble_parts()
    return docwriter.parts["body"]


def get_worker_id() -> str:
    prefix = "bptl"
    guid = uuid.uuid4()
    return f"{prefix}-{guid}"
