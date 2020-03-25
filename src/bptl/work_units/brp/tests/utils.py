import requests_mock

NAMES = {
    "JANE": "999990676",
    "JILL": "999993392",
    "RICK": "999991978",
    "MARY": "999992223",
    "JOHN": "999993333",
    "LISA": "999994177",
    "KATE": "999991929",
    "JACK": "999995224",
    "BART": "999992612",
}


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
    """
    create family with following structure:
                JANE
                 |
              ---+---
             |      |
           JILL   RICK
            |       |
    KATE   MARY   JOHN
     |      |
    JACK - LISA
         |
        BART
    """

    # level 0
    mock_relations(m, brp_url, NAMES["JANE"], children=[NAMES["JILL"], NAMES["RICK"]])

    # level 1
    mock_relations(
        m, brp_url, NAMES["JILL"], parents=[NAMES["JANE"]], children=[NAMES["MARY"]]
    )
    mock_relations(
        m, brp_url, NAMES["RICK"], parents=[NAMES["JANE"]], children=[NAMES["JOHN"]]
    )

    # level 2
    mock_relations(
        m, brp_url, NAMES["MARY"], parents=[NAMES["JILL"]], children=[NAMES["LISA"]]
    )
    mock_relations(m, brp_url, NAMES["JOHN"], parents=[NAMES["RICK"]])
    mock_relations(m, brp_url, NAMES["KATE"], children=[NAMES["JACK"]])

    # level 3
    mock_relations(
        m, brp_url, NAMES["LISA"], parents=[NAMES["MARY"]], children=[NAMES["BART"]]
    )
    mock_relations(
        m, brp_url, NAMES["JACK"], parents=[NAMES["KATE"]], children=[NAMES["BART"]]
    )

    # level 4
    mock_relations(m, brp_url, NAMES["BART"], parents=[NAMES["LISA"], NAMES["JACK"]])
