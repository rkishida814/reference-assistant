import { DEFAULT_CONFIG, fetchMetadata, buildRunsForEntry, buildTxt, buildDocx } from "./format.js?v=4";

const FONT_FIELDS = ["Author", "Title", "Journal", "Vol", "Page", "Year"];
const DELIM_KEYS = ["author_author", "author_title", "title_journal", "journal_vol", "vol_page", "page_year"];
const DELIM_OPTIONS = [",", ";", ":", ".", " "];
export const VERSION = "4";
const DRAFT_KEY = "reference-assistant-draft";
const canUseFS = "showOpenFilePicker" in window;

const $ = (id) => document.getElementById(id);
const clone = (x) => JSON.parse(JSON.stringify(x));

const state = {
  entries: [],
  config: normalizeConfig(DEFAULT_CONFIG),
  listName: "Untitled_List",
  fileHandle: null, // File System Access API のハンドル（あれば同じファイルへ自動保存）
  undoStack: [],
};


function normalizeConfig(cfg) {
  const c = { ...clone(DEFAULT_CONFIG), ...clone(cfg || {}) };
  c.italic = { ...(cfg && cfg.italic ? cfg.italic : DEFAULT_CONFIG.italic) };
  c.bold = { ...(cfg && cfg.bold ? cfg.bold : DEFAULT_CONFIG.bold) };
  const delims = (cfg && cfg.delims) || DEFAULT_CONFIG.delims;
  c.delims = {};
  // デスクトップ版と同じく、未指定の区切りは ","
  for (const k of DELIM_KEYS) c.delims[k] = delims[k] !== undefined ? delims[k] : ",";
  return c;
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 2500);
}

// ---------- 保存 ----------

function serialize() {
  return JSON.stringify({ entries: state.entries, config: state.config }, null, 2);
}

let saveTimer = null;
function markChanged(tableToo = true) {
  if (tableToo) render();
  else renderPreview();
  try { localStorage.setItem(DRAFT_KEY, JSON.stringify({ name: state.listName, data: serialize() })); } catch {}
  $("save-status").textContent = state.fileHandle ? "保存待ち…" : "未保存（「保存」で手元に書き出し）";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(autoSave, 1000);
}

async function autoSave() {
  if (!state.fileHandle) return;
  try {
    const w = await state.fileHandle.createWritable();
    await w.write(serialize());
    await w.close();
    $("save-status").textContent = `自動保存済み: ${state.fileHandle.name}`;
  } catch (e) {
    $("save-status").textContent = "自動保存に失敗しました。「保存」を押してください";
    console.error(e);
  }
}

async function saveAs() {
  const suggested = `${state.listName}.txt`;
  if (canUseFS) {
    try {
      state.fileHandle = await window.showSaveFilePicker({
        suggestedName: suggested,
        types: [{ description: "Reference list", accept: { "text/plain": [".txt"] } }],
      });
      state.listName = state.fileHandle.name.replace(/\.txt$/i, "");
      $("list-name").value = state.listName;
      await autoSave();
    } catch (e) {
      if (e.name !== "AbortError") toast(`保存できませんでした: ${e.message}`);
    }
  } else {
    download(new Blob([serialize()], { type: "text/plain" }), suggested);
    $("save-status").textContent = "ダウンロードしました";
  }
}

