#!/usr/bin/env python3
"""Apply Voipstudio Remote Support branding to a RustDesk source tree.

Run from the repository root, after `git submodule update --init` (hbb_common is
patched in its working tree; it is not forked). Every edit is an exact-anchor
replacement with an expected count, so an upstream change that moves an anchor
fails here loudly instead of producing a half-branded build.

    VS_VARIANT=full|quicksupport python3 branding/apply.py

quicksupport = incoming-only client for customers (can be controlled, cannot
connect out); full = normal client for support staff.
"""
import os
import re
import shutil
import sys

APP_NAME = "Voipstudio Remote Support"
# Linux only: package, binary, systemd unit and config dir. Must equal what the
# `directories` crate derives from APP_NAME on Linux (lowercase, spaces removed),
# because linux.rs builds `~/.config/<name>` itself in one place.
SLUG = "voipstudioremotesupport"
ORG = "com.voipstudio"
BUNDLE_ID = "com.voipstudio.remotesupport"
RENDEZVOUS = "remote.voipstudio.com"
PUB_KEY = "2L7VKp5r5asEgHlrAxIhkRtOGJe7vXDkpKeIKh+lssY="
COMPANY = "Level 7 Network Limited"
COPYRIGHT = ("Based on RustDesk, Copyright © Purslane Tech Pte. Ltd. (AGPL-3.0). "
             "Modifications Copyright © 2026 Level 7 Network Limited.")

VARIANT = os.environ.get("VS_VARIANT", "full")
if VARIANT not in ("full", "quicksupport"):
    sys.exit(f"VS_VARIANT must be full or quicksupport, not {VARIANT!r}")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
failures = []


def edit(path, old, new, count=1, regex=False):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    found = len(re.findall(old, text)) if regex else text.count(old)
    if found != count:
        failures.append(f"{path}: expected {count} x {old!r}, found {found}")
        return
    text = re.sub(old, new, text) if regex else text.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def asset(src, *dests):
    for d in dests:
        if not os.path.exists(d):
            failures.append(f"asset target missing (upstream moved it?): {d}")
            continue
        shutil.copyfile(os.path.join(HERE, "assets", src), d)


# --- identity, server, key (hbb_common) ---------------------------------------
cfg = "libs/hbb_common/src/config.rs"
edit(cfg, 'APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
     f'APP_NAME: RwLock<String> = RwLock::new("{APP_NAME}".to_owned());')
edit(cfg, 'ORG: RwLock<String> = RwLock::new("com.carriez".to_owned());',
     f'ORG: RwLock<String> = RwLock::new("{ORG}".to_owned());')
