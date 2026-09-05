#!/usr/bin/env python3
"""
Transform the old project's JSONL export into the flat data model used by
the Eleventy + Pagefind proof of concept:

    { id, author, author_display, title, text, year_start, year_end }

Dates are SYNTHETIC placeholders for testing the date-range filter
mechanism only -- most are loosely inspired by these writers' real eras,
but they are not scholarly claims and should not be treated as such.
A handful are deliberately pushed into BCE (negative years, ignoring the
no-year-zero technicality -- irrelevant at this granularity) so the BCE
handling in the filter can actually be exercised.
"""
import csv
import io
import json
import hashlib
import sys
import urllib.request
import urllib.error
from pathlib import Path

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "manual_3.jsonl"
HARLAND_SRC = Path(__file__).parent / "harland_data.json"
SHEET_CONFIG = Path(__file__).parent / "sheet_config.json"
OUT = Path(__file__).parent / "site" / "_data" / "records.json"

# Rough, non-scholarly floruit windows for named authors in the dataset,
# just so the demo doesn't look like pure noise. (year_start, year_end)
KNOWN_RANGES = {
    "Chrysostom": (349, 407),
    "Augustine": (354, 430),
    "Cyprian of Carthage": (200, 258),
    "Tertullian": (155, 220),
    "Eusebius": (260, 340),
    "Tacitus": (56, 120),
    "Sozomen": (400, 450),
    "Ambrose": (340, 397),
    "Sulpitius Severus": (363, 425),
    "Theodoret": (393, 457),
    "Leo the Great": (400, 461),
    "Origen": (184, 253),
    "Socrates Scholasticus": (380, 439),
    "Jerome": (347, 420),
    "Paul": (5, 65),
    "John Cassian": (360, 435),
    "Clement of Alexandria": (150, 215),
    "Tatian": (120, 180),
    "Athanasius": (296, 373),
    "Nicodemus": (300, 400),
    "Luke": (75, 95),
    "pseudo-Hippolytus of Rome": (200, 250),
    "Lactantius": (250, 325),
    "Gregory the Great": (540, 604),
    "Barnabas": (70, 135),
    "Ignatius": (35, 108),
    "Marcion": (85, 160),
    "Mark": (65, 75),
    "Ignatius of Antioch": (35, 108),
    "Hippolytus of Rome": (170, 235),
    "Dionysius": (190, 265),
    "Clement of Rome": (35, 99),
    "Peter": (1, 64),
    "Matthew": (70, 90),
    "Iranaeus": (130, 202),
    "Justin Martyr": (100, 165),
    "Polycarp": (69, 155),
    "Pamphilus": (240, 309),
    "Archelaus": (250, 300),
    "Peter of Alexandria": (250, 311),
    "pseudo-Peter": (100, 200),
    "Venantius": (530, 609),
    "Simeon Metaphrastes": (900, 1000),
    "Moses of Chorene": (410, 490),
    "Aristides": (124, 150),
    "Rufinus": (344, 411),
    "Gregory of Nyssa": (335, 395),
    "Cyril of Jerusalem": (313, 386),
    "Lucian": (125, 180),
}

# A few titles/works deliberately given a BCE-inclusive synthetic range,
# for testing purposes -- some of these (e.g. parts of the Testament of
# the Twelve Patriarchs) do have real BCE-dating arguments in scholarship,
# others here are just picked to exercise the mechanic. Not to be relied on.
FORCED_BCE_TITLES = {
    "Testament of the Twelve Patriarchs": (-180, 50),
    "The Testaments of the Twelve Patriarchs": (-180, 50),
    "Odes of Solomon": (-50, 100),
    "Revelation of Esdras": (-100, 100),
}


def deterministic_range(key: str, low=-400, high=500, min_width=10, max_width=50):
    """Stable pseudo-random (start, end) window derived from a hash of `key`,
    so the same author/title always gets the same synthetic dates."""
    h = hashlib.md5(key.encode("utf-8")).hexdigest()
    n1 = int(h[:8], 16)
    n2 = int(h[8:16], 16)
    span = high - low
    start = low + (n1 % span)
    width = min_width + (n2 % (max_width - min_width + 1))
    return (start, start + width)


def format_year(y: int) -> str:
    if y < 0:
        return f"{abs(y)} BCE"
    if y == 0:
        return "1 BCE"
    return f"{y} CE"


def display_range(y1: int, y2: int) -> str:
    return f"{format_year(y1)} – {format_year(y2)}"


def make_own_record(record_id: str, author_raw: str, title_raw: str, text: str, ecw_id: str = ""):
    """Build one 'own' (full-text) record, sharing the same date-assignment
    logic regardless of whether it came from the original JSONL export or a
    contributor's spreadsheet row."""
    author_raw = (author_raw or "").strip()
    title = (title_raw or "").strip() or "Untitled"
    text = text or ""

    author_display = author_raw if author_raw else "Unknown / Anonymous"
    date_key = author_raw if author_raw else title

    if title in FORCED_BCE_TITLES:
        y1, y2 = FORCED_BCE_TITLES[title]
    elif author_raw in KNOWN_RANGES:
        y1, y2 = KNOWN_RANGES[author_raw]
    else:
        y1, y2 = deterministic_range(date_key)

    return {
        "id": record_id,
        "author": author_display,
        "title": title,
        "ecw_id": ecw_id,
        "text": text,
        "year_start": y1,
        "year_end": y2,
        "year_display": display_range(y1, y2),
        "source": "own",
    }


