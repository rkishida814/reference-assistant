# Reference List Creation Assistant

**Web版:** https://rkishida814.github.io/reference-assistant/ （`docs/` を GitHub Pages で配信）

- ブラウザだけで動きます。Crossref への問い合わせもブラウザから直接行います。
- 文献リスト（`.txt`、中身は JSON）は手元で管理します。「開く…」で手元のファイルを開くと、Chrome / Edge では変更がそのファイルに自動保存されます。Safari / Firefox では「保存」でダウンロードされます。
- リストのファイルはこのリポジトリには含めません（`.gitignore` で `list/` と `*.txt` を除外）。

以下はデスクトップ版（PyQt6）の説明です。

A Python/PyQt6 application that automatically retrieves bibliographic metadata from DOI links or URLs via the Crossref API, allowing you to easily build and format reference lists.

## Features

- **Automatic Metadata Parsing:** Paste a DOI or URL to instantly retrieve authors, title, journal, volume, pages, and year via Crossref API.
- **Dynamic Formatting:** Real-time preview and export styles:
  - Author initials (e.g., "J. Smith" instead of "John Smith")
  - Toggle visibility of article titles
  - Reorder metadata logic (e.g., Vol, Page, Year vs Year, Vol, Page)
  - Custom delimiters between authors, titles, and journal info
- **Rich Text Export (DOCX):** Export properly formatted references to Microsoft Word Document (`.docx`) including all bold and italic settings.
- **Plain Text Export (TXT):** Export unstyled raw text list if needed.
- **Auto-Save:** Saves your current table state to a `.txt` (JSON structure) automatically in the background.

## Installation

1. Make sure Python 3.9+ is installed.
2. Clone or locate the repository directory.
3. Install the dependencies via pip:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Using a virtual environment (`python -m venv venv`) is highly recommended.)*

## Usage

1. Start the application:
   ```bash
   python main.py
   ```
2. **Start Screen:** Choose "New List" to start fresh or "Load Existing List" to load an auto-saved `.txt` project file.
3. **Editor Screen:**
   - **Adding Entries:** Enter a Crossref DOI (e.g. `10.1038/s41586-020-2649-2`) or URL into the top text box and click "Load Metadata".
   - **Styling:** Use checkboxes to apply italics or bold texts to specific fields and watch the changes apply instantly in the table.
   - **Reordering:** Drag and drop table rows on the left to re-order your references.
   - **Exporting:** When finished, click "Export as DOCX" to get your styled list!
