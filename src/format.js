/* format.js
 *
 * Turns a value from an artifact into the text a reader sees, and writes the
 * sentences for the three states a figure can be in when it is not there:
 * loading, failed to load, and present but empty. No DOM, so it runs under
 * plain node; tools/validate-artifacts.mjs does exactly that. The sibling
 * crack-spread-study's formatter with this study's units.
 *
 * WHERE THE DECIMALS COME FROM. Not from here. Each artifact carries
 * conventions.decimals, a map from a format name such as usd_mmbtu to a count
 * of places, and every numeric segment names its format. A format the artifact
 * does not declare throws, naming it, rather than falling back to a guess.
 *
 * SIGNS. A negative figure in prose carries U+2212, the minus sign, a true
 * minus rather than a hyphen; in Figtree and JetBrains Mono it is near the
 * width of a figure, in Fraunces narrower, which in prose does not matter
 * because no figure there is read against one above it. A negative figure in a table cell
 * carries the ASCII hyphen minus, so a copied cell pastes into a spreadsheet as
 * a number. A positive figure carries a plus only when the artifact marks the
 * value signed. A value that rounds to zero prints with no sign at all, so the
 * page never says "-0.00".
 *
 * MISSING. null, undefined, NaN and the infinities are missing, never zero.
 * The number formatters return null for them, and the caller decides what the
 * gap says: the artifact's own words for it, never the field's identifier.
 *
 * Numeric literals: the code point of the minus sign, declared in
 * tools/check-literals.mjs. The unit words hold no digits.
 */

const MINUS_SIGN = 0x2212;

/** U+2212, the typographic minus, for prose. */
export const MINUS_PROSE = String.fromCharCode(MINUS_SIGN);
/** U+002D, the hyphen minus, for table cells. */
export const MINUS_TABLE = "-";

/** The unit each format is read in. An empty string is a dimensionless
 *  figure: a count, a year, a t statistic. */
export const UNITS = Object.freeze({
  usd_mmbtu: "$/MMBtu",
  eur_mwh: "EUR/MWh",
  usd_day: "$/day",
  usd_per_eur: "USD per EUR",
  eur_t: "EUR/t",
  percent: "percent",
  share_percent: "percent",
  days: "days",
  nm: "nautical miles",
  knots: "knots",
  usd: "$",
  rate_percent: "percent",
  bp: "basis points",
  share: "",
  percent_day: "percent a day",
  boil_off_percent: "percent a day",
  fill_percent: "percent",
  mmbtu_per_m3: "MMBtu per m3",
  mmbtu_per_t: "MMBtu per tonne",
  mmbtu_per_mwh: "MMBtu per MWh",
  m3: "m3",
  mmbtu: "MMBtu",
  bcf: "Bcf",
  slope: "",
  t_stat: "",
  r2: "",
  count: "",
  year: "",
});

/* A year is written 2026, never 2,026. Every other format groups thousands. */
const UNGROUPED = new Set(["year"]);

/** True for anything the page must show as a gap rather than a number. */
export function isMissing(value) {
  return value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value);
}

/** The number of places the artifact declares for a format, or a thrown
 *  Error naming the format and the formats it does declare. */
export function decimalsFor(format, decimals) {
  if (!decimals || typeof decimals !== "object") {
    throw new Error("format.js was given no decimals table; pass the artifact's conventions.decimals");
  }
  const places = decimals[format];
  if (!Number.isInteger(places) || places < 0) {
    throw new Error(
      "the artifact declares no decimals for the format " + JSON.stringify(format) +
      "; it declares " + Object.keys(decimals).sort().join(", ")
    );
  }
  return places;
}

/** Format one number.
 *
 *    value     the number from the artifact
 *    format    its format name, for example "usd_mmbtu"
 *    decimals  the artifact's conventions.decimals
 *    options   { signed: boolean, context: "prose" | "table" }
 *
 *  Returns a string, or null when the value is missing. */
export function formatNumber(value, format, decimals, options) {
  const opts = options || {};
  const places = decimalsFor(format, decimals);
  if (isMissing(value)) return null;
  const body = new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
    useGrouping: !UNGROUPED.has(format),
  }).format(Math.abs(value));
  const roundsToZero = !/[1-9]/.test(body);
  if (roundsToZero) return body;
  if (value < 0) return (opts.context === "table" ? MINUS_TABLE : MINUS_PROSE) + body;
  if (opts.signed) return "+" + body;
  return body;
}

/** A number and its unit, "23.96 $/MMBtu", or null when the value is missing. */
export function formatQuantity(value, format, decimals, options) {
  const text = formatNumber(value, format, decimals, options);
  if (text === null) return null;
  const unit = Object.prototype.hasOwnProperty.call(UNITS, format) ? UNITS[format] : "";
  return unit ? text + " " + unit : text;
}

/** The text of one sentence segment, as the export writes them:
 *    { text }                                  words, no digit
 *    { field, value, format, signed? }         a number
 *    { field, value, label }                   a date or a word, with its label
 *  Returns { text, kind, field, missing } where kind is "text", "number" or
 *  "label". A missing number keeps its field so the caller can name the gap. */
export function segmentText(segment, decimals) {
  if (Object.prototype.hasOwnProperty.call(segment, "text")) {
    return { text: segment.text, kind: "text", field: null, missing: false };
  }
  if (typeof segment.label === "string") {
    return { text: segment.label, kind: "label", field: segment.field, missing: false };
  }
  const text = formatNumber(segment.value, segment.format, decimals, {
    signed: segment.signed === true,
    context: "prose",
  });
  return { text, kind: "number", field: segment.field, missing: text === null };
}