def load_sheet_records():
    """Pull contributor-submitted rows from a published Google Sheet (CSV
    export link), and turn each into an 'own' record -- full text shown,
    same as the original JSONL export, just added by someone filling in a
    spreadsheet row instead of editing JSON by hand.

    Configured via sheet_config.json: {"csv_url": "https://docs.google.com/.../pub?output=csv"}
    That file is NOT a secret -- publishing a sheet "to the web" already
    makes it reachable by anyone with the link, so the URL is safe to check
    into the repo. If the file is missing, empty, or still has the
    placeholder URL, this simply contributes zero records (so the pipeline
    still works before anyone's set a sheet up).

    Expected columns (header row, any order): author, title, text.
    A row's id is derived from a hash of its author+title, so re-running
    this after someone fixes a typo in the "text" column keeps the same
    permalink -- but editing the title changes the id, since that's the
    only stable handle we have without asking contributors to manage IDs.
    """
    if not SHEET_CONFIG.exists():
        return []

    try:
        config = json.loads(SHEET_CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Warning: sheet_config.json is not valid JSON -- skipping sheet import.")
        return []

    csv_url = (config.get("csv_url") or "").strip()
    if not csv_url or "PASTE" in csv_url.upper():
        print("No sheet configured yet (sheet_config.json has no real csv_url) -- skipping.")
        return []

    try:
        with urllib.request.urlopen(csv_url, timeout=30) as response:
            raw_bytes = response.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Warning: could not fetch the sheet ({e}) -- continuing without it.")
        return []

    text_content = raw_bytes.decode("utf-8-sig")  # sheet exports often have a BOM
    rows = list(csv.DictReader(io.StringIO(text_content)))

    records = []
    skipped = 0
    for row in rows:
        # Normalize header casing/whitespace so "Author" / "author " etc. all work.
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        author = row.get("author", "")
        title = row.get("title", "")
        text = row.get("text", "")

        if not (author or "").strip() and not (title or "").strip() and not (text or "").strip():
            continue  # blank row, e.g. a trailing empty line in the sheet
        if not (text or "").strip():
            skipped += 1
            continue  # no snippet text -- nothing to publish yet

        key = f"{(author or '').strip()}|{(title or '').strip()}"
        record_id = "sheet-" + hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
        records.append(make_own_record(record_id, author, title, text))

    if skipped:
        print(f"Sheet: skipped {skipped} row(s) with no text yet.")

    return records


def load_harland_records():
    """Load the partner (Harland) sample: metadata only, never full text.

    Raw data was pulled from Harland's public WordPress REST API
    (philipharland.com/Blog/wp-json/wp/v2/posts) for the ethnic-relations
    category tree, one representative sample per category (this is a POC,
    not the full ~750-post corpus). Each entry's ancient author and a
    coarse year range were read off its title (e.g. "early first century
    CE", "fourth century BCE on") by hand -- these are real attributions,
    not synthetic placeholders like the "own" side's dates, but the year
    ranges are deliberately coarse (century-level) rather than precise.
    The 15 "Guide to [Author]" posts (a separate navigational category)
    were excluded as finding aids rather than ethnographic content.
    """
    if not HARLAND_SRC.exists():
        return []

    raw = json.loads(HARLAND_SRC.read_text(encoding="utf-8"))
    records = []
    for item in raw:
        y1, y2 = item["year_start"], item["year_end"]
        records.append({
            "id": f"harland-{item['id']}",
            "author": item["author"],
            "title": item["title"],
            "ecw_id": "",
            "text": "",
            "year_start": y1,
            "year_end": y2,
            "year_display": display_range(y1, y2),
            "source": "partner",
            "original_url": item["link"],
        })
    return records


def main():
    records = []
    skipped = 0
    with open(SRC, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            ecw_id = rec.get("ecw_id") or ""
            record_id = f"r{i:04d}-{ecw_id}" if ecw_id else f"r{i:04d}"
            records.append(make_own_record(record_id, rec.get("author"), rec.get("title"), rec.get("text"), ecw_id))

    jsonl_count = len(records)
    sheet_records = load_sheet_records()
    records.extend(sheet_records)

    harland_records = load_harland_records()
    records.extend(harland_records)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUT} (skipped {skipped} bad lines)")
    print(f"  own, from manual_3.jsonl (full text): {jsonl_count}")
    print(f"  own, from the contributor spreadsheet (full text): {len(sheet_records)}")
    print(f"  partner / Harland (metadata only): {len(harland_records)}")

    authors = sorted({r["author"] for r in records})
    bce = [r for r in records if r["year_start"] < 0 or r["year_end"] < 0]
    print(f"Unique authors: {len(authors)}")
    print(f"Records with a BCE-touching range: {len(bce)}")


if __name__ == "__main__":
    main()
