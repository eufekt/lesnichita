# lesnichita.info

Personal site of Nichita Hariton. Plain HTML + CSS, no build step, no dependencies.

## Structure

- `public/` — the entire site (static files). This folder is the deploy artifact and is portable to any static host.
- `public/projects.json` — project catalog. The homepage lists these under work.
- `public/projects/<slug>/` — one static page per project. The folder name is the slug.
- `scripts/sync-projects.py` — reads the catalog and Are.na, then writes those pages.
- `wrangler.jsonc` — Cloudflare Workers static assets config, with the `lesnichita.info` custom domain.
- `.github/workflows/deploy.yml` — deploys to Cloudflare on every push to `main`.

## Projects

Each entry in `public/projects.json` has:

- `slug` — page address, `/projects/<slug>/`
- `title`
- `description`
- `date` — displayed as written (`2021`, `2021-03`, …)
- `tags` — list of strings; an empty list is omitted on the page
- `meta_image` — a direct image URL, or an Are.na block URL such as `https://www.are.na/block/10298222`
- `arena_channel` — optional Are.na channel URL. The project page shows that channel's images.

Pages are static HTML. A visit does not call Are.na. Refresh them with:

```sh
python3 scripts/sync-projects.py
```

The script reads the public API ([docs](https://www.are.na/developers/explore)): `GET /v3/channels/:slug/contents`, in the channel's own order, and `GET /v3/blocks/:id` for a meta image that is not already in the channel. Stills use Are.na's small and medium renditions. A file over 2 MB, including this channel's gif, is saved as a still; the original loads only if that still is opened.

To add a project, add an object to `projects.json` and run the script. It writes `public/projects/<slug>/index.html` and the homepage list. Edit the catalog, not the generated HTML.

## Deploy manually

```sh
npx wrangler deploy
```

Requires being logged in with `npx wrangler login`.

## CI

Pushes to `main` deploy automatically via GitHub Actions. Secrets required on the repo:

- `CLOUDFLARE_API_TOKEN` — token with "Edit Cloudflare Workers" permissions
- `CLOUDFLARE_ACCOUNT_ID`
