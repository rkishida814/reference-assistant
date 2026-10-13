// 雑誌略称の個人辞書
// - ブラウザ内（localStorage）に保存し、全リストで共通に使う
// - リスト保存時に .txt にも写しを書き込み、ブラウザの履歴を消しても開いたリストから復元できるようにする
// 形式: { "<正規化した正式名>": { journal: "<正式名>", abbrev: "<略称>" } }

const STORE_KEY = "reference-assistant-abbreviations";

let dict = {};
try { dict = JSON.parse(localStorage.getItem(STORE_KEY) || "{}") || {}; } catch { dict = {}; }

function persist() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(dict)); } catch {}
}

export function normalizeJournal(name) {
  return (name || "")
    .replace(/&amp;/gi, "&")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\.$/, "")
    .toLowerCase();
}

export function lookup(journal) {
  const hit = dict[normalizeJournal(journal)];
  return hit ? hit.abbrev : "";
}

export function learn(journal, abbrev) {
  const key = normalizeJournal(journal);
  abbrev = (abbrev || "").trim();
  if (!key || !abbrev) return false;
  if (dict[key] && dict[key].abbrev === abbrev) return false;
  dict[key] = { journal: journal.trim(), abbrev };
  persist();
  return true;
}

export function remove(key) {
  delete dict[key];
  persist();
}

export function setAbbrev(key, abbrev) {
  if (!dict[key]) return;
  abbrev = abbrev.trim();
  if (abbrev) dict[key].abbrev = abbrev;
  else delete dict[key];
  persist();
}

export function all() {
  return Object.entries(dict)
    .map(([key, v]) => ({ key, ...v }))
    .sort((a, b) => a.journal.localeCompare(b.journal));
}

export function snapshot() {
  return JSON.parse(JSON.stringify(dict));
}

// ファイルにあった辞書を取り込む（ブラウザ側に既にある項目を優先）。追加した件数を返す
export function mergeFrom(other) {
  if (!other || typeof other !== "object") return 0;
  let added = 0;
  for (const [key, v] of Object.entries(other)) {
    if (!dict[key] && v && v.abbrev) {
      dict[key] = { journal: v.journal || key, abbrev: v.abbrev };
      added++;
    }
  }
  if (added) persist();
  return added;
}

// 辞書と食い違う行（略称が辞書と違う）を返す
export function mismatches(entries, exclude = null) {
  return entries.filter((e) => {
    if (e === exclude) return false;
    const abbr = lookup(e.journal);
    return abbr && e.short_journal !== abbr;
  });
}
