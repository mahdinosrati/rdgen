# RDGen, a RustDesk client generator to use with your self-hosted RustDesk server

## This fork: GitHub Pages + serverless Windows builds

Open [the configuration editor](https://mahdinosrati.github.io/rdgen/).
No Django server is required for Windows 64-bit builds:

1. Fill in the client options, Host, Relay Server, port and public key.
2. Click **Generate Custom Client** to download encrypted `payload.json`.
3. Click **Upload to GitHub**, upload that file and commit directly to `master`.
4. The upload workflow starts the Windows build automatically. Download
   `windows-client-…` from the completed generator run's **Artifacts** section.

No personal access token is required. Sign in to GitHub with write access to
this repository to upload the file. GitHub Pages cannot authorize builds by
itself; the GitHub upload/commit is the authorization step.

The editor removes duplicate image fields and encrypts the configuration and
original PNGs with AES-256-GCM, wrapping its random key with the repository's
RSA-OAEP public key. Upload only encrypted `payload.json`, never your original
configuration. Actions moves the encrypted input to a temporary branch and
removes it from master; the temporary branch is deleted after the build.
Encrypted content remains in Git history. Configurations up to 15 MB are
accepted without resizing images. Small configurations can still use the
manual `config_json` workflow input.
Downloaded clients necessarily contain their preset password, so avoid private
passwords in public builds even though the upload itself is encrypted.
Other platforms still use the Django service described below.

Fork maintainers must provision their own `RDGEN_PRIVATE_KEY` Actions secret and
matching public JWK in `web/build-key.json` before using encrypted uploads.

### Network behavior

A nonempty Relay Server field overrides any manual `relay-server` setting;
leave it blank to retain manual configuration or server discovery. Use
`relay.example.org:21117` or `[IPv6]:21117`.

The host, port, public key and API URL are embedded in `override-settings` for
every connection direction and permission mode, replacing stale local network
settings. Put only a hostname/IP in **Host** and use the separate **Port** field.
IPv6 is supported. The API field is optional for RustDesk OSS servers; an omitted
API no longer invents a `host:21114` service. Bare API hostnames are normalized to
`http://`; enter `https://` explicitly for TLS. Explicit Network fields take
precedence over the same keys in manual settings. A relay override can be entered
as `relay-server=host:port` in Override settings.

Builds now stop if upstream network constants cannot be patched, instead of
silently producing a client pointed at the public server. The Windows x86 custom
configuration filename and LAN discovery/auto-disconnect setting placement are
also corrected.

### Development and publication

```sh
pip install -r requirements.txt
python manage.py test
python scripts/build_pages.py
python -m http.server --directory dist 8765
```

The Pages workflow tests the Python configuration path and publishes `dist/` on
pushes to `master`. Repository Settings → Pages must use **GitHub Actions**.

The client generator is currently hosted [here](https://rdgen.crayoneater.org).
If you would like to host the generator yourself, see [here](setup.md)

## rustdesk api server integration

The rdgen client generator is integrated into my fork of the [rustdesk-api](https://github.com/bryangerlach/rustdesk-api). This is currently a work in progress, and might have bugs.

## rdgen local build alternative

If you would prefer to build rustdesk on your own computer, check out the [DVForge](https://github.com/VenimK/DVForge) project.

## Features

- Embed server and key into client
- Custom app name
- Custom icon/logo
- Set default settings for the client
- Support for rustdesk advanced settings (https://rustdesk.com/docs/en/self-host/client-configuration/advanced-settings/)

## Generate RustDesk clients from command line instead of using a web browser

Save your configuration from the rdgen web interface, or generate your own, then use that json file with [@AlekseyLapunov's rdgen-cli](https://github.com/AlekseyLapunov/rdgen-cli) to build from the command line on Windows, Linux, or MacOS like this: `python rdgen-cli -f my_config.json --set-version 1.4.5 --set-platform windows -s https://rdgen.crayoneater.org`

## Notes

- Icons should be square (256x256 recommended)
- Avoid special characters or non-English characters in app name and file name
- Build time is currently 30 - 45 minutes

