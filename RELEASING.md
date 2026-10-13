# Releasing

A release is a pushed `vX.Y.Z` tag. It starts `.github/workflows/release.yml`, which runs four
jobs, each only when the one before it passed:

1. **cells**: asks tox for the full list of cells (the `full` label in `tox.toml`).
2. **matrix**: runs every cell.
3. **build**: fails when the tag disagrees with `version` in `pyproject.toml` (`v1.0.0` needs
   `1.0.0`), then runs `uv build`.
4. **publish**: uploads the distributions to PyPI through trusted publishing, so no API token
   is stored anywhere.

The workflow does not create a GitHub Release page; step 8 below does.

## Each release

1. On a release branch, set `version` in `pyproject.toml` to `X.Y.Z` and add a
   `## [X.Y.Z] - <date>` section to `CHANGELOG.md`. Merge it into `main` with CI green.
2. Update your local `main`:
   ```bash
   git checkout main
   git pull
   ```
3. Check that the date in the CHANGELOG section is today. If it isn't, fix it through a small
   pull request first.
4. Tag the merge commit with an annotated tag:
   ```bash
   git tag -a vX.Y.Z -m "X.Y.Z"
   ```
5. Push the tag. This starts the release; pushing `main` alone does not.
   ```bash
   git push origin vX.Y.Z
   ```
6. Watch *Actions → Release*. If the environment has a required reviewer, approve the publish
   job when it asks.
7. Check https://pypi.org/project/pytest-django-admin-kit/ and install the release in a fresh
   virtual environment:
   ```bash
   pip install pytest-django-admin-kit==X.Y.Z
   ```
8. Create the GitHub Release from the tag, with the version's CHANGELOG section as its notes,
   through *Releases → Draft a new release*, or:
   ```bash
   gh release create vX.Y.Z --title "X.Y.Z" --notes "<the X.Y.Z section of CHANGELOG.md>"
   ```

## When something fails

- **The matrix or the build fails.** Nothing has reached PyPI. Fix it through a pull request,
  then delete the tag and repeat steps 2 to 5:
  ```bash
  git tag -d vX.Y.Z
  git push origin :vX.Y.Z
  ```
  This deletes the tag; it is not a force-push.
- **The publish job fails.** Nothing has reached PyPI. Fix the cause the job reports and
  re-run the failed job from the Actions page; no new tag is needed.
- **A broken release is already on PyPI.** That version is final: PyPI never accepts the same
  version twice, even after it is deleted. Release the fix as the next patch version, with a
  version bump and a new tag.
