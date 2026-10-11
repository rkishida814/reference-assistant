// core/metadata_fetcher.py と core/exporter.py のブラウザ版移植

const DOI_REGEX = /(10\.\d{4,9}\/[-._;()/:A-Z0-9]+)/i;

const KNOWN_ABBREVIATIONS = {
  "international journal of molecular sciences": "Int. J. Mol. Sci.",
  "international journal of molecular science": "Int. J. Mol. Sci.",
};

export const DEFAULT_CONFIG = {
  initials: true,
  hide_title: false,
  journal_abbrev: true,
  year_parens: false,
  end_period: true,
  doi_export: "DOI Only (doi:...)",
  ordering: "Vol, Page, Year",
  author_format: "First Last (John Smith)",
  hide_author_after: 0,
  export_et_al: true,
  italic: { Journal: true },
  bold: {},
  delims: { author_title: "." },
};

export function extractDoi(text) {
  const m = DOI_REGEX.exec(text);
  return m ? m[1].replace(/\/+$/, "") : null;
}

function resolveShortJournal(journal, crossrefShort) {
  const known = KNOWN_ABBREVIATIONS[journal.toLowerCase()];
  if (known) return known;
  return crossrefShort || journal;
}

export async function fetchMetadata(inputText) {
  const doi = extractDoi(inputText);
  if (!doi) throw new Error("入力から DOI を見つけられませんでした。");

  const res = await fetch(`https://api.crossref.org/works/${encodeURIComponent(doi)}`);
  if (!res.ok) throw new Error(`Crossref API がステータス ${res.status} を返しました。`);
  const message = (await res.json()).message || {};

  const authors = (message.author || [])
    .map((a) => ({ first: (a.given || "").trim(), last: (a.family || "").trim() }))
    .filter((a) => a.first || a.last);

  const first = (arr) => (arr && arr.length ? String(arr[0]).trim() : "");
  const title = first(message.title);
  const journal = first(message["container-title"]);
  const shortJournal = resolveShortJournal(journal, first(message["short-container-title"]));

  const vol = (message.volume || "").trim();
  const pageStr = (message.page || "").trim();
  let page1 = "", page2 = "";
  if (pageStr.includes("-")) {
    const i = pageStr.indexOf("-");
    page1 = pageStr.slice(0, i).trim();
    page2 = pageStr.slice(i + 1).trim();
  } else {
    page1 = pageStr;
  }

  const published = message["published-print"] || message["published-online"] || {};
  const dp = published["date-parts"];
  const year = dp && dp[0] && dp[0][0] != null ? String(dp[0][0]) : "";

  return {
    authors, title, journal, short_journal: shortJournal,
    vol, page1, page2, year, doi, doi_url: `https://doi.org/${doi}`,
  };
}

function decodeEntities(s) {
  return s.replace(/&(amp|lt|gt|quot|apos|#\d+|#x[0-9a-f]+);/gi, (all, e) => {
    const named = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" }[e.toLowerCase()];
    if (named) return named;
    const code = e[1].toLowerCase() === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
    return Number.isFinite(code) ? String.fromCodePoint(code) : all;
  });
}

function formatAuthor(author, config) {
  let first = (author.first || "").trim();
  const last = (author.last || "").trim();
  if (config.initials && first) first = `${first[0]}.`;
  if ((config.author_format || "").startsWith("Last, First")) {
    return first && last ? `${last}, ${first}` : last || first;
  }
  return first && last ? `${first} ${last}` : last || first;
}

