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
| `work.html` | All 23 projects as a field guide (3 eras) |
| `about.html` | About page — draft copy with `.todo` markers |
| `press.html` | 16 verified press clippings |
| `writing.html` | Blog slot (feed-first) |
| `404.html` | Pizza slice with googly eyes |
| `project/` | 3 project detail pages (PTP, PtP, MoodMonitor) |
| `assets/` | CSS, JS, and images |

## Content updates

Edit the source files and commit:
- **Project details**: `content/projects/*.md` (MoodMonitor already updated with merger story)
- **Press data**: `_data/press.json`
- **About copy**: `about.html` — check for `.todo` dashed markers

## Custom domain

To use `scottduncombe.com` instead of `YOUR_USERNAME.github.io/scottduncombe.com/`:

1. Update DNS at your domain registrar:
   - `A` record `@` → `185.199.108.153` (and `109.`, `110.`, `111.`)
   - `CNAME` record `www` → `mojowen.github.io`
2. In GitHub repo Settings → Pages, set the custom domain `scottduncombe.com`
   and enforce HTTPS. **GitHub commits a `CNAME` file to the repo root.**
3. **Keep the deploy `rsync --delete` from ever removing it:**

   ```bash
   rsync -a --delete --exclude '.git' --exclude '.github' \
     --exclude 'DEPLOYMENT.md' --exclude 'package.json' \
     --exclude '.eleventy.js' --exclude 'README.md' \
     --exclude 'CNAME' \
     ~/Projects/scottduncombe-prototype/ ~/Projects/scottduncombe-github-site/
   ```

## No redirects needed from the old WordPress site

The old WP permalinks are preserved 1:1 by the directory layout —
`/project/<slug>/` serves `project/<slug>/index.html`, and `/about/`,
`/press/`, `/work/`, `/writing/` all exist as `*/index.html`. Once the A
records are repointed, spot-check a few old URLs (they should all be 200):

    /  /about/  /press/  /work/  /writing/
    /project/pizza-to-the-polls/  /project/moodmonitor/  /project/<slug>/…
1. Update GitHub Pages to serve from `main` → `/ (root)` (default)

2. The old WP URLs need 301 redirects. Create `_redirects` file:

   ```
   /project/pizza-to-the-polls/   /project/pizza-to-the-polls.html   301!
   /project/power-the-polls/      /project/power-the-polls.html      301!
   /project/moodmonitor/          /project/moodmonitor.html          301!
   /about                         /about.html                        301!
   /press                         /press.html                        301!
   ```

3. Or configure redirects at your domain registrar/CDN

## Notes

- This is a **static site** — no server-side processing
- All content is pre-rendered HTML
- Images are ~17MB total (scraped from the live site)
- Press data is in `content/projects/press.json` — can be updated via `collect_press.py` from the old theme

## Next steps after launch

1. **DNS switch**: Point `scottduncombe.com` to GitHub Pages
2. **SSL**: GitHub Pages handles HTTPS automatically
3. **Redirects**: Set up 301s from old WP URLs
4. **Analytics**: Add GA4 (the old UA-15235777-1 is not carried over)
5. **Blog**: Start writing posts in `content/writing/*.md`