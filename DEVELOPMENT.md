# Developer universe

The repository uses Python 3.12+ standard library only. All profile numbers, languages, pinned repositories, recent pushes, and contributions come from GitHub at generation time. The README and SVGs are committed outputs, so GitHub's README renderer needs no script execution, hosting, or paid service.

## Generate locally

1. Export a token with access to public profile data: `export GITHUB_TOKEN=...`.
2. Run `python3 -m unittest discover -s tests -v`.
3. Run `python3 -m scripts.main`.

For a first local visual preview without GraphQL authentication, run `python3 -m scripts.main --public-preview`. It uses real public REST and GitHub Linguist data, and explicitly marks pinned and contribution content as awaiting the authenticated workflow. Run the normal command once a token is available.

The token must be able to read GitHub GraphQL `user.pinnedItems` and `user.contributionsCollection`. The scheduled workflow tries the built-in `github.token` first. If its GraphQL access is insufficient, create a fine-grained personal access token with **read access to public repositories and public profile data** and add it as repository secret `UNIVERSE_TOKEN`. A classic token with `read:user` is another option. No write token is required for data fetching; the workflow's built-in token performs the commit.

The generator fetches the entire snapshot before writing any file. API errors therefore leave the last successful README and assets intact. The workflow runs every six hours and on manual dispatch, serializes its jobs, and commits only changed generated files. Its `[skip ci]` commit does not trigger itself because the workflow has no push trigger.

## Data rules

- Repositories must be public, owned by the configured username, and not forked or archived unless configuration changes those filters.
- Language percentages use total bytes returned by each repository's REST `/languages` endpoint. Colors come from GraphQL repository language nodes. GitHub's own primary language determines which planet receives each repository moon. Unsupported or missing primary languages are omitted from the hero; their repositories remain in the fetched snapshot. Pinned cards always follow GraphQL's exact order.
- The heatmap uses the latest 26 weeks. The current year total starts January 1. The current streak ends today if there is a contribution, otherwise yesterday. The longest streak covers the fetched calendar-year window. GitHub's calendar day boundaries determine dates.
- Recent public push events come from GitHub's public events feed, which is limited by GitHub's event retention. Empty activity produces no comets.
- SVG animation uses SMIL without JavaScript. GitHub image sanitization or a viewer's reduced-motion setting can disable motion; the static image remains a valid SVG. Native GitHub README rendering must be checked after the first workflow run.

## Layout and limitations

The hero is 1200 × 720 SVG with a responsive Markdown image. Pinned cards are one per line to remain readable on narrow mobile views. SVG `image` elements embed the latest avatar. SVGs include no remote resources or credentials. The graphical language markers are colored planets rather than third-party icon downloads, keeping every asset self-contained. Public-only contributions may differ from totals visible to the profile owner when private contributions are enabled.

## Configuration

Edit `data/config.json` for visual density, limits, timing, inclusion rules, and professional text. Pinned repository names are never configured. After editing, run the tests and regenerate.
