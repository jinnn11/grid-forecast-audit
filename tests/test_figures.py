from pathlib import Path

import pandas as pd
import pytest

from grid_audit import figures


def test_national_by_year_writes_png_and_csv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(figures, "FIGURES_DIR", tmp_path)
    years = pd.Index([2016, 2017, 2018], name="year")
    lines = pd.DataFrame(
        {"As published": [3.5, 3.25, 4.0], "All corrections": [3.5, 3.0, 3.125]}, index=years
    )
    figures.national_by_year(lines, "Trend 2016–2018: made up.")
    assert (tmp_path / "national_by_year.png").stat().st_size > 0
    # The CSV holds the plotted values unchanged, at four decimals: 3.125 -> 3.1250.
    text = (tmp_path / "national_by_year.csv").read_text().splitlines()
    assert text == [
        "year,As published,All corrections",
        "2016,3.5000,3.5000",
        "2017,3.2500,3.0000",
        "2018,4.0000,3.1250",
    ]


def test_national_by_year_has_two_colours() -> None:
    # Two categorical slots: a third line would need a colour the palette does not have.
    lines = pd.DataFrame({"a": [1.0], "b": [1.0], "c": [1.0]}, index=[2016])
    with pytest.raises(ValueError, match="at most 2"):
        figures.national_by_year(lines, "")
