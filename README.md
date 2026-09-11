# DGDClone

CI that turns `original.apk` (`DGDcreateFB`, `com.dgd.createfb`) into **10 apps
that install side-by-side** with no external cloner:

| # | App name | Package id |
|---|----------|------------|
| 1 | DGDcreateFB 1 | `com.dgd.createfbc1` |
| ... | ... | ... |
| 10 | DGDcreateFB 10 | `com.dgd.createfbc10` |

## How to use

1. Push (or run the workflow manually) - CI builds all 10.
2. Download them from the `clones` artifact or the `clones-vN` Release.
3. Install any/all - each is a separate app with its own data.

## How it works

`clone.yml` decodes the APK with apktool, rewrites the manifest package +
label, pre-fills the reg-password default, stamps each clone's launcher icon
with its number badge, rebuilds, zipaligns, and signs every clone with the
same key.

## Launcher number badges

Each clone's icon carries a royal-blue (`#1D4ED8`) scalloped-seal badge with
its number (1-10), top-left inside the icon border (`badge_icons.py`,
reusable: `add_number_badge(icon, number)`):

- One fixed badge size/position for all numbers (wide enough for "10").
- Positioned circle-safe: the whole seal stays inside the launcher circle
  mask, so the number survives even circle-crop launchers.
- Original icon pixels outside the badge are untouched.
- The clone app labels (`DGDcreateFB 1` ... `DGDcreateFB 10`) double as the
  TalkBack accessible names; `badge_content_description()` builds the
  `"App name, number N"` form.

Run the badge checks locally (needs Pillow):

```
pip install pillow
python3 -m unittest discover -s . -p "test_*.py" -v
```

CI runs the same tests on every build, plus a `badge-preview` artifact
(contact sheet of badges 1-10, also committed under `preview/`).

## Update the source app

Replace `original.apk` with the new version and push - fresh clones are built.
Keep the same signing key (repo secrets `CLONE_KEYSTORE_*`) and clones update
in place without losing data.

## Limits

- Clones share one signature that differs from the original, so they install
  *next to* the original, never *over* it.
- Apps that check their own signature or package id (banking, some Google
  login flows) may refuse to run as clones.
