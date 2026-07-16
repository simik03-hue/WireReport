# The Wire Report — automation

This folder contains the site (`index.html`) plus a script that keeps it
stocked with fresh headlines automatically.

## If your laptop can't run Python locally (old OS, etc.) — start here

You don't need to run anything on your own machine. Everything below can be
done from a normal web browser, using GitHub as the place both your site
and its automation live and run.

**1. Create a free GitHub account** at github.com if you don't have one.

**2. Create a new repository**
   - Click the **+** in the top right → **New repository**
   - Name it something like `wire-report`
   - Set it to **Public** (required for free GitHub Pages)
   - Click **Create repository**

**3. Upload these files** — no command line needed:
   - On your new repo's page, click **Add file → Upload files**
   - Drag in everything from this folder (`index.html`, `README.md`,
     `requirements.txt`, and the `config/`, `scripts/`, `data/`, and
     `.github/` folders, keeping their names/structure — GitHub's uploader
     preserves folder paths when you drag a whole folder in from your
     file explorer)
   - Click **Commit changes**

**4. Turn on GitHub Pages** (this makes your site live on the web)
   - Go to **Settings → Pages** in your repo
   - Under "Build and deployment," set **Source** to "Deploy from a branch"
   - Pick branch `main`, folder `/ (root)`, click **Save**
   - GitHub gives you a URL like `https://yourusername.github.io/wire-report`
     within a minute or two — that's your live site

**5. Turn on the automation**
   - Go to the **Actions** tab in your repo
   - You'll see the "Fetch headlines" workflow (from `.github/workflows/fetch.yml`)
     — click it, then click **Enable workflow** if prompted
   - Click **Run workflow** once manually to test it immediately, rather than
     waiting for the timer
   - Check the run's log — if it succeeds, you'll see `data/wire_data.json`
     get updated in your repo automatically. It'll then keep running every
     15 minutes on its own, forever, without your laptop needing to be on

**6. Edit your source list anytime, from the browser**
   - Open `config/feeds.json` in your repo, click the pencil/edit icon,
     make changes, commit — no local editing needed
   - Each entry is one RSS feed:
     ```json
     {
       "name": "Reuters",
       "url": "https://feeds.reuters.com/reuters/topNews",
       "topic": "top",
       "lean": "center",
       "note": "Wire service, editorially independent, widely used as a baseline source."
     }
     ```
   - `topic` controls which column/section it lands in: `top`, `politics`,
     `world`, or `business`.
   - `lean` and `note` power the hover tooltip on each source tag.
   - **Important:** RSS endpoints change or get discontinued without
     notice. The URLs shipped in `feeds.json` are a starting point — verify
     each one actually resolves before relying on it. Most outlets list
     their current feed URL on an "RSS" or "Follow us" page, or search
     `"[outlet name]" RSS feed`. Google News also exposes free feeds at
     `https://news.google.com/rss/search?q=YOUR+QUERY` for topic-based
     feeds rather than a single outlet.

That's the whole setup. Everything from here on is optional background for
if you ever do want to run things locally (e.g. from a different, newer
machine, or a VPS).

---

## Folder structure

```
wire-automation/
├── index.html              the website (open this / deploy this)
├── config/
│   └── feeds.json          list of RSS sources — edit this to change what you aggregate
├── scripts/
│   └── fetch_feeds.py      fetches feeds, dedupes, writes the JSON below
├── data/
│   ├── wire_data.json      generated: current homepage content
│   └── archive.json        generated: rolling daily headline history
├── .github/workflows/
│   └── fetch.yml           the GitHub Actions schedule — runs fetch_feeds.py in the cloud
└── requirements.txt
```

## Running it locally instead (optional — only if you have a machine that supports it)

```bash
pip install -r requirements.txt --break-system-packages
```

(Drop `--break-system-packages` if you're using a virtual environment, which
is the cleaner option if you're comfortable with `python3 -m venv`.)

## Running it locally instead (optional — only if you have a machine that supports it)

**Install:**
```bash
pip install -r requirements.txt --break-system-packages
```
(Drop `--break-system-packages` if using a virtual environment.)

**Configure your sources** in `config/feeds.json` — see the field
explanation two sections up (`topic`, `lean`, `note`), same rules apply.

**Run it once, manually:**
```bash
python3 scripts/fetch_feeds.py
```

**Preview the site locally** — browsers block `fetch()` of local files
opened directly from disk, so serve it instead:
```bash
python3 -m http.server 8000
```
Then open `http://localhost:8000`.

**Automate it on a schedule** — if the site lives on your own Linux
server/VPS instead of GitHub Pages:
```bash
crontab -e
```
```
*/15 * * * * cd /path/to/wire-automation && /usr/bin/python3 scripts/fetch_feeds.py >> logs/fetch.log 2>&1
```
Or, most shared hosts and platforms-as-a-service (Render, Railway,
PythonAnywhere) have a built-in "scheduled task" feature in their dashboard
that does the same thing without cron.

## Publishing on Hostinger

1. hPanel → **Websites → Manage** → **File Manager** → open `public_html`
2. Upload this whole folder as a zip, then **Extract** it
3. Make sure `index.html` ends up directly inside `public_html` (not nested
   in a subfolder) — move files up a level if the extraction created one
4. Visit your domain — the site is live

### Populating headlines — manual way

Edit `data/wire_data.json` directly in Hostinger's File Manager (right-click
→ Edit). See `data/wire_data.json.example` in this folder for the exact
shape to follow — copy it, rename it to `wire_data.json`, replace the
example headlines/URLs with real ones, save. The homepage picks it up on
next load, no redeploy needed.

### Populating headlines — automated way (via the GitHub Actions pipeline)

The `.github/workflows/fetch.yml` workflow already fetches and de-dupes
headlines on a schedule (see the earlier setup steps above). To also push
that fresh data to your live Hostinger site automatically, it now includes
an FTP deploy step. You need to give it your Hostinger FTP credentials as
GitHub repo secrets:

1. In hPanel, go to **Files → FTP Accounts** and note the FTP server
   address, username, and password (or create a new FTP account there)
2. In your GitHub repo, go to **Settings → Secrets and variables →
   Actions → New repository secret** and add three secrets:
   - `HOSTINGER_FTP_SERVER`
   - `HOSTINGER_FTP_USERNAME`
   - `HOSTINGER_FTP_PASSWORD`
3. Re-run the workflow (Actions tab → Run workflow) — it will fetch new
   headlines, commit them to your repo, *and* upload `data/wire_data.json` +
   `data/archive.json` straight to `public_html/data/` on Hostinger

From then on, every scheduled run keeps your live Hostinger site's
headlines current with zero manual work.

## Keep in mind

- **Links only, never full text.** The script pulls headline + link, which
  is standard aggregator practice. Don't extend it to scrape and republish
  full article bodies — that's copyright infringement, not aggregation.
- **AdSense wants some of your own writing, too.** A pure auto-generated
  link list tends to read as thin content to reviewers. Consider adding a
  short human-written blurb, "editor's note," or short original post
  alongside the automated feed — it materially helps approval odds.
- **The `sponsored` section in `index.html` is never touched by this
  script** — it's manually edited, by design, so paid placements stay
  clearly separated from editorial content.
- **Tune `DEDUPE_SIMILARITY_THRESHOLD`** in `fetch_feeds.py` (currently
  `0.5`) if you notice too many near-duplicate stories slipping through, or
  too many distinct stories getting collapsed together.
