# CreateFB Clones

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
label, rebuilds, zipaligns, and signs every clone with the same key.

## Update the source app

Replace `original.apk` with the new version and push - fresh clones are built.
Keep the same signing key (repo secrets `CLONE_KEYSTORE_*`) and clones update
in place without losing data.

## Limits

- Clones share one signature that differs from the original, so they install
  *next to* the original, never *over* it.
- Apps that check their own signature or package id (banking, some Google
  login flows) may refuse to run as clones.
