import subprocess


def test_build_docs(tmpdir):
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    subprocess.check_call(
        ["sphinx-build", "-W", "-bhtml", "-d", str(doctrees), ".", str(htmldir)],
    )