// [{text, bold, italic}, ...] を返す
export function buildRunsForEntry(entry, config) {
  const runs = [];
  const delims = config.delims || {};
  const d = (key, def) => (delims[key] !== undefined ? delims[key] : def);

  const addRun = (text, field, forceItalic = false) => {
    if (!text) return;
    runs.push({
      text,
      bold: !!(config.bold || {})[field],
      italic: forceItalic || !!(config.italic || {})[field],
    });
  };
  const addDelim = (text) => {
    if (text) runs.push({ text: text === " " ? text : `${text} `, bold: false, italic: false });
  };

  // 1. 著者
  let authorStrs = (entry.authors || [])
    .filter((a) => a.first || a.last)
    .map((a) => formatAuthor(a, config));
  const hideAfter = Number(config.hide_author_after) || 0;
  const exportEtAl = config.export_et_al !== false;
  if (exportEtAl && hideAfter > 0 && authorStrs.length > hideAfter) {
    authorStrs = [...authorStrs.slice(0, hideAfter), "et al."];
  }
  authorStrs.forEach((s, idx) => {
    const isEtAl = s === "et al.";
    addRun(s, "Author", isEtAl);
    if (idx < authorStrs.length - 1) {
      addDelim(authorStrs[idx + 1] === "et al." ? " " : d("author_author", ","));
    }
  });

  const addAuthorTitleDelim = () => {
    const delim = d("author_title", ".");
    if (authorStrs.length && authorStrs[authorStrs.length - 1] === "et al." && delim === ".") addDelim(" ");
    else addDelim(delim);
  };

  // Crossref のタイトルに含まれる <i> <b> <sub> <sup> を書式に変換する
  const addMarkupRun = (text, field) => {
    if (!text) return;
    const baseBold = !!(config.bold || {})[field];
    const baseItalic = !!(config.italic || {})[field];
    const depth = { i: 0, b: 0, sub: 0, sup: 0 };
    const alias = { em: "i", strong: "b" };
    const tagRe = /<\s*(\/?)\s*([a-z0-9:]+)[^>]*>/gi;
    let last = 0, m;
    const push = (chunk) => {
      chunk = decodeEntities(chunk);
      if (!chunk) return;
      runs.push({
        text: chunk,
        bold: baseBold || depth.b > 0,
        italic: baseItalic !== depth.i > 0, // 全体が斜体のときはタグ部分を立体に戻す
        sub: depth.sub > 0,
        sup: depth.sup > 0,
      });
    };
    while ((m = tagRe.exec(text))) {
      push(text.slice(last, m.index));
      last = tagRe.lastIndex;
      const name = alias[m[2].toLowerCase()] || m[2].toLowerCase();
      if (name in depth) depth[name] = Math.max(0, depth[name] + (m[1] ? -1 : 1));
    }
    push(text.slice(last));
  };

  // 2. タイトル
  if (!config.hide_title) {
    const title = entry.title || "";
    if (title && authorStrs.length) addAuthorTitleDelim();
    addMarkupRun(title, "Title");
  }

  // 3. 雑誌名
  let journal = config.journal_abbrev ? entry.short_journal || "" : entry.journal || "";
  if (!journal && config.journal_abbrev) journal = entry.journal || "";
  if (journal) {
    if (!config.hide_title && entry.title) addDelim(d("title_journal", "."));
    else if (authorStrs.length && config.hide_title) addAuthorTitleDelim();
    addRun(journal, "Journal");
  }

  // 4. 巻・ページ・年（順序指定）
  const page1 = entry.page1 || "", page2 = entry.page2 || "";
  let year = entry.year || "";
  if (config.year_parens && year) year = `(${year})`;
  const values = {
    Vol: entry.vol || "",
    Page: page1 && page2 ? `${page1}-${page2}` : page1 || page2,
    Year: year,
  };
  const orderKeys = (config.ordering || "Vol, Page, Year").split(",").map((k) => k.trim());
  const hasVpy = Object.values(values).some(Boolean);

  if (journal && hasVpy) addDelim(d("journal_vol", ","));
  let prevAdded = false;
  for (const key of orderKeys) {
    const val = values[key] || "";
    if (!val) continue;
    if (prevAdded) {
      const delimKey = key === "Page" ? "vol_page" : key === "Year" ? "page_year" : "journal_vol";
      addDelim(d(delimKey, ","));
    }
    addRun(val, key);
    prevAdded = true;
  }

  // DOI
  let doiText = "";
  if (config.doi_export === "URL (https://doi.org/...)") doiText = entry.doi_url || "";
  else if (config.doi_export === "DOI Only (doi:...)" && entry.doi) doiText = `doi: ${entry.doi}`;
  if (doiText) {
    if (hasVpy || journal || authorStrs.length || entry.title) addDelim(" ");
    addRun(doiText, "DOI");
  }

  if (config.end_period && runs.length) {
    const last = runs[runs.length - 1];
    if (!last.text.trimEnd().endsWith(".")) last.text = last.text.trimEnd() + ".";
  }
  return runs;
}

export function buildTxt(entries, config) {
  return entries
    .map((e, i) => `${i + 1}. ${buildRunsForEntry(e, config).map((r) => r.text).join("")}\n`)
    .join("");
}

// window.docx（docx ライブラリの IIFE 版）を使って Blob を作る
export async function buildDocx(entries, config) {
  const { Document, Packer, Paragraph, TextRun } = window.docx;
  const paragraphs = entries.map((e, i) => new Paragraph({
    spacing: { line: 480 }, // ダブルスペース
    children: [
      new TextRun(`[${i + 1}] `),
      ...buildRunsForEntry(e, config).map((r) => new TextRun({ text: r.text, bold: r.bold, italics: r.italic, subScript: !!r.sub, superScript: !!r.sup })),
    ],
  }));
  const doc = new Document({
    styles: {
      default: { document: { run: { font: "Times New Roman", size: 21 } } }, // 10.5pt
    },
    sections: [{ children: paragraphs }],
  });
  return Packer.toBlob(doc);
}
