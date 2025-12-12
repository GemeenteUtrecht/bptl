from types import SimpleNamespace

import pytest

from bptl.openklant.exceptions import OpenKlantEmailException
from bptl.work_units.open_klant.utils import (
    build_email_context,
    get_actor_email_from_interne_taak,
    get_organisatie_eenheid_email,
)


def test_get_organisatie_eenheid_email_no_results_returns_empty_and_logs(
    monkeypatch, caplog
):
    caplog.set_level("WARNING")
    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_paginated_results",
        lambda *a, **k: [],
    )

    out = get_organisatie_eenheid_email("ID123", obj_client=SimpleNamespace())
    assert out == ""
    assert any("Could not find an object" in r.message for r in caplog.records)


def test_get_organisatie_eenheid_email_one_result_returns_email(monkeypatch):
    results = [{"record": {"data": {"email": "x@example.com"}}}]
    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_paginated_results",
        lambda *a, **k: results,
    )

    out = get_organisatie_eenheid_email("ID123", obj_client=SimpleNamespace())
    assert out == "x@example.com"


def test_get_organisatie_eenheid_email_multiple_results_returns_empty(
    monkeypatch, caplog
):
    caplog.set_level("WARNING")
    results = [
        {"record": {"data": {"email": "a@example.com"}}},
        {"record": {"data": {"email": "b@example.com"}}},
    ]
    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_paginated_results",
        lambda *a, **k: results,
    )

    out = get_organisatie_eenheid_email("ID123", obj_client=SimpleNamespace())
    assert out == ""
    assert any("Found more than 1 result" in r.message for r in caplog.records)


def test_get_actor_email_from_interne_taak_no_actor_urls_returns_empty():
    interne_taak = {"toegewezenAanActoren": [], "uuid": "U1"}
    assert (
        get_actor_email_from_interne_taak(interne_taak, client=SimpleNamespace()) == ""
    )


def test_get_actor_email_from_interne_taak_no_active_actors_raises(monkeypatch):
    interne_taak = {
        "toegewezenAanActoren": [{"url": "http://actor/1"}],
        "uuid": "U2",
    }

    fake_client = SimpleNamespace()
    fake_client.retrieve = lambda resource, url: {"indicatieActief": False}

    class FakeParallel:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, items):
            return [fn(i) for i in items]

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.parallel", lambda: FakeParallel()
    )

    with pytest.raises(OpenKlantEmailException):
        get_actor_email_from_interne_taak(interne_taak, client=fake_client)


def test_get_actor_email_from_interne_taak_medewerker_with_email_returns_email(
    monkeypatch,
):
    interne_taak = {
        "toegewezenAanActoren": [{"url": "http://actor/1"}],
        "uuid": "U3",
    }

    actor = {
        "indicatieActief": True,
        "soortActor": "medewerker",
        "actoridentificator": {
            "codeSoortObjectId": "email",
            "objectId": "ok@example.com",
        },
    }

    fake_client = SimpleNamespace()
    fake_client.retrieve = lambda resource, url: actor

    class FakeParallel:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, items):
            return [fn(i) for i in items]

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.parallel", lambda: FakeParallel()
    )

    out = get_actor_email_from_interne_taak(interne_taak, client=fake_client)
    assert out == "ok@example.com"


def test_get_actor_email_from_interne_taak_medewerker_multiple_emails_raises(
    monkeypatch,
):
    interne_taak = {
        "toegewezenAanActoren": [{"url": "http://a/1"}, {"url": "http://a/2"}],
        "uuid": "U4",
    }

    actor1 = {
        "indicatieActief": True,
        "soortActor": "medewerker",
        "actoridentificator": {
            "codeSoortObjectId": "email",
            "objectId": "a@example.com",
        },
    }
    actor2 = {
        "indicatieActief": True,
        "soortActor": "medewerker",
        "actoridentificator": {
            "codeSoortObjectId": "email",
            "objectId": "b@example.com",
        },
    }

    fake_client = SimpleNamespace()
    fake_client.retrieve = lambda resource, url: (
        actor1 if url.endswith("/1") else actor2
    )

    class FakeParallel:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, items):
            return [fn(i) for i in items]

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.parallel", lambda: FakeParallel()
    )

    with pytest.raises(OpenKlantEmailException):
        get_actor_email_from_interne_taak(interne_taak, client=fake_client)


def test_build_email_context_without_klantcontact_subject_is_nb(monkeypatch):
    task = SimpleNamespace(variables={})

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_openklant_client",
        lambda: SimpleNamespace(),
    )

    ctx = build_email_context(task, client=SimpleNamespace())

    assert ctx["subject"] == "KISS contactverzoek N.B."
    assert ctx["klantcontact"] is None


def test_build_email_context_with_klantcontact(monkeypatch):
    task = SimpleNamespace(
        variables={
            "aanleidinggevendKlantcontact": {"url": "http://kc/1"},
            "gevraagdeHandeling": "H",
            "toelichting": "T",
        }
    )

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_openklant_client",
        lambda: SimpleNamespace(),
    )

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_klantcontact_for_interne_taak",
        lambda url, client=None: {
            "onderwerp": "Onderwerp X",
            "hadBetrokkenen": [{"url": "http://b/1"}, {"url": "http://b/2"}],
        },
    )

    def fake_details(url, client=None):
        if url.endswith("/1"):
            return ("Jan", "jan@example.com", "0611111111")
        return ("Piet", "N.B.", "0622222222")

    monkeypatch.setattr(
        "bptl.work_units.open_klant.utils.get_details_betrokkene", fake_details
    )

    ctx = build_email_context(task, client=SimpleNamespace())

    assert ctx["naam"] == "Jan, Piet"
    assert ctx["email"] == "jan@example.com"
    assert ctx["telefoonnummer"] == "0611111111, 0622222222"
    assert ctx["onderwerp"] == "Onderwerp X"
    assert ctx["subject"] == "KISS contactverzoek jan@example.com"
