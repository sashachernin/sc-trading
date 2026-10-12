# GitHub and Vercel deployment

Keep the monorepo private by default. Configure a dedicated publishing identity limited to this repository and contents read/write. A fine-grained token or scoped GitHub App is appropriate; repository scope does not provide per-folder permissions, so the publisher independently enforces its changed-path allowlist. Use a protected Linux credential helper; avoid credentials in remotes, command arguments, prompts or repository files.

Import the GitHub repository into Vercel. Project root: **frontend/**. Install: `npm ci`. Build: `npm run build`. Output: **out/**. Production branch: configured `PUBLISH_BRANCH` (default main). The Next.js static export pre-generates index, weekly and meeting routes from committed data. No DB, provider, engine or Codex secret belongs in the Vercel environment. Generated-only commits must trigger builds; do not configure ignored-build logic that skips `public/data` or articles.

Official references verified during implementation:

- [Vercel Git integration](https://vercel.com/docs/git/vercel-for-github)
- [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports)
- [Vercel deployment protection](https://vercel.com/docs/deployment-protection)
- [GitHub fine-grained credentials](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

Check the current hosting plan and protection scope. A private GitHub repo does not make the site private. Vercel's Standard Protection excludes production domains; select a method/scope that protects all production, preview/deployment and historical URLs. If private production coverage is unavailable, keep real-data publishing disabled. Public access requires explicit owner configuration `SITE_VISIBILITY=public`; never silently widen the audience.

## Synthetic smoke test

1. Build a separate synthetic experiment, export, inspect approved content and run static validation.
2. Use the independent publisher checkout with configured approved branch protections/author permissions.
3. With deployment protection already configured, anonymously request `/`, `/weeks/.../`, `/meetings/.../`, `/data/manifest.json`, a week JSON and `/transcripts/...md` through production and deployment URLs. None may return the underlying protected resource. Check the actual auth flow and access logs, not a UI badge.
4. Set `PRIVATE_ACCESS_VERIFIED=true` only after successful operator acceptance. Run `python -m app.cli publish-site`; record Git commit and PUSHED_UNVERIFIED.
5. Check the Vercel build, actual successful deployment and exact manifest snapshot. Set DEPLOYMENT_URL for automation if the private protected mechanism supports it. The initial checker performs unauthenticated requests and does not manufacture verification when protection rejects it.
6. Test a second generated-content-only revision and assert unchanged frontend source. Test a publication retry and a stale revision.

Repository/hosting permissions and real credentials are not available from this checkout. No live Git push or Vercel deployment is claimed by local build success. Token rotation: create a new narrowly scoped credential, update the Linux helper, test synthetic push, then revoke the old credential. Preserve branch rules; document the approved automation path instead of disabling checks.