/** A whole sentence of segments as plain text, for an SVG title or desc. A
 *  missing number reads as the segment's own `missing` words, or "no figure". */
export function segmentsText(segments, decimals) {
  return segments
    .map((segment) => {
      const piece = segmentText(segment, decimals);
      return piece.missing ? missingFigureText(segment.missing) : piece.text;
    })
    .join("");
}

/** A figure for a table cell: hyphen minus, sign when asked, or null. */
export function formatCell(value, format, decimals, signed) {
  return formatNumber(value, format, decimals, { signed: signed === true, context: "table" });
}

/* The words after a count, in the number the count actually is. Alternatives
 * are written {singular|plural}, the syntax the export's _plural reads. */
const PLURAL_CHOICE = /\{([^{}|]*)\|([^{}]*)\}/g;

/** countWords(1, " {week|weeks} from ") is " week from ". */
export function countWords(count, text) {
  return String(text).replace(PLURAL_CHOICE, (all, one, many) => (Number(count) === 1 ? one : many));
}

/* ------------------------------------------------------------- time --- */

/* "2-digit" is Intl's own option vocabulary, a string the API defines, not a
 * figure; tools/check-literals.mjs allows it by exact value. */
const INSTANT_PARTS = Object.freeze({
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "UTC",
});

const DAY_PARTS = Object.freeze({ day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

/** "8 October 2026 at 21:04 UTC", for a fetch time. null for anything that is
 *  not a valid instant. */
export function formatInstant(iso) {
  const date = typeof iso === "string" ? new Date(iso) : iso;
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return null;
  const parts = {};
  for (const part of new Intl.DateTimeFormat("en-GB", INSTANT_PARTS).formatToParts(date)) {
    parts[part.type] = part.value;
  }
  return parts.day + " " + parts.month + " " + parts.year + " at " + parts.hour + ":" + parts.minute + " UTC";
}

/** "7 October 2026" for an ISO day, or null. */
export function formatDay(iso) {
  if (typeof iso !== "string") return null;
  // A date only ISO string is read as midnight UTC.
  const date = new Date(iso.slice(0, "YYYY-MM-DD".length));
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", DAY_PARTS).format(date);
}

/* ------------------------------------------ loading, empty and error --- */

/** "Loading the netbacks." */
export function loadingSentence(what) {
  return "Loading " + what + ".";
}

/** Two sentences for an artifact that did not load: what happened, then what
 *  to do. `failure` is the record state.js keeps, with its time. */
export function loadFailureSentences(failure) {
  const when = formatInstant(failure.at);
  const happened =
    "The page could not load " + failure.path + ", which holds " + failure.holds +
    ": " + failure.what + (when ? ", at " + when : "") + ".";
  const todo = failure.todo ||
    "Reload the page to try again. If it fails again the file is missing or damaged in this copy of the site, " +
    "and nothing it holds is shown, rather than shown from a guess.";
  return [happened, todo];
}

/** The sentence an empty chart shows in place of its marks.
 *
 *    series      the series name, in words
 *    fetchedAt   the ISO time of the last fetch attempt, or null
 *    status      the manifest's status word for the series
 *    reason      the reason for the gap, a sentence, or null
 */
export function emptySeriesSentence({ series, fetchedAt, status, reason }) {
  const when = formatInstant(fetchedAt);
  let fetch;
  if (status === "failed") {
    fetch = when ? "its last fetch failed, at " + when : "its last fetch failed, and the time of that fetch is not recorded";
  } else if (status === "stale") {
    fetch = when ? "its last successful fetch, at " + when + ", is stale" : "it is stale, and the time of its last fetch is not recorded";
  } else {
    fetch = when ? "it was last fetched at " + when + " and holds no values for this range" : "it holds no values for this range, and the time of its last fetch is not recorded";
  }
  const because = reason ? " " + reason.trim().replace(/\.?$/, ".") : "";
  return "Nothing is drawn for " + series + ": " + fetch + "." + because + " The gap is left empty rather than filled.";
}

/* The words for one missing figure. The words are the caller's, taken from the
 * artifact, which is where the series and the reason for the gap are named. An
 * identifier handed here is dropped rather than printed: a column's code name
 * is not what the thing is called, and a cell that only says "no figure" is
 * still true. Each empty cell's reason is also said once in words, in the
 * caption or the note beside its table. */

/** What a cell with no figure says when nothing else can be said about it. */
export const NO_FIGURE = "no figure";

const HAS_UNDERSCORE = /_/;
const ENDS_LIKE_A_FIELD = /\b(usd\s+mmbtu|eur\s+mwh|usd\s+day|usd\s+per\s+eur|eur\s+t|days|nm|mmbtu|usd|percent|count|year|t\s+stat)$/i;
const IS_ONE_WORD = /^\S+$/;

/** The words for a figure that is missing: the artifact's plain words, or
 *  "no figure" when they are absent or shaped like an identifier. */
export function missingFigureText(words) {
  const name = typeof words === "string" ? words.trim() : "";
  if (!name) return NO_FIGURE;
  if (HAS_UNDERSCORE.test(name) || IS_ONE_WORD.test(name) || ENDS_LIKE_A_FIELD.test(name)) return NO_FIGURE;
  return name;
}
