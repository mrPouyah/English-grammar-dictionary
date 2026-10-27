/* Persian/Arabic-aware text normalization.
   Must stay byte-for-byte equivalent to telegram_bot.normalized() and the
   Python exporter's normalize(): NFKC, lowercase, yeh/kaf unification,
   zero-width non-joiner and tatweel to space, combining marks removed. */
export function normalize(text) {
  let t = String(text || '').normalize('NFKC').toLowerCase();
  t = t.replace(/[\u064a\u0649]/g, '\u06cc')   // ي ى -> ی
       .replace(/\u0643/g, '\u06a9')            // ك -> ک
       .replace(/[\u200c\u0640]/g, ' ')         // ZWNJ, tatweel -> space
       .replace(/\p{M}+/gu, '');                // combining marks
  return t.split(/\s+/).filter(Boolean).join(' ');
}

export function terms(query) {
  return normalize(query).split(' ').filter(Boolean);
}
