# RDGen, a RustDesk client generator to use with your self-hosted RustDesk server

## This fork: GitHub Pages + serverless Windows builds

Open [the configuration editor](https://mahdinosrati.github.io/rdgen/).
No Django server is required for Windows 64-bit builds:

1. Fill in the client options and your RustDesk server host, port and public key.
2. Select **Copy build JSON**, then **Open GitHub Actions**.
3. Choose **Run workflow**, paste the JSON into `config_json`, and leave `zip_url` empty.
4. Download `windows-client-…` from the completed run's **Artifacts** section.

For large configurations, use **Generate Custom Client** with a fine-grained
GitHub token granting **Actions and Contents read/write** on this repository.
The editor removes duplicate image fields and encrypts the configuration and
original PNGs with AES-256-GCM, wrapping its random key with the repository's
RSA-OAEP public key. Only an encrypted payload goes into a temporary
`rdgen-inputs/…` branch; Actions decrypts it using `RDGEN_PRIVATE_KEY` and deletes
the branch after the build. Configurations up to 15 MB are accepted without
resizing images. The token is never saved or included in configuration exports.
Small configurations can still use the manual `config_json` workflow input.
Downloaded clients necessarily contain their preset password, so avoid private
passwords in public builds even though the upload itself is encrypted.
Other platforms still use the Django service described below.

Fork maintainers must provision their own `RDGEN_PRIVATE_KEY` Actions secret and
matching public JWK in `web/build-key.json` before using encrypted uploads.

### Network behavior

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

