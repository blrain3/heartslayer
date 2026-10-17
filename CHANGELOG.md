# Changelog

## Init

- Initial heartslayer-kit operations and verification toolkit.

## PR #1

- Add installable project metadata, contributor guidance, and an English docs overview.
- Add CLI help and error handling, ignore common editor files, and document verification commands.

## 0.2.0

- Migrate `blrain3/bottled_ai` (`verify-localization-fix`) via `git subtree --squash` into `heartslayer/`.
- Rename package `rs` → `heartslayer` across all imports; `rg` audit confirms zero residual `rs` references.
- Delete `heartslayer/ops/heart-batch/` (duplicate scripts); retain root `scripts/` and `tools/` enhanced versions.
- License compliance: retain dual `LICENSE` (root + `heartslayer/LICENSE.md`), add `NOTICE.md` attribution.
- Add `pyproject.toml` (`flit_core>=3.9`, `name=heartslayer`, `dependencies=[spirecomm>=0.3]`).
- Update `README.md`: standalone bot documentation with CommunicationMod setup instructions.
- Verification: `bash -n scripts/*.sh`, `python3 -m compileall`, import test `from heartslayer.ai...`.

Strategies preserved: `claw_is_law`, `observant_heartslayer`, `peaceful_pummeling`, `pwnder_my_orbs`, `requested_strike`.
