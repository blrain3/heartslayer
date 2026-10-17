# Contributing

## Lint and verification

Run the repository's local syntax checks before submitting changes:

```bash
bash -n scripts/*.sh && python3 -m compileall scripts tools
```

Keep changes within the requested scope. Do not edit the Chinese battle reports or `.github/workflows/lint.yml` as part of routine toolkit changes.

## Commits

Use a short Conventional Commit subject in the form `type: imperative summary`, for example `feat: add CLI help`. Keep each commit focused and include the relevant files only.

## Dry runs

Use `./scripts/launch-batch.sh N --dry-run` to exercise the launch gates without starting a game batch. Do not launch a real batch as part of routine verification.
