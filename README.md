# DH snippet database — proof of concept

A working test of the architecture from the planning document: a fully static site
(Eleventy) with client-side search and filtering (Pagefind) — no server, no database.
It now combines **two sources**, exactly like the real project is meant to:

- **Own data** (401 records) — your export of early Christian text snippets
  (`manual_3.jsonl`), full text shown, one page per record.
- **Partner data** (37 records) — a sample from Philip Harland's *Ethnic Relations
  and Migration in the Ancient World* database (philipharland.com/Blog), pulled from
  his site's public WordPress REST API across the ethnic-relations category tree.
  Only **title, author, and date range** are shown; there is no text to show because
  none was fetched. Every partner card/page carries a blue "Partner data — Harland
  database" badge and links out to the entry on his own site instead of a page here.

**Dates are synthetic on the "own" side, real-but-coarse on the partner side.** The
"own" data has no date field at all, so every record there got a placeholder
`year_start`/`year_end` (see `transform.py`) purely to test the year-range filter —
some deliberately pushed into BCE. The partner data's dates are real, read off each
post's title (e.g. "early first century CE"), but only to century-level precision —
treat those as approximate, not the "own" side's synthetic ones.

There's now a **third source**, too: a Google Sheet that lets non-technical
collaborators add "own" entries (full text shown) without touching JSON or a
terminal — see `HOW-TO-ADD-AN-ENTRY.md` for that workflow, and "Setting up the
automation" below for the one-time technical setup it depends on.

## What's in here

- `manual_3.jsonl` — your original export, unmodified.
- `harland_data.json` — the raw partner sample: id, title, link, author, and
  year_start/year_end for 37 posts across 8 of Harland's ethnic-relations categories
  (a representative sample, not the full ~750-post corpus — this is a POC). The 15
  "Guide to [Author]" posts (a separate navigational category) were left out as
  finding aids rather than ethnographic content, and two entries about modern
  reception of ancient imagery (not primary ancient sources) were also excluded.
- `sheet_config.json` — points `transform.py` at a published Google Sheet CSV link
  (see "Setting up the automation"). Ships with a placeholder URL, which
  `transform.py` treats as "no sheet configured yet" and simply skips.
- `sheet-template.csv` — import this into a new Google Sheet to get the right
  columns (`author`, `title`, `text`) immediately.
- `transform.py` — converts `manual_3.jsonl`, the configured Google Sheet, **and**
  `harland_data.json` into `site/_data/records.json`, the flat data model the site
  is built from (`id`, `author`, `title`, `text`, `year_start`, `year_end`,
  `year_display`, `source`, and `original_url` for partner records). Re-run it any
  time a source changes: `python3 transform.py [path-to-jsonl]`.
- `site/` — the Eleventy input: `records.njk` generates one page per record (branching
  on `record.source` for the partner display rules above), `search.njk` is the
  search/filter UI, `index.njk` is the home page.
- `.github/workflows/publish.yml` — the GitHub Action that pulls the sheet, rebuilds,
  and deploys, triggered manually from GitHub's Actions tab (see below).
- `.eleventy.js`, `package.json` — build configuration.

## Running it yourself

```
npm install
npm run build          # Eleventy -> _site/
npx pagefind --site _site   # generates the search index into _site/pagefind/
```

Then **serve `_site/` over HTTP** — Pagefind's index is fetched via JavaScript, which
browsers block over a plain `file://` URL. The simplest option:

```
cd _site && python3 -m http.server 8080
```