function download(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---------- 読み込み ----------

function parseList(text) {
  const data = JSON.parse(text);
  if (Array.isArray(data)) return { entries: data, config: null }; // 旧形式
  return { entries: data.entries || [], config: data.config || null };
}

async function pickFile() {
  if (canUseFS) {
    try {
      const [handle] = await window.showOpenFilePicker({
        types: [{ description: "Reference list", accept: { "text/plain": [".txt", ".json"] } }],
      });
      return { handle, file: await handle.getFile() };
    } catch (e) {
      if (e.name === "AbortError") throw e;
      // 使えない環境では従来のファイル選択に切り替える（この場合は自動保存なし）
      console.warn(e);
      toast(`ファイル選択を切り替えます（${e.name}）`);
    }
  }
  return new Promise((resolve, reject) => {
    const input = $("file-input");
    input.value = "";
    input.onchange = () => (input.files[0] ? resolve({ handle: null, file: input.files[0] }) : reject(new DOMException("", "AbortError")));
    input.oncancel = () => reject(new DOMException("", "AbortError"));
    input.click();
  });
}

async function openList() {
  try {
    const { handle, file } = await pickFile();
    const { entries, config } = parseList(await file.text());
    state.entries = entries;
    state.config = normalizeConfig(config || DEFAULT_CONFIG);
    state.fileHandle = handle;
    state.listName = file.name.replace(/\.(txt|json)$/i, "");
    state.undoStack = [];
    $("list-name").value = state.listName;
    syncControls();
    render();
    $("save-status").textContent = handle ? `開いています: ${file.name}（変更は自動保存）` : `読み込みました: ${file.name}`;
  } catch (e) {
    if (e.name !== "AbortError") toast(`読み込めませんでした: ${e.message}`);
  }
}

async function appendFromList() {
  try {
    const { file } = await pickFile();
    const { entries } = parseList(await file.text());
    snapshot();
    state.entries.push(...entries);
    markChanged();
    toast(`${entries.length} 件追加しました`);
  } catch (e) {
    if (e.name !== "AbortError") toast(`読み込めませんでした: ${e.message}`);
  }
}

function newList() {
  if (state.entries.length && !confirm("今のリストを閉じて新規リストを作りますか？（保存済みファイルはそのまま残ります）")) return;
  state.entries = [];
  state.config = normalizeConfig(DEFAULT_CONFIG);
  state.fileHandle = null;
  state.listName = "Untitled_List";
  state.undoStack = [];
  $("list-name").value = state.listName;
  syncControls();
  markChanged();
}

// ---------- 取り消し ----------

function snapshot() {
  state.undoStack.push(clone(state.entries));
  if (state.undoStack.length > 50) state.undoStack.shift();
}
function undo() {
  if (!state.undoStack.length) return;
  state.entries = state.undoStack.pop();
  markChanged();
}

// ---------- メタデータ取得 ----------

async function loadMetadata() {
  const input = $("doi-input");
  const text = input.value.trim();
  if (!text) return toast("DOI または URL を入力してください");
  const btn = $("btn-load");
  btn.disabled = true;
  btn.textContent = "取得中…";
  try {
    const entry = await fetchMetadata(text);
    snapshot();
    state.entries.push(entry);
    input.value = "";
    markChanged();
  } catch (e) {
    toast(`取得に失敗しました: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "メタデータ取得";
  }
}

// ---------- 設定パネル ----------

function buildSettingsUI() {
  for (const [rowId, kind] of [["italic-row", "italic"], ["bold-row", "bold"]]) {
    const row = $(rowId);
    for (const f of FONT_FIELDS) {
      const label = document.createElement("label");
      label.innerHTML = `<input type="checkbox" data-font="${kind}" data-field="${f}"> ${f}`;
      row.appendChild(label);
    }
  }
  const delimRow = $("delim-row");
  for (const k of DELIM_KEYS) {
    const label = document.createElement("label");
    label.innerHTML = `<span data-delim-label="${k}"></span> <select data-delim="${k}">${DELIM_OPTIONS.map((o) => `<option value="${o}">${o === " " ? "(空白)" : o}</option>`).join("")}</select>`;
    delimRow.appendChild(label);
  }

  document.querySelector(".settings").addEventListener("change", (ev) => {
    const el = ev.target;
    const c = state.config;
    if (el.dataset.cfg) {
      const k = el.dataset.cfg;
      c[k] = el.type === "checkbox" ? el.checked : el.type === "number" ? Math.max(0, parseInt(el.value, 10) || 0) : el.value;
    } else if (el.dataset.font) {
      c[el.dataset.font][el.dataset.field] = el.checked;
    } else if (el.dataset.delim) {
      c.delims[el.dataset.delim] = el.value;
    } else return;
    updateDelimLabels();
    markChanged();
  });
}

function syncControls() {
  const c = state.config;
  document.querySelectorAll("[data-cfg]").forEach((el) => {
    const v = c[el.dataset.cfg];
    if (el.type === "checkbox") el.checked = !!v;
    else el.value = v;
  });
  document.querySelectorAll("[data-font]").forEach((el) => { el.checked = !!c[el.dataset.font][el.dataset.field]; });
  document.querySelectorAll("[data-delim]").forEach((el) => { el.value = c.delims[el.dataset.delim]; });
  updateDelimLabels();
}

function updateDelimLabels() {
  const p = state.config.ordering.split(",").map((s) => s.trim());
  const labels = {
    author_author: "著者間", author_title: "著者-タイトル", title_journal: "タイトル-雑誌",
    journal_vol: `Journal-${p[0]}`, vol_page: `${p[0]}-${p[1]}`, page_year: `${p[1]}-${p[2]}`,
  };
  document.querySelectorAll("[data-delim-label]").forEach((el) => { el.textContent = labels[el.dataset.delimLabel] + ":"; });
}

// ---------- 表 ----------

function columns() {
  const maxAuthors = Math.max(1, ...state.entries.map((e) => (e.authors || []).length));
  const hideAfter = Number(state.config.hide_author_after) || 0;
  const cols = [];
  for (let i = 0; i < maxAuthors; i++) {
    if (hideAfter > 0 && i >= hideAfter) break;
    cols.push({ head: `Author ${i + 1} First`, author: i, part: "first", font: "Author", cls: "w-name" });
    cols.push({ head: `Author ${i + 1} Last`, author: i, part: "last", font: "Author", cls: "w-name" });
  }
  const journalKey = state.config.journal_abbrev ? "short_journal" : "journal";
  cols.push(
    { head: "Title", key: "title", font: "Title", cls: "w-title" },
    { head: state.config.journal_abbrev ? "Journal (略称)" : "Journal", key: journalKey, font: "Journal", cls: "w-journal" },
    { head: "Vol", key: "vol", font: "Vol", cls: "w-short" },
    { head: "Page 1", key: "page1", font: "Page", cls: "w-short" },
    { head: "Page 2", key: "page2", font: "Page", cls: "w-short" },
    { head: "Year", key: "year", font: "Year", cls: "w-short" },
    { head: "DOI URL", key: "doi_url", cls: "w-url" },
  );
  return cols;
}

function getCell(entry, col) {
  if (col.author !== undefined) return ((entry.authors || [])[col.author] || {})[col.part] || "";
  return entry[col.key] || "";
}

function setCell(entry, col, value) {
  if (col.author !== undefined) {
    entry.authors = entry.authors || [];
    while (entry.authors.length <= col.author) entry.authors.push({ first: "", last: "" });
    entry.authors[col.author][col.part] = value;
  } else {
    entry[col.key] = value;
  }
}

let currentCols = [];

function render() {
  currentCols = columns();
  const c = state.config;
  const thead = $("ref-table").tHead;
  thead.innerHTML = `<tr><th></th><th></th><th>#</th>${currentCols.map((col) => `<th>${col.head}</th>`).join("")}</tr>`;

  const tbody = $("ref-table").tBodies[0];
  tbody.innerHTML = "";
  state.entries.forEach((entry, r) => {
    const tr = document.createElement("tr");
    tr.dataset.row = r;
    tr.innerHTML = `<td class="ctrl del" title="この行を削除">🗑️</td><td class="ctrl handle" title="ドラッグで並べ替え">↕</td><td class="num-col">${r + 1}</td>`;
    currentCols.forEach((col, ci) => {
      const td = document.createElement("td");
      const input = document.createElement("input");
      input.className = col.cls;
      input.value = getCell(entry, col);
      input.dataset.row = r;
      input.dataset.col = ci;
      if (col.font) {
        if (c.italic[col.font]) input.classList.add("it");
        if (c.bold[col.font]) input.classList.add("bd");
      }
      td.appendChild(input);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  $("empty-msg").hidden = state.entries.length > 0;
  renderPreview();
}

function renderPreview() {
  const c = state.config;
  const list = $("preview-list");
  list.innerHTML = "";
  for (const entry of state.entries) {
    const li = document.createElement("li");
    for (const run of buildRunsForEntry(entry, c)) {
      const span = document.createElement(run.sub ? "sub" : run.sup ? "sup" : "span");
      span.textContent = run.text;
      if (run.italic) span.className = "it";
      if (run.bold) span.classList.add("bd");
      li.appendChild(span);
    }
    list.appendChild(li);
  }
}

function setupTable() {
  const tbody = $("ref-table").tBodies[0];

  // セル編集（確定時に 1 回だけ取り消し履歴を積む）
  tbody.addEventListener("change", (ev) => {
    const el = ev.target;
    if (el.tagName !== "INPUT") return;
    const entry = state.entries[+el.dataset.row];
    const col = currentCols[+el.dataset.col];
    if (getCell(entry, col) === el.value) return;
    snapshot();
    const before = columns().length;
    setCell(entry, col, el.value);
    markChanged(columns().length !== before);
  });

  // 表計算ソフトからのタブ区切り貼り付けを複数セルに展開
  tbody.addEventListener("paste", (ev) => {
    const el = ev.target;
    if (el.tagName !== "INPUT") return;
    const text = ev.clipboardData.getData("text/plain");
    if (!/[\t\n]/.test(text)) return;
    ev.preventDefault();
    snapshot();
    const r0 = +el.dataset.row, c0 = +el.dataset.col;
    text.replace(/\r/g, "").replace(/\n$/, "").split("\n").forEach((line, dr) => {
      const entry = state.entries[r0 + dr];
      if (!entry) return;
      line.split("\t").forEach((val, dc) => {
        const col = currentCols[c0 + dc];
        if (col) setCell(entry, col, val);
      });
    });
    markChanged();
  });

  tbody.addEventListener("click", (ev) => {
    const td = ev.target.closest("td.del");
    if (!td) return;
    const r = +td.parentElement.dataset.row;
    if (confirm(`${r + 1} 行目を削除しますか？`)) {
      snapshot();
      state.entries.splice(r, 1);
      markChanged();
    }
  });

  // ↕ をつかんだときだけ行をドラッグ可能にする
  let dragFrom = null;
  tbody.addEventListener("mousedown", (ev) => {
    const handle = ev.target.closest("td.handle");
    if (handle) handle.parentElement.draggable = true;
  });
  tbody.addEventListener("dragstart", (ev) => {
    const tr = ev.target.closest("tr");
    dragFrom = +tr.dataset.row;
    tr.classList.add("dragging");
    ev.dataTransfer.effectAllowed = "move";
    ev.dataTransfer.setData("text/plain", String(dragFrom));
  });
  const clearMarks = () => tbody.querySelectorAll("tr").forEach((t) => t.classList.remove("drop-before", "drop-after", "dragging"));
  tbody.addEventListener("dragover", (ev) => {
    if (dragFrom === null) return;
    const tr = ev.target.closest("tr");
    if (!tr) return;
    ev.preventDefault();
    const rect = tr.getBoundingClientRect();
    const after = ev.clientY > rect.top + rect.height / 2;
    tbody.querySelectorAll("tr").forEach((t) => t.classList.remove("drop-before", "drop-after"));
    tr.classList.add(after ? "drop-after" : "drop-before");
  });
  tbody.addEventListener("drop", (ev) => {
    if (dragFrom === null) return;
    ev.preventDefault();
    const tr = ev.target.closest("tr");
    if (tr) {
      const rect = tr.getBoundingClientRect();
      let to = +tr.dataset.row + (ev.clientY > rect.top + rect.height / 2 ? 1 : 0);
      if (dragFrom < to) to -= 1;
      if (to !== dragFrom) {
        snapshot();
        const [item] = state.entries.splice(dragFrom, 1);
        state.entries.splice(to, 0, item);
        markChanged();
      }
    }
    dragFrom = null;
    clearMarks();
  });
  tbody.addEventListener("dragend", (ev) => {
    dragFrom = null;
    clearMarks();
    const tr = ev.target.closest && ev.target.closest("tr");
    if (tr) tr.draggable = false;
  });
}

// ---------- 起動 ----------

function init() {
  $("version").textContent = `v${VERSION}`;
  buildSettingsUI();
  setupTable();

  $("btn-new").onclick = newList;
  $("btn-open").onclick = openList;
  $("btn-append").onclick = appendFromList;
  $("btn-save").onclick = saveAs;
  $("btn-load").onclick = loadMetadata;
  $("doi-input").addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) loadMetadata(); });
  $("list-name").addEventListener("change", (ev) => {
    state.listName = ev.target.value.trim() || "Untitled_List";
    ev.target.value = state.listName;
  });

  $("btn-export-txt").onclick = () => download(new Blob([buildTxt(state.entries, state.config)], { type: "text/plain" }), `${state.listName}.txt`);
  $("btn-export-docx").onclick = async () => {
    if (!window.docx) return toast("DOCX ライブラリを読み込めていません。通信を確認して再読み込みしてください");
    download(await buildDocx(state.entries, state.config), `${state.listName}.docx`);
  };

  // 入力欄の外での ⌘Z / Ctrl+Z は表の取り消し（入力欄の中はブラウザ標準の取り消し）
  document.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && !ev.shiftKey && ev.key.toLowerCase() === "z") {
      const tag = document.activeElement && document.activeElement.tagName;
      if (tag !== "INPUT" && tag !== "SELECT") {
        ev.preventDefault();
        undo();
      }
    }
  });

  // ページを再読み込みしても作業中のリストを失わないよう、ブラウザ内の下書きを復元
  try {
    const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null");
    if (draft) {
      const { entries, config } = parseList(draft.data);
      state.entries = entries;
      state.config = normalizeConfig(config);
      state.listName = draft.name || state.listName;
      $("list-name").value = state.listName;
      if (entries.length) $("save-status").textContent = "前回の下書きを復元しました（ファイルとは未接続。「開く」か「保存」でつなぎ直せます）";
    }
  } catch {}

  syncControls();
  render();
}

init();
