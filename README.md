# lesnichita.info

Personal site of Nichita Hariton. Plain HTML + CSS, no build step, no dependencies.

## Structure

- `public/` — the entire site (static files). This folder is the deploy artifact and is portable to any static host.
- `public/projects.json` — project catalog. The homepage lists these under work.
- `public/projects/<slug>/` — one page per project. The folder name is the slug.
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

Are.na is read in the browser from the public API, with no token. Docs: [https://www.are.na/developers/explore](https://www.are.na/developers/explore).

- A block image is `GET https://api.are.na/v3/blocks/:id`.
- Channel contents are `GET https://api.are.na/v3/channels/:slug/contents`, following `meta.has_more_pages`. Order is `position_desc`, the same order as the channel page.
- GIFs use the original file so they stay animated. Other images use Are.na's resized versions.

To add a project, add an object to `projects.json` and copy `public/projects/a-la-recherche-des-textures/index.html` to `public/projects/<slug>/index.html`. Set that file's `<title>`, description, and canonical URL. The page body is filled from the catalog.

## Deploy manually

```sh
npx wrangler deploy
```

Requires being logged in with `npx wrangler login`.

## CI

Pushes to `main` deploy automatically via GitHub Actions. Secrets required on the repo:

- `CLOUDFLARE_API_TOKEN` — token with "Edit Cloudflare Workers" permissions
- `CLOUDFLARE_ACCOUNT_ID`
