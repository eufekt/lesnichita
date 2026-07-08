# lesnichita.info

Personal site of Nichita Hariton. Plain HTML + CSS, no build step, no dependencies.

## Structure

- `public/` — the entire site (static files). This folder is the deploy artifact and is portable to any static host.
- `wrangler.jsonc` — Cloudflare Workers static assets config, with the `lesnichita.info` custom domain.
- `.github/workflows/deploy.yml` — deploys to Cloudflare on every push to `main`.

## Deploy manually

```sh
npx wrangler deploy
```

Requires being logged in with `npx wrangler login`.

## CI

Pushes to `main` deploy automatically via GitHub Actions. Secrets required on the repo:

- `CLOUDFLARE_API_TOKEN` — token with "Edit Cloudflare Workers" permissions
- `CLOUDFLARE_ACCOUNT_ID`