edit(cfg, 'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];',
     f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{RENDEZVOUS}"];')
edit(cfg, r'pub const RS_PUB_KEY: &str = "[A-Za-z0-9+/=]{44}";',
     f'pub const RS_PUB_KEY: &str = "{PUB_KEY}";', regex=True)
if VARIANT == "quicksupport":
    edit(cfg, "pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
         'pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new('
         'HashMap::from([("conn-type".to_owned(), "incoming".to_owned())]));')

# --- never auto-update to stock RustDesk ---------------------------------------
# check_software_update() already returns early for a renamed app (is_custom_client);
# the Windows background updater does not, so guard it the same way.
edit("src/updater.rs", "fn check_update(manually: bool) -> ResultType<()> {\n",
     "fn check_update(manually: bool) -> ResultType<()> {\n"
     "    if crate::is_custom_client() {\n        return Ok(());\n    }\n")

# --- Linux: internal names must be one token --------------------------------------
# These build shell commands / process matches / unit names from the lowercased app
# name; with spaces they break (systemctl gets three args, grep matches nothing).
edit("src/platform/linux.rs", "crate::get_app_name().to_lowercase()",
     "crate::get_app_name().to_lowercase().replace(' ', \"\")", count=9)
edit("src/core_main.rs", '.arg(&format!("{} --tray", crate::get_app_name().to_lowercase()))',
     '.arg(&format!("{} --tray", crate::get_app_name().to_lowercase().replace(\' \', "")))')
edit("flutter/linux/CMakeLists.txt", 'set(BINARY_NAME "rustdesk")', f'set(BINARY_NAME "{SLUG}")')
edit("flutter/linux/CMakeLists.txt", 'set(APPLICATION_ID "com.carriez.flutter_hbb")',
     f'set(APPLICATION_ID "{BUNDLE_ID}")')
# build.py: only the Flutter .deb packaging and its control file
start = open("build.py", encoding="utf-8").read()
fn = re.search(r"\ndef build_flutter_deb\(version, features\):\n.*?\n(?=\n\S)", start, re.S)
ctl = re.search(r"\ndef generate_control_file\(version\):\n.*?\n(?=\n\S)", start, re.S)
if not fn or not ctl:
    failures.append("build.py: build_flutter_deb / generate_control_file not found")
else:
    body = fn.group(0)
    for a, b in [
        ("'cp ../res/rustdesk.service tmpdeb/usr/share/rustdesk/files/systemd/')",
         f"'cp ../res/rustdesk.service tmpdeb/usr/share/{SLUG}/files/systemd/{SLUG}.service')"),
        ("usr/share/rustdesk", f"usr/share/{SLUG}"),
        ("tmpdeb/usr/bin/rustdesk", f"tmpdeb/usr/bin/{SLUG}"),
        ("apps/rustdesk.png", f"apps/{SLUG}.png"),
        ("apps/rustdesk.svg", f"apps/{SLUG}.svg"),
        ("applications/rustdesk.desktop", f"applications/{SLUG}.desktop"),
        ("applications/rustdesk-link.desktop", f"applications/{SLUG}-link.desktop"),
    ]:
        if a not in body:
            failures.append(f"build.py build_flutter_deb: anchor {a!r} missing")
        body = body.replace(a, b)
    cbody = ctl.group(0)
    if "Package: rustdesk\n" not in cbody:
        failures.append("build.py generate_control_file: 'Package: rustdesk' missing")
    cbody = cbody.replace("Package: rustdesk\n", f"Package: {SLUG}\n").replace(
        "Description: A remote control software.", f"Description: {APP_NAME}")
    open("build.py", "w", encoding="utf-8").write(
        start.replace(fn.group(0), body).replace(ctl.group(0), cbody))
for f in ("res/DEBIAN/postinst", "res/DEBIAN/postrm", "res/DEBIAN/preinst", "res/DEBIAN/prerm"):
    text = open(f, encoding="utf-8").read()
    if "rustdesk" not in text:
        failures.append(f"{f}: no 'rustdesk' to rename")
    open(f, "w", encoding="utf-8").write(re.sub(r"\brustdesk\b", SLUG, text))
svc = open("res/rustdesk.service", encoding="utf-8").read()
svc = svc.replace("Description=RustDesk", f"Description={APP_NAME}")
svc = re.sub(r"\brustdesk\b", SLUG, svc)
open("res/rustdesk.service", "w", encoding="utf-8").write(svc)
for f in ("res/rustdesk.desktop", "res/rustdesk-link.desktop"):
    text = open(f, encoding="utf-8").read()
    text = text.replace("Name=RustDesk", f"Name={APP_NAME}")
    text = re.sub(r"\brustdesk\b", SLUG, text)
    open(f, "w", encoding="utf-8").write(text)

# --- product strings ---------------------------------------------------------------
edit("Cargo.toml", 'ProductName = "RustDesk"', f'ProductName = "{APP_NAME}"')
edit("Cargo.toml", 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{APP_NAME}"')
edit("Cargo.toml", 'LegalCopyright = "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved."',
     f'LegalCopyright = "{COPYRIGHT}"')
edit("Cargo.toml", '[package.metadata.bundle]\nname = "RustDesk"\nidentifier = "com.carriez.rustdesk"',
     f'[package.metadata.bundle]\nname = "{APP_NAME}"\nidentifier = "{BUNDLE_ID}"')
rc = "flutter/windows/runner/Runner.rc"
edit(rc, 'VALUE "CompanyName", "Purslane Tech Pte. Ltd." "\\0"', f'VALUE "CompanyName", "{COMPANY}" "\\0"')
edit(rc, 'VALUE "FileDescription", "RustDesk Remote Desktop" "\\0"', f'VALUE "FileDescription", "{APP_NAME}" "\\0"')
edit(rc, 'VALUE "LegalCopyright", "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved." "\\0"',
     f'VALUE "LegalCopyright", "{COPYRIGHT}" "\\0"')
edit(rc, 'VALUE "OriginalFilename", "rustdesk.exe" "\\0"', f'VALUE "OriginalFilename", "{APP_NAME}.exe" "\\0"')
edit(rc, 'VALUE "ProductName", "RustDesk" "\\0"', f'VALUE "ProductName", "{APP_NAME}" "\\0"')
xc = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
edit(xc, "PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {APP_NAME}")
edit(xc, "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb", f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}")
edit("build.py", "service ./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/'",
     f"service \"./build/macos/Build/Products/Release/{APP_NAME}.app/Contents/MacOS/\"'")

# --- icons and logo ------------------------------------------------------------------
asset("app.ico", "res/icon.ico", "flutter/windows/runner/resources/app_icon.ico")
asset("tray.ico", "res/tray-icon.ico")
asset("icon-1024.png", "res/icon.png")
asset("mac-1024.png", "res/mac-icon.png")
asset("AppIcon.icns", "flutter/macos/Runner/AppIcon.icns")
asset("mac-tray-dark-x2.png", "res/mac-tray-dark-x2.png")
asset("mac-tray-light-x2.png", "res/mac-tray-light-x2.png")
asset("icon-32.png", "res/32x32.png")
asset("icon-64.png", "res/64x64.png")
asset("icon-128.png", "res/128x128.png")
asset("icon-256.png", "res/128x128@2x.png")
asset("icon-tile.svg", "res/scalable.svg", "res/logo.svg", "flutter/assets/icon.svg")
for name in ("logo.png", "logo_light.png", "logo_dark.png"):   # optional, read by _resolveLogoAsset
    shutil.copyfile(os.path.join(HERE, "assets", name), os.path.join("flutter/assets", name))

if failures:
    print("BRANDING FAILED:\n  " + "\n  ".join(failures), file=sys.stderr)
    sys.exit(1)
print(f"branding applied: {APP_NAME} ({VARIANT}), server {RENDEZVOUS}")
