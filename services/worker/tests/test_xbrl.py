from leadmachine.financial.xbrl import parse_xbrl


def test_parses_primary_period_only(xbrl_bytes) -> None:
    fin = parse_xbrl(xbrl_bytes)
    # 2023 figures, not the 2022 comparatives
    assert fin.gross_profit == 1_200_000
    assert fin.profit_loss == 350_000
    assert fin.equity == 900_000  # instant 2023-12-31, not 600_000 (2022)
    assert fin.assets == 1_500_000
    assert fin.employee_expense == 800_000
    assert fin.avg_employees == 4


def test_dimensional_revenue_is_ignored(xbrl_bytes) -> None:
    # Revenue only appears on a segment context -> treated as omitted
    fin = parse_xbrl(xbrl_bytes)
    assert fin.revenue is None


def test_empty_document_yields_blank_financials() -> None:
    doc = b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"></xbrli:xbrl>'
    fin = parse_xbrl(doc)
    assert fin.as_dict() == {}


def test_negative_sign_attribute() -> None:
    doc = (
        '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:fsa="http://xbrl.dcca.dk/fsa">'
        '<xbrli:context id="D"><xbrli:period>'
        "<xbrli:startDate>2023-01-01</xbrli:startDate>"
        "<xbrli:endDate>2023-12-31</xbrli:endDate></xbrli:period></xbrli:context>"
        '<fsa:ProfitLoss contextRef="D" sign="-">50000</fsa:ProfitLoss>'
        "</xbrli:xbrl>"
    ).encode()
    assert parse_xbrl(doc).profit_loss == -50_000
