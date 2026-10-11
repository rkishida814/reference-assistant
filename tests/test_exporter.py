import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.exporter import build_runs_for_entry

def test_build_runs():
    entry = {
        "authors": [
            {"first": "John", "last": "Smith"},
            {"first": "Jane", "last": "Doe"}
        ],
        "title": "A Great Paper",
        "journal": "Journal of Science",
        "vol": "10",
        "page1": "100",
        "page2": "110",
        "year": "2023"
    }
    
    config = {
        "initials": True,
        "author_format": "Last, First",
        "ordering": "Vol, Page, Year",
        "delims": {
            "author_author": ",",
            "author_title": ".",
            "title_journal": ".",
            "journal_vol": ",",
            "vol_page": ":",
            "page_year": " "
        },
        "bold": {"Title": True},
        "year_parens": True
    }
    
    runs = build_runs_for_entry(entry, config)
    
    # Check that authors are "Smith, J." and "Doe, J."
    assert any(r["text"] == "Smith, J." for r in runs)
    assert any(r["text"] == "Doe, J." for r in runs)
    
    # Check that title is bold
    title_run = next(r for r in runs if "A Great Paper" in r["text"])
    assert title_run["bold"] is True
    assert title_run["italic"] is False
    
    # Check year parens
    assert any(r["text"] == "(2023)" for r in runs)
    
    # We can also join all text and check the layout
    full_text = "".join(r["text"] for r in runs)
    assert "Smith, J., Doe, J.. A Great Paper. Journal of Science, 10: 100-110 (2023)" in full_text
