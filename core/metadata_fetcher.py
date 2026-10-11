import re
import requests

DOI_REGEX = re.compile(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', re.IGNORECASE)

def extract_doi(text: str) -> str:
    """Extracts a DOI from a URL or raw text."""
    match = DOI_REGEX.search(text)
    if match:
        return match.group(1).rstrip('/')
    return None

KNOWN_ABBREVIATIONS = {
    "international journal of molecular sciences": "Int. J. Mol. Sci.",
    "international journal of molecular science": "Int. J. Mol. Sci.",
}

def resolve_short_journal(journal: str, crossref_short: str) -> str:
    if journal.lower() in KNOWN_ABBREVIATIONS:
        return KNOWN_ABBREVIATIONS[journal.lower()]
    if crossref_short:
        return crossref_short
    return journal

def fetch_metadata(input_text: str) -> dict:
    """
    Given a URL, DOI, or raw text, attempts to find the DOI, fetch metadata from Crossref,
    and returns a structured dictionary.
    """
    doi = extract_doi(input_text)
    if not doi:
        raise ValueError("Could not extract a valid DOI from the input.")
        
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "ReferenceApp/1.0 (mailto:kishida@example.com) based on Crossref guidelines"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"Crossref API returned status code {response.status_code}")
        
    data = response.json()
    message = data.get("message", {})
    
    # Process Authors
    authors_raw = message.get("author", [])
    authors = []
    for a in authors_raw:
        first = a.get("given", "").strip()
        last = a.get("family", "").strip()
        if first or last:
            authors.append({"first": first, "last": last})
            
    # Process Title
    titles = message.get("title", [])
    title = titles[0].strip() if titles else ""
    
    # Process Journal
    journals = message.get("container-title", [])
    journal = journals[0].strip() if journals else ""
    
    short_journals = message.get("short-container-title", [])
    crossref_short = short_journals[0].strip() if short_journals else ""
    
    short_journal = resolve_short_journal(journal, crossref_short)
    
    # Process Volume and Pages
    vol = message.get("volume", "").strip()
    page_str = message.get("page", "").strip()
    page1, page2 = "", ""
    if page_str:
        if "-" in page_str:
            parts = page_str.split("-", 1)
            page1, page2 = parts[0].strip(), parts[1].strip()
        else:
            page1 = page_str
            
    # Process Year
    year = ""
    # Prefer published-print, fallback to published-online
    published = message.get("published-print", message.get("published-online", {}))
    date_parts = published.get("date-parts", [])
    if date_parts and date_parts[0]:
        year = str(date_parts[0][0])
        
    # Return structured dict
    return {
        "authors": authors,
        "title": title,
        "journal": journal,
        "short_journal": short_journal,
        "vol": vol,
        "page1": page1,
        "page2": page2,
        "year": year,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}"
    }

# Quick testing block
if __name__ == "__main__":
    test_url = "https://doi.org/10.1038/s41586-020-2649-2"
    try:
        res = fetch_metadata(test_url)
        print("Success:")
        for k, v in res.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
