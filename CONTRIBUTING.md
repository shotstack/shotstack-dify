# Contributing

## Develop

- Python 3.12 or newer: `pip install -r requirements.txt`.
- Offline tests (Shotstack's API is mocked, no key needed): `python -m unittest tests.test_shotstack`
- Live check against the free Sandbox: `SHOTSTACK_SANDBOX_KEY=<your Sandbox key> python tests/live_check.py`.
  The plugin itself only calls Production; this script points it at the Sandbox so the check is free. Use a Sandbox
  key only. The script makes one throwaway template and deletes it.
- Try it in Dify: copy `.env.example` to `.env`, fill in the debugging host and key from Dify (Integrations > Debugging),
  then run `python -m main`. Restart it after every change.

## Pull requests

- **One PR is one revertible change.** Unrelated fixes go in separate PRs. Renames, formatting and dependency bumps
  go in their own PR.
- **Under 400 changed lines.** Over that, say why in the description.
- **Nothing goes straight to `main`.** Branch off `main` and open a PR.
- **Title:** imperative, says what the change makes true: "Return the file URL when a template render finishes".
- **Description:** under 200 words. Lead with why. Add only what the diff does not say: a decision a reviewer would
  question, a constraint, a migration note. Then `Verify:` (the command or test that proves it) and, if it matters,
  `Risk:` (what breaks if it is wrong, and the rollback). The template in `.github/` has the shape.
- **Commits:** one line, semantic, no body, no AI attribution.
- **Add, never change.** Workflows depend on tool names, parameter names and output fields. Add new ones. Do not rename,
  remove or change the meaning of an existing one. If a change is unavoidable, do it in three PRs: add the new,
  move users over, remove the old.
- **No internal context.** This repo is public: no ticket IDs, internal system names or internal reasoning in code
  comments, commits or PRs.

## Release a new version

1. Raise `version` in `manifest.yaml` and `VERSION` in `shotstack_api.py` together (leave `meta.version`: it is the
   manifest format version), and add an entry to `CHANGELOG.md`. Merge that by PR.
2. From the folder above this one: `dify plugin package ./shotstack-dify`.
3. Validate the `.difypkg` with `validator/validate-difypkg.py` from
   [dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit).
4. Open a PR to [langgenius/dify-plugins](https://github.com/langgenius/dify-plugins) as a "Version update": add the new
   package to `shotstack/shotstack/` and remove the old one (Dify keeps only the current version). One package per PR.
