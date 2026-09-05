# How to add an entry (no coding required)

This is the everyday guide — for adding a new snippet to the site once someone
technical has done the one-time setup in `README.md`. If that setup hasn't
happened yet, none of this works yet; ask whoever set the project up.

## 1. Open the spreadsheet

Ask the project's technical contact for the link to the Google Sheet, if you
don't already have it. It has three columns: **author**, **title**, **text**.

## 2. Add a new row

Fill in one row per entry:

- **author** — the ancient author's name, spelled the way it's spelled
  elsewhere in the sheet if this author already appears (e.g. always
  "Chrysostom", not sometimes "John Chrysostom"). Leave it blank for an
  anonymous work — it'll show up on the site as "Unknown / Anonymous."
- **title** — the title of the work (or a short descriptive title if the work
  doesn't really have one).
- **text** — the actual snippet, pasted in full. A row with nothing in this
  column is skipped automatically, so it's safe to jot down author/title now
  and paste the text in later.

You don't need to fill in a date — that gets assigned automatically based on
the author, the same way it already works for the rest of the collection.

Take your time and double check spelling before moving on — see the note on
IDs below for why that matters.

## 3. Ask for it to be published

New rows do **not** appear on the site automatically. Once you've added and
double-checked a row (or a batch of them), tell whoever has access to the
project's GitHub repo, so they can publish it:

1. Go to the repo on GitHub and click the **Actions** tab.
2. Click **Publish site** in the left-hand list.
3. Click the **Run workflow** button, then **Run workflow** again to confirm.
4. Wait a minute or two — the little dot next to the run turns into a green
   checkmark when it's done. That's the site rebuilt and redeployed with your
   new entry included.

If you have GitHub access yourself, you can do this last step directly —
no coding involved, just those clicks.

## A note on fixing mistakes

- **Fixing a typo in the text** and republishing is completely safe — it
  updates the same entry.
- **Changing the title** creates what the site treats as a brand-new entry
  (its web address is derived from author + title). If an entry already has a
  title and needs a small correction, mention it to your technical contact
  first rather than editing it yourself, so it doesn't silently duplicate.
- **Deleting a row** removes that entry the next time someone publishes.
