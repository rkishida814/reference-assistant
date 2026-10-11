import os
from docx import Document
from docx.shared import Pt

def format_author(author, config):
    first = author.get("first", "").strip()
    last = author.get("last", "").strip()
    
    if config.get("initials", False) and first:
        # Just take first letter of each part, assuming spaces or hyphens might exist
        # A simple approach: first letter + '.'
        first = f"{first[0]}."
        
    fmt = config.get("author_format", "First Last")
    if fmt.startswith("Last, First"):
        # "Smith, John" or "Smith, J."
        if first and last:
            return f"{last}, {first}"
        return last or first
    else:
        # "John Smith" or "J. Smith"
        if first and last:
            return f"{first} {last}"
        return last or first

def build_runs_for_entry(entry, config):
    """
    Returns a list of dicts: [{"text": "...", "bold": bool, "italic": bool}, ...]
    """
    runs = []
    
    def add_run(text, field_name, is_delim=False, force_italic=False):
        if not text:
            return
        b = False if is_delim else config.get("bold", {}).get(field_name, False)
        i = force_italic if force_italic else (False if is_delim else config.get("italic", {}).get(field_name, False))
        runs.append({"text": text, "bold": b, "italic": i})

    def add_delim(text):
        if text:
            # We append space after delimiters like comma, semicolon, colon
            # If the user selects ' ', we ensure no double space.
            delim_text = text if text == " " else f"{text} "
            runs.append({"text": delim_text, "bold": False, "italic": False})

    # 1. AUTHORS
    authors = entry.get("authors", [])
    author_strs = [format_author(a, config) for a in authors if a.get("first") or a.get("last")]
    author_delim = config.get("delims", {}).get("author_author", ",")
    
    hide_after = config.get("hide_author_after", 0)
    export_et_al = config.get("export_et_al", True)
    
    if export_et_al and hide_after > 0 and len(author_strs) > hide_after:
        author_strs = author_strs[:hide_after] + ["et al."]
            
    
    for idx, auth_str in enumerate(author_strs):
        is_et_al = (auth_str == "et al.")
        add_run(auth_str, "Author", force_italic=is_et_al)
        if idx < len(author_strs) - 1:
            if author_strs[idx+1] == "et al.":
                add_delim(" ")
            else:
                add_delim(author_delim)

    def add_author_title_delim():
        delim = config.get("delims", {}).get("author_title", ".")
        if author_strs and author_strs[-1] == "et al." and delim == ".":
            add_delim(" ")
        else:
            add_delim(delim)

    # 2. TITLE
    if not config.get("hide_title", False):
        title = entry.get("title", "")
        if title and author_strs:
            add_author_title_delim()
        add_run(title, "Title")

    # 3. JOURNAL
    journal_field = "short_journal" if config.get("journal_abbrev", False) else "journal"
    journal = entry.get(journal_field, "")
    if not journal and journal_field == "short_journal":
        journal = entry.get("journal", "") # fallback
        
    if journal:
        # Delim before journal
        if not config.get("hide_title", False) and entry.get("title", ""):
            add_delim(config.get("delims", {}).get("title_journal", "."))
        elif author_strs and config.get("hide_title", False):
            add_author_title_delim()
            
        add_run(journal, "Journal")

    # 4. VOL, PAGE, YEAR (Ordered)
    orderings = config.get("ordering", "Vol, Page, Year")
    
    vol = entry.get("vol", "")
    page1 = entry.get("page1", "")
    page2 = entry.get("page2", "")
    page = f"{page1}-{page2}" if page1 and page2 else (page1 or page2)
    
    year = entry.get("year", "")
    if config.get("year_parens", False) and year:
        year = f"({year})"

    parts = []
    if "Vol" in orderings: parts.append(("Vol", vol))
    if "Page" in orderings: parts.append(("Page", page))
    if "Year" in orderings: parts.append(("Year", year))
    
    # Actually split the ordering string to know the exact sequence
    order_keys = [k.strip() for k in orderings.split(",")]
    
    has_vpy = any(val for k, val in parts)
    
    prev_added = False
    if journal:
        if has_vpy:
            add_delim(config.get("delims", {}).get("journal_vol", ","))
            
    for idx, key in enumerate(order_keys):
        val = next((v for k, v in parts if k == key), "")
        if not val:
            continue
            
        if prev_added:
            # Need a delimiter
            if key == "Page": delim_key = "vol_page"
            elif key == "Year": delim_key = "page_year"
            else: delim_key = "journal_vol"
            add_delim(config.get("delims", {}).get(delim_key, ","))
            
        add_run(val, key)
        prev_added = True

    # Add DOI if requested
    doi_export = config.get("doi_export", "No DOI")
    doi_text = ""
    if doi_export == "URL (https://doi.org/...)":
        doi_text = entry.get("doi_url", "")
    elif doi_export == "DOI Only (doi:...)":
        doi = entry.get("doi", "")
        if doi:
            doi_text = f"doi: {doi}"
            
    if doi_text:
        # Delim before DOI (typically a `. ` or ` `)
        if has_vpy or journal or author_strs or entry.get("title", ""):
            add_delim(" ")
        add_run(doi_text, "DOI")
        
    # Check if we need to ensure the final list item ends cleanly with a period.
    if config.get("end_period", False):
        if runs:
            last_text = str(runs[-1]["text"])
            if not last_text.rstrip().endswith("."):
                runs[-1]["text"] = last_text.rstrip() + "."

    return runs

def export_to_txt(entries, config, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(entries):
            runs = build_runs_for_entry(entry, config)
            text_line = "".join(r["text"] for r in runs)
            f.write(f"{i+1}. {text_line}\n")

def export_to_docx(entries, config, file_path):
    doc = Document()
    
    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10.5)
    
    # Set double spacing
    paragraph_format = style.paragraph_format
    paragraph_format.line_spacing = 2.0
    
    for i, entry in enumerate(entries):
        p = doc.add_paragraph()
        p.style = doc.styles['Normal']
        
        # Add the list number e.g. [1]
        run_num = p.add_run(f"[{i+1}] ")
        
        runs = build_runs_for_entry(entry, config)
        for r in runs:
            run = p.add_run(r["text"])
            run.bold = r["bold"]
            run.italic = r["italic"]
            
    doc.save(file_path)
