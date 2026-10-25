# Voipstudio Remote Support branding

This branch (`voipstudio`) is RustDesk with Voipstudio branding applied at build time.
Upstream source is left untouched in git; `.github/workflows/voipstudio-build.yml`
runs `branding/apply.py` straight after checkout.

* `apply.py` — name, server (`remote.voipstudio.com`) and key, product strings, Linux
  package/binary/unit names (`voipstudioremotesupport`), updater guard, icons. Every edit
  is an exact-anchor replacement that fails if upstream moved it.
  `VS_VARIANT=quicksupport` additionally makes the client incoming-only.
* `assets/` — generated from `assets/source-logo.svg` by `render-icons.js` (Playwright /
  headless Chromium) plus PIL for the `.ico`/`.icns` containers.

Source: this is a modified version of RustDesk (https://github.com/rustdesk/rustdesk),
licensed AGPL-3.0; the full corresponding source is this repository.

## Upgrading to a new upstream tag

    git fetch upstream --tags
    git rebase --onto <new-tag> 1.5.0 voipstudio
    python3 branding/apply.py   # any moved anchor is reported here
    git checkout -- . && git submodule foreach git checkout -- .

then bump `VERSION` (and any toolchain versions upstream changed) in the workflow.