...then open `http://localhost:8080/`. (Any static file server works — `npx serve`,
VS Code's Live Server extension, etc.)

## What to actually try on `/search/`

- Type a keyword (e.g. "baptism", "prison", "conscience") — full-text search across
  every snippet.
- Type into the small box above the author list (e.g. "chrys", "aug") — it narrows the
  checkbox list live instead of making you scroll ~50 names, then check one or more
  to filter.
- Enter a year range, including negative numbers for BCE (e.g. `-300` to `-50`) — a
  snippet matches if its own (synthetic) date range overlaps the range you type at
  all, even without any keyword typed.
- Combine all three at once; "Clear all filters" resets everything.

## Setting up the automation (one-time, technical)

This turns "someone edits JSON in a terminal" into "someone fills in a
spreadsheet row and clicks a button." It's a few accounts and one config file,
done once, by whoever's setting the project up.

**1. Create the Google Sheet.**
Make a new Google Sheet and import `sheet-template.csv` (File → Import) so the
header row is exactly `author,title,text`. Share it with whoever will be
adding entries (edit access for them; you don't need to share it for this
step to work).

**2. Publish it as a CSV link.**
File → Share → **Publish to web**. Under "Link", choose the specific sheet
(not "Entire document"), and under the format dropdown pick **Comma-separated
values (.csv)**, then click Publish. Copy the URL it gives you — this is a
read-only, unlisted link (not indexed by search engines, but viewable by
anyone who has the exact URL). Paste it into `sheet_config.json` as the
`csv_url` value. This file is safe to commit to the repo — publishing already
made the sheet reachable at that link, so there's no secret to protect here.

**3. Put the project on GitHub.**
If you don't already have this code in a repo: create a new (private or
public, your choice) repository on GitHub, then from this project's folder:

```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

**4. Create a Cloudflare Pages project.**
In the Cloudflare dashboard, create a Pages project via a one-time manual
upload of the current `_site/` folder (any placeholder content is fine — the
Action will overwrite it). Note the exact project name Cloudflare assigns.

**5. Give the GitHub Action permission to deploy.**
In Cloudflare, create an API token with "Cloudflare Pages: Edit" permission,
and note your Cloudflare account ID (both are on the Cloudflare dashboard).
In the GitHub repo: Settings → Secrets and variables → Actions, and add two
**repository secrets**: `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
Then open `.github/workflows/publish.yml` and replace
`REPLACE-WITH-YOUR-PAGES-PROJECT-NAME` with the project name from step 4.

**That's it.** From here on, adding an entry is exactly the `HOW-TO-ADD-AN-ENTRY.md`
workflow: someone fills in a spreadsheet row, then a person with repo access
goes to the **Actions** tab, selects **Publish site**, and clicks **Run
workflow**. Nothing publishes automatically or on a timer — a human always
triggers it, which doubles as a chance to glance at the sheet before
publishing.

## Known simplifications, since this is a proof of concept and not the real build

- Only `author`, `text`, and the date range are wired up as filters, per your steer —
  no `genre`/topic facet, and no "stereotype about" / "stereotype from" facets yet
  (that extraction work is intentionally out of scope for this POC).
- The partner sample is 37 posts, not Harland's full corpus, and its author/date
  extraction was done by hand reading each title — good enough to prove the
  own/partner display split works, not a validated dataset.
- No CI, hosting, or Endings-compliance scaffolding (data dictionary, validation,
  versioned editions) — this is purely to prove the search/filter mechanics work
  against real data, not a deployable build.
- Blank `author` values in the "own" source (~76 records, mostly untitled
  Acts/Apocrypha texts) show as "Unknown / Anonymous" in the filter list; the same
  fallback is used for a handful of partner entries with no named ancient author
  (e.g. an inscription or artifact rather than a text).
- A sheet row's permalink ID is derived from a hash of `author + title`, so it's
  stable across re-publishes as long as those two fields don't change — editing
  `text` is always safe, but editing `title` after publishing creates what looks
  like a brand-new entry rather than updating the old one (see the note in
  `HOW-TO-ADD-AN-ENTRY.md`). There's no delete/edit history or approval queue
  beyond "someone glances at the sheet before clicking Run workflow."
- The sheet pipeline assigns dates the exact same way the JSONL import does
  (`KNOWN_RANGES` lookup by author name, else a deterministic hash-based
  placeholder) — so a sheet row for an author already in `KNOWN_RANGES` gets a
  sensible-looking range, but a new author gets the same kind of synthetic
  filler date as the rest of the "own" side, not a real one.
