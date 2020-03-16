import requests_mock


def mock_relations(m, brp_url, bsn, parents=None, children=None):
    parents = [{"burgerservicenummer": p} for p in parents] if parents else []
    children = [{"burgerservicenummer": c} for c in children] if children else []
    url = f"{brp_url}ingeschrevenpersonen/{bsn}?expand=kinderen.burgerservicenummer,ouders.burgerservicenummer"
    data = {
        "burgerservicenummer": bsn,
        "_embedded": {"ouders": parents, "kinderen": children},
    }
    m.get(url, json=data)


def mock_family(m: requests_mock.Mocker, brp_url: str):
    # level 1
    mock_relations(m, brp_url, "999990676", children=["999993392", "999991978"])

    # level 2
    mock_relations(
        m, brp_url, "999993392", parents=["999990676"], children=["999992223"]
    )
    mock_relations(
        m, brp_url, "999991978", parents=["999990676"], children=["999993333"]
    )

    # level 3
    mock_relations(
        m, brp_url, "999992223", parents=["999993392"], children=["999994177"]
    )
    mock_relations(m, brp_url, "999993333", parents=["999991978"])
    mock_relations(m, brp_url, "999991929", children=["999995224"])

    # level 4
    mock_relations(
        m, brp_url, "999994177", parents=["999992223"], children=["999992612"]
    )
    mock_relations(
        m, brp_url, "999995224", parents=["999991929"], children=["999992612"]
    )

    # level 5
    mock_relations(m, brp_url, "999992612", parents=["999994177", "999995224"])
