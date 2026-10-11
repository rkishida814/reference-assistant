import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.metadata_fetcher import extract_doi

def test_extract_doi():
    # Valid extractions
    assert extract_doi("https://doi.org/10.1038/s41586-020-2649-2") == "10.1038/s41586-020-2649-2"
    assert extract_doi("10.1038/s41586-020-2649-2") == "10.1038/s41586-020-2649-2"
    assert extract_doi("Some text DOI: 10.1109/CVPR42600.2020.00018 and more text") == "10.1109/CVPR42600.2020.00018"
    assert extract_doi("http://dx.doi.org/10.1002/andp.19053221004") == "10.1002/andp.19053221004"
    assert extract_doi("doi:10.1016/j.jcp.2018.11.006") == "10.1016/j.jcp.2018.11.006"

def test_extract_doi_invalid():
    assert extract_doi("https://github.com/abc/def") is None
    assert extract_doi("Just a normal sentence.") is None
