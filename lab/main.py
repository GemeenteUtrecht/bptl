#!/usr/bin/env python

from sphinx.application import Sphinx


def main(builder="html"):
    print("Rendering experiments...")

    app = Sphinx(
        ".",
        "../doc/",
        "_build",
        ".doctrees",
        builder,
        confoverrides={"master_doc": "doc",},
    )

    app.build(force_all=False, filenames=["doc.rst"])


if __name__ == "__main__":
    main()
