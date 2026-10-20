# lesnichita.info

Personal site of Nichita Hariton. Visitors get plain HTML and CSS.

## Structure

- `public/` — the entire site (static files). This folder is the deploy artifact and is portable to any static host.
- `public/projects.json` — project catalog. The homepage lists these under work.
- `public/projects/<slug>/` — one static page per project. The folder name is the slug.
- `scripts/sync-projects.py` — the publish step that reads the catalog and Are.na, then writes the pages. GitHub Actions runs it.
- `wrangler.jsonc` — Cloudflare Workers static assets config, with the `lesnichita.info` custom domain.
- `.github/workflows/deploy.yml` — publishes to Cloudflare on every push to `main`, and every hour if an Are.na channel changed.

## Projects

Each entry in `public/projects.json` has:

- `slug` — page address, `/projects/<slug>/`
- `title`
- `description`
- `date` — displayed as written (`2021`, `2021-03`, …)
- `tags` — list of strings; an empty list is omitted on the page
- `meta_image` — a direct image URL, or an Are.na block URL such as `https://www.are.na/block/10298222`
- `arena_channel` — optional Are.na channel URL. The project page shows that channel's images.

`scripts/sync-projects.py` runs when the site is published, not in the browser. It reads each `arena_channel` from Are.na (`GET /v3/channels/:slug/contents`, in the channel's own order) and writes the HTML. Stills use Are.na's resized images. A file over 2 MB, including this channel's gif, is saved as a still; the animation loads only if that still is opened.

Are.na does not send a notice when a channel changes. The publish workflow checks the channel every hour and deploys again only if something changed. A push to `main` publishes immediately. The workflow can also be started by hand from the Actions tab.

To add a project, add an object to `projects.json` and push. Edit the catalog, not the generated HTML.

## Deploy manually

```sh
npx wrangler deploy
```

Requires being logged in with `npx wrangler login`.

## CI

Pushes to `main` deploy automatically via GitHub Actions. Secrets required on the repo:

- `CLOUDFLARE_API_TOKEN` — token with "Edit Cloudflare Workers" permissions
- `CLOUDFLARE_ACCOUNT_ID`
