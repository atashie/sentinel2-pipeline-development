# Vercel hosting for the presentation, 2026-09-11

The presentation is prepared for sharing as a static site, following the weather assessment repository's pattern.
Status on 2026-09-11: configuration exists. No deployment URL or verified deployment is recorded.

## Layout

Vercel serves this `docs/` directory as the site root. [vercel.json](vercel.json) routes `/` to [s2-options.html](s2-options.html), skips installation and building, and serves the directory as is.
The page loads its images from `assets/discovery/` by relative path and requests nothing external. It deploys unchanged.
Every file under `docs/` becomes readable on the web: the inventory, the reviews, the survey report, and the map provenance. `docs/archive/` is ignored by git and is not deployed.
Markdown files are served as source text, not as formatted pages. Direct links from the page reach those files. Links inside Markdown that leave `docs/` require a repository checkout or GitHub view.

## First deployment

1. Sign in to the owner's existing Vercel account.
2. Confirm the account can read the `atashie/sentinel2-pipeline-development` repository on GitHub.
3. Publish the reviewed files to GitHub once the owner authorizes the commit.
4. In Vercel, add a new project and import the repository. Name it `sentinel2-pipeline-development`.
5. Set the root directory to `docs` and the framework preset to Other.
6. Leave the install and build commands empty. Set the output directory to `.`.
7. Confirm the production branch and the deployment access setting, then deploy.
8. Open the assigned URL and run the checks below.
9. Record the project, source revision, URL, and verification outcome in a dated review.

The root directory is a project setting. The configuration file supplies the rest.

## Updating

1. Finish the edits and the review cycle for the step.
2. Run `uv run python tools/render_options.py` and the check workflow.
3. Commit and push when the owner authorizes it. Vercel deploys the pushed revision.
4. Open the deployment before sharing the link again.

Vercel serves the committed HTML. It does not run the renderer. Uncommitted local changes never reach a deployment.

## Verification

- Open `/` and `/s2-options.html` and confirm the update date in the footer.
- Open a deep link such as `/#aws` and confirm the Discovery tab opens at that section.
- Switch all four tabs and both map views.
- Open the provenance link and one repository document link.
- Check a phone-width layout.
- Confirm access from a signed-out browser, subject to the chosen access setting.

References: [Vercel static configuration](https://vercel.com/docs/project-configuration/vercel-json), [deployment protection](https://vercel.com/docs/deployment-protection).
