# Deploy scottduncombe.com to GitHub Pages

This repo contains the static site for scottduncombe.com ready for GitHub Pages deployment.

## Quick start

1. **Create a new GitHub repo** (or use an existing one):
   - Name it `scottduncombe.com` (or your preferred repo name)
   - Make it public

2. **Push this code**:
   ```bash
   cd ~/Projects/scottduncombe-github-site
   git remote add origin https://github.com/YOUR_USERNAME/scottduncombe.com.git
   git push -u origin main
   ```

3. **Enable GitHub Pages**:
   - Go to repo Settings → Pages
   - Under "Source", select `main` branch → `/ (root)` → Save
   - GitHub will build and deploy (usually takes 1-2 minutes)

4. **Visit your site** at `https://YOUR_USERNAME.github.io/scottduncombe.com/`

## What's in this repo

| File/Folder | Purpose |
|-------------|---------|
| `index.html` | Home page — featured work, stat posters, press strip |
| `work/` | All 23 projects as a field guide (3 habitats) |
| `about/` | About page |
| `press/` | 16 verified press clippings |
| `writing/` | Blog slot (feed-first) |
| `resume/` | Redirect → `assets/docs/scott-duncombe-resume.pdf` |
| `404.html` | Pizza slice with googly eyes |
| `project/` | 23 project detail pages |
| `tools/check.py` | Static-site checks (run before every commit) |
| `assets/` | CSS, JS, images, resume PDF |

## Content updates

Edit the HTML directly (no build step — it's all pre-rendered), then:

```bash
python3 tools/check.py --root .   # links, feeds, style rules

git add -A && git commit -m "..." && git push   # push to main = deploy
```

- **Project details**: `project/<slug>/index.html` (23 pages)
- **Press**: `press/index.html`
- **About copy**: `about/index.html`

## Custom domain

To use `scottduncombe.com` instead of `YOUR_USERNAME.github.io/scottduncombe.com/`:

1. Update DNS at your domain registrar:
   - `A` record `@` → `185.199.108.153` (and `109.`, `110.`, `111.`)
   - `CNAME` record `www` → `mojowen.github.io`
2. In GitHub repo Settings → Pages, set the custom domain `scottduncombe.com`
   and enforce HTTPS. **GitHub commits a `CNAME` file to the repo root.**
3. **Working on the site:** this repo is the single source of truth —
   edit here, run `python3 tools/check.py --root .`, commit, push.
   (The old two-copy "prototype + rsync" workflow was retired 2026-10-30;
   the prototype directory is archived in `~/Projects-archive/2026-10-30/`.)

## No redirects needed from the old WordPress site

The old WP permalinks are preserved 1:1 by the directory layout —
`/project/<slug>/` serves `project/<slug>/index.html`, and `/about/`,
`/press/`, `/work/`, `/writing/` all exist as `*/index.html`. Once the A
records are repointed, spot-check a few old URLs (they should all be 200):

    /  /about/  /press/  /work/  /writing/  /resume/
    /project/pizza-to-the-polls/  /project/moodmonitor/  /project/<slug>/…

(The stale `_redirects` instructions that used to live here contradicted
this section — the directory layout covers every old WordPress URL.)

## Notes

- This is a **static site** — no server-side processing, no build step
- Images are ~17MB total (scraped from the live site)
- Run `tools/check.py` before every commit — it guards links, feeds, and style rules

## Next steps after launch

1. **DNS switch**: Point `scottduncombe.com` to GitHub Pages
2. **SSL**: GitHub Pages handles HTTPS automatically
3. **Redirects**: Set up 301s from old WP URLs
4. **Analytics**: Add GA4 (the old UA-15235777-1 is not carried over)
5. **Blog**: Start writing posts in `content/writing/*.md`