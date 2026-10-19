# Advanced Snap installation

For an existing installation with working dependencies, see [Update the extension](../README.md#update-the-extension). This guide covers runtime preparation and manual installation.

**A fresh Snap installation still needs a compatible MKVToolNix runtime. This repository does not download or bundle it.** The steps below assume you can supply those binaries and libraries.

The commands below install into Snap VLC's data directory and provide a launcher
for its helper dependencies. Runtime compatibility depends on the Snap revision;
check dependencies inside confinement as described below. These commands are an
alternative to `install_snap.py` when preparing dependencies manually.

Run host commands from this project's directory as your normal user. If VLC is
not installed, install it with `sudo snap install vlc`. Launch Snap VLC once so
its user directories exist, then close it before installing the extension.

**1. Prepare the helper dependencies on the host.** Snap uses a different runtime
environment, so installing host packages alone is insufficient. Store the helper
runtime under Snap's revision-independent user `common` directory:

```sh
sudo apt install python3 python3-pip
mkdir -p "$HOME/snap/vlc/common/video-metadata-runtime/python"
python3 -m pip install --target "$HOME/snap/vlc/common/video-metadata-runtime/python" -r requirements.txt
```

Supply a compatible staged MKVToolNix runtime containing the binaries and their
required shared libraries. Replace `/absolute/path/to/mkvtoolnix` with its actual
location. The destination `mkvtoolnix` directory should not already exist:

```sh
cp -a /absolute/path/to/mkvtoolnix \
  "$HOME/snap/vlc/common/video-metadata-runtime/mkvtoolnix"
```

The staged runtime is not included in this repository. The destination must use
this layout:

```text
video-metadata-runtime/mkvtoolnix/usr/bin/mkvextract
video-metadata-runtime/mkvtoolnix/usr/bin/mkvpropedit
video-metadata-runtime/mkvtoolnix/usr/bin/mkvinfo
video-metadata-runtime/mkvtoolnix/usr/lib/x86_64-linux-gnu/
```

Include `mkvinfo` for Super Playlist, which reuses this runtime to read MKV titles
and durations. Metadata Pro itself uses `mkvextract` and `mkvpropedit`.

This example is for x86-64 Linux. Match the libraries to the Snap's base/runtime,
not just the host distribution; adjust the library directory for other
architectures. There is currently no automated downloader for this runtime.

**2. Copy the helper launcher.** Run this on the host from the project directory:

```sh
install -m 755 launcher.sh "$HOME/snap/vlc/common/video-metadata-runtime/python-launcher"
```

`/usr/bin/python3` here means the interpreter visible **inside the Snap**. If that
interpreter is missing, provide a compatible Python runtime accessible to the
Snap and adjust the launcher's `exec` line. A host virtual environment is not
necessarily usable inside confinement.

**3. Check dependencies inside Snap before installing.** Open a confined shell:

```sh
snap run --shell vlc
```

In that shell, run:

```sh
"$SNAP_USER_COMMON/video-metadata-runtime/python-launcher" -c 'import sys, mutagen, subprocess; print(sys.version); print("Mutagen", mutagen.version_string); subprocess.run(["mkvextract", "--version"], check=True); subprocess.run(["mkvpropedit", "--version"], check=True); subprocess.run(["mkvinfo", "--version"], check=True)'
exit
```

All four dependency version checks must succeed. Missing libraries, an unavailable Python
interpreter, or `GLIBC_* not found` errors mean the staged runtime needs fixing;
copying the Lua extension alone will not fix those errors. Checking Snap's
libraries with the host Python is not equivalent to running inside confinement.

**4. Install from the host, then restart Snap VLC.**

```sh
python3 install.py \
  --data-dir "$HOME/snap/vlc/current/.local/share/vlc" \
  --python "$HOME/snap/vlc/common/video-metadata-runtime/python-launcher"
```

Open **View > Video Metadata Pro 1.00** and try loading and saving disposable copies of
both an MP4 and an MKV. Use **Check status** after each operation. Confirm the
values by reopening the files in the extension and check that backups exist.

The installed presets and job logs are under:

```text
~/snap/vlc/current/.local/share/vlc/lua/extensions/video_metadata_support/config/
~/snap/vlc/current/.local/share/vlc/lua/extensions/video_metadata_support/jobs/
```

If an operation never finishes, inspect its job's `worker.log`. For file access
failures, check `snap connections vlc` and the file/directory write permissions.
The helper needs permission to create temporary files and backups beside the
video, in addition to permission to read it.

The installer preserves the `current` symlink in the helper path so it follows
Snap revision updates. Keep the runtime under `common` in place, and repeat the
dependency check if a Snap update changes the runtime. Presets are preserved on
reinstall.

See Snap's [environment variable documentation](https://snapcraft.io/docs/environment-variables)
for `snap run --shell`, `SNAP_USER_COMMON`, and revision-specific user directories.

