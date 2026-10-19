# Metadata Pro for VLC

Edit **Artist, Album and Genre** in local **MP4 and MKV** videos using a Linux
VLC 3 extension. Type values or add them from configurable preset lists.

## License

Metadata Pro is licensed under the GNU General Public License version 2 only
(`GPL-2.0-only`). See [LICENSE](LICENSE) for the complete license text.
See [COPYRIGHT.md](COPYRIGHT.md) for copyright attribution and the scope of
these notices, including AI-generated material. Third-party dependencies
retain their own licenses.

## Getting started

1. [Install the extension](#installing-the-extension) for your VLC installation type.
   If it is already installed, see [Update the extension](#updating-the-extension).
2. Open a video, then choose **View > Metadata Pro**.
3. Click **Check status** until the existing values appear.

- [Load, edit and save](#load-edit-and-save)
- [Entering multiple values](#entering-multiple-values)
- [Saving and recovery](#saving-and-recovery)
- [Remove a video's backups](#remove-a-videos-backups)
- [Remove metadata values](#remove-metadata-values)
- [Add more preset choices](#add-more-preset-choices)
  - [Optional: create a preset with one click](#optional-create-a-preset-with-one-click)
  - [Edit the preset files directly](#edit-the-preset-files-directly)
- [Optional: include Genre values in Album](#optional-include-genre-values-in-album)
- [Diagnosing a freeze](#diagnosing-a-freeze)
- [Troubleshooting](#troubleshooting)
- [Version and build date](#version-and-build-date)
- [Create a clean installation package](#create-a-clean-installation-package)
- [Installing the extension](#installing-the-extension)
  - [Conventional Ubuntu/Debian VLC](#conventional-ubuntudebian-vlc)
  - [Snap VLC](#snap-vlc)
- [Updating the extension](#updating-the-extension)
  - [Conventional VLC](#conventional-vlc)
  - [Snap VLC with dependencies already installed](#snap-vlc-with-dependencies-already-installed)
- [Structure](#structure)
- [Keeping the editor accessible](#keeping-the-editor-accessible)
- [Tests](#tests)
- [Virtual machine installation (experimental)](#virtual-machine-installation-experimental)

## Load, edit and save

1. Open or play a local MP4 or MKV, or a playlist containing such files. You may
   leave it playing or pause it. Only MP4 and MKV files are currently supported;
   support for additional formats is planned.
2. Choose **View > Metadata Pro** (or **View > Metadata Pro > Show editor**
   when the extension is already active). If the dialog is already open, click
   **Load current video**. Check that the filename at the top is the video you want.
3. Click **Check status** until the status says **Loaded** and the fields appear.
   Clicking **Load current video** again also collects a pending load result.
4. Type space-separated values. Alternatively, select one or more presets and
   click **+ Add selected**; this appends them without duplicating existing values.
5. Click **Save changes**. Playback of the target stops; the worker saves in the background.
6. Click **Check status** until it reports that saving and verification succeeded.
7. The extension refreshes the saved video's cached Artist, Album and Genre
   when its VLC input item is available. Playback does not resume automatically.
   If Media Information still shows old values, close that window and reopen it;
   if necessary, remove the playlist entry and open the file again.

Changed fields and existing lists needing alphabetical sorting are written. With the Genre-to-Album option enabled,
Save may also update Album automatically. Remove individual values by editing the
text; to remove an entire field, select its **Clear on Save** checkbox. Emptying
the text alone does not delete a field. Selecting a preset never writes to disk.
Text inputs supply pending values unless **Clear on Save** is selected.

When VLC changes tracks, the dialog starts loading the new file if there are no
unsaved text edits or running saves. Clear on Save selections reset immediately
when the target file changes, even if text edits prevent switching. If you switch
during a save, collecting its successful
completion with **Check status** starts loading the latest selected file, provided
no new edits remain. Click **Check status** again to collect its values. Late load
results from a previous file are ignored. Abandoned load jobs are asked to stop;
video hashing checks cancellation between chunks. Submitted saves and backup
removal are never cancelled by navigation or closing. Unsupported items clear the old target.
You can also use **Load current video** to switch. Previous fields and preset list
selections reset as soon as a new load starts. **Discard edits** explicitly
restores the loaded values before switching. Edits made while a save runs remain in the
inputs as unsaved changes. Wait for a read operation before editing its results.
Closing the extension window always exits and discards unsaved edits. A save
already submitted continues in the background; closing does not cancel it.
Loading also works after playback stops: the extension uses VLC's current
playlist item, or its remembered file if VLC no longer has a current item.
If neither is available, open the video and pause it, then click **Load current video**.

## Entering multiple values

Separate values with spaces. Use underscores inside a name:

```text
Artist: Alice Björk The_Band
Album:  Summer_2025 Live_Recordings
Genre:  Rock Acoustic Live
```

`The_Band` is one value; `The Band` is two values. Repeated spaces are ignored.
On Save, values are sorted alphabetically ignoring case, with a case-sensitive
tie break. Exact duplicate values are removed; `Rock` and `rock` remain different
values. Save also sorts existing lists without requiring text edits.

An existing value containing whitespace, such as `The Beatles`, is flagged and
preserved when other fields change. Preset addition to that unchanged field is
blocked. To replace it, type explicit tokens, for example `The_Beatles`.

MP4 saves store Artist, Album, and Genre as single space-separated strings, with
private value-list records for lossless editing. Save also converts older repeated
MP4 values to this display format. Input still uses spaces, not commas.

MKV Genre also uses a space-separated display string with a private value-list
record, so VLC can display every saved genre. Save converts existing repeated
Genre values to this format even without text edits.

VLC's built-in Media Information view may display only part of repeated MKV Artist or Album tags or
format them differently. The extension reads complete supported lists directly
from the file. Real VLC GUI display of repeated values remains a manual
compatibility check; successful helper verification does not establish GUI display.

## Saving and recovery

A save copies the file beside the original, modifies that temporary copy, reads
back the requested values, creates a numbered backup (`.bak`, `.bak.1`, …), and
atomically replaces the original. Existing backups are never overwritten.
If VLC selects a `.mp4.bak`, `.mkv.bak`, or numbered backup from a folder,
Load current identifies it as a backup and shows the original video to open.
Backups are not editable targets. Save and Check status retain this explanation
until another load starts. Backups beside an original do not prevent loading it.
A failed edit or verification leaves the original intact. Backups are retained;
remove them with **Remove backups** when no longer needed. An interrupted backup copy may remain
incomplete, so check reported failures before relying on that backup.

Full copies and hashing take time on large videos and require roughly twice the
video's size in additional free space during saving. Metadata changes do not
re-encode audio or video. The worker checks that the source has not changed since
loading or during saving, and serializes jobs for each target within this
installation. Do not edit the same file concurrently using another program;
external programs do not participate in these locks. Symlink inputs are rejected.

Jobs and logs are under `video_metadata_support/jobs`. If a worker exits without
publishing a result, inspect its `worker.log`. Completed job directories can be
removed when the extension is idle. Closing VLC does not cancel an already
launched worker. After restarting, load the file again to read its current state.

## Remove a video's backups

The status field reserves six lines and expands for longer messages, so all
details are visible without paging. Click **Check status** to update it.

Keep backups until you have checked the saved tags. Each backup is a full copy
of the video, so repeated saves can consume substantial disk space.

1. Load the original video and click **Check status**.
2. Click **Remove backups**, then **Check status** to see the count, total size,
   and target filename.
3. Click **Confirm removal** to permanently delete those backups, or **Cancel
   removal** to keep them. Click **Check status** for the result.

This removes only regular sibling files named exactly `video.mp4.bak`,
`video.mp4.bak.1`, and so on (also for MKV). Symbolic links, directories, and
other filenames are excluded. The names identify candidates; files created
by another program using exactly the same names are included too. The original
video and unsaved editor text are unchanged. If the video or backup set changes
after review, cleanup requires a new preview. Navigating or starting another
operation cancels the confirmation. Removal already submitted runs to completion
even if you close the window. The next metadata save creates a backup again.

## Remove metadata values

1. Load the video and click **Check status** until its values appear.
2. Select **Clear on Save** beside Artist, Album, or Genre. You can select more
   than one field. The selected field's text is ignored when saving, and preset
   additions are blocked until you uncheck it. The text box remains editable.
3. Click **Save changes**, then **Check status** until saving and verification succeed.
   The cleared fields become empty and their checkboxes reset.
4. VLC's cached values are refreshed when the saved input item is available.
   If old values remain visible, close and reopen Media Information, or remove
   the playlist entry and open the file again.

Before saving, **Discard edits** unchecks all Clear boxes and restores the loaded
values. A failed save keeps the selections so you can inspect the error and retry
or discard. Checkbox changes made during a save remain pending edits; they do not
cancel an operation already submitted to the worker.

Clearing Album takes precedence over **Append sorted Genre values to Album on
Save** for that save. Clearing Genre also removes its matching appended suffix
from an Album carrying this extension's combined-Album record, even if appending
is now disabled. Other Album values and explicit Album replacements are kept.
The append option remains enabled for later saves unless you uncheck it.

Removal uses the same verified copy and backup process as other edits. To undo a
completed removal, close the video and restore its pre-save backup, keeping a copy
of the current file if it contains later changes you need.

Only the supported Artist, Album, and Genre values are removed. Unrelated tags
remain. For MKV, track-specific and localized tags and Album Artist are preserved;
nested metadata keeps its parent structure while the parent's own text value is
removed. Matching binary tags are rejected rather than deleted.

## Add more preset choices

### Optional: create a preset with one click

To enable quick creation, set `quick_tag_editing=true` in
`video_metadata_support/config/settings.txt`, then reopen the extension.
The supplied template enables it for fresh package installations. Existing
settings are preserved during updates; if the setting is absent or `false`,
the quick creation controls are hidden. Keep it enabled to add presets while
editing videos, or disable it if you prefer to maintain a fixed set of choices
in the preset files.

With a video loaded, type one value into **New artist**, **New album**, or
**New genre**, then click its **Add artist**, **Add album**, or **Add genre**
button. That single click saves the preset, refreshes that category's list,
and adds the value to the video's editable field. Each category is independent.
Use underscores instead of spaces, for example `New_Album`. Values cannot
start with `#` or contain control characters. Exact duplicates are reused;
capitalization remains significant.

Click **Save changes** to write the video metadata using the normal backup
process. **Discard edits** discards video edits but does not remove saved presets.
Quick creation waits until running operations finish and respects **Clear on
Save** and the protection for existing values containing whitespace. On a
configuration write failure, the input is retained for retry.

Saving preserves comments, `quick_tag_editing`, and other settings in
`settings.txt`; it updates only the Album/Genre option. A configuration lock
prevents two extension instances from writing the same config simultaneously.
Avoid editing a config externally at the same moment. If a crash leaves a
`*.txt.lock` directory, close all extension instances before removing that
stale lock and retrying.

### Edit the preset files directly

Preset lists use preset files. **They do not automatically collect values from your
videos.** The supplied Artist, Album, and Genre templates contain only commented
examples, so fresh package installations start with empty preset lists. Uncomment
example entries or add your own values to the installed files.

For Snap VLC, edit these files in a text editor (`~` means your home directory):

```text
~/snap/vlc/current/.local/share/vlc/lua/extensions/video_metadata_support/config/artists.txt
~/snap/vlc/current/.local/share/vlc/lua/extensions/video_metadata_support/config/albums.txt
~/snap/vlc/current/.local/share/vlc/lua/extensions/video_metadata_support/config/genres.txt
```

For example, `artists.txt` could contain:

```text
Alice
Björk
The_Band
```

Save the text file, then click **Refresh presets** in the extension. Select a value
and click **+ Add selected** to append it to the editable field. Repeat to add more values,
then click **Save changes** to write the edited metadata to the video.

Use UTF-8 text, one whitespace-free value per line. File order determines preset list
order. Blank lines, lines starting with `#` (also after leading whitespace), and
exact duplicates are ignored. Comments must be on their own lines. Entries containing internal
whitespace are skipped. Missing or empty files leave that preset list empty.

For other installations, these files are under
`<VLC data>/lua/extensions/video_metadata_support/config/`. Edit the installed
files; the project's `config/` directory only supplies defaults for new installs.
The tracked `config/*.txt.example` files are documented templates. The installer
uses each template when the corresponding local `.txt` file is absent. To customize
a new deployment, copy a template (for example, `config/artists.txt.example` to
`config/artists.txt`) and edit the copy before installing. These local `.txt` files
are ignored by Git. Reinstallation never overwrites existing installed configs.

## Optional: include Genre values in Album

Enable **Append sorted Genre values to Album on Save**, then click **Save changes**.
The checkbox defaults to off and is remembered when saving. It works for both
MP4 and MKV, including when no text fields were edited.

For example, Album `album1 album2` and Genre `genre5 genre4` produce:

```text
Album: album1 album2 genre4 genre5
Genre: genre4 genre5
```

Album-only values are sorted alphabetically first. Current Genre values appear once at the end,
sorted alphabetically ignoring case (with a deterministic case-sensitive tie
break). Genre itself is also sorted alphabetically. Exact duplicates are removed; differently
cased values remain distinct. Repeated saves do not accumulate copies.

In this mode, Album is stored as one space-separated string so VLC can read the
whole Album value. A small custom metadata tag records the original value list
for lossless editing in the extension. Reopen the video in VLC to refresh its
cached metadata. This does not add a dedicated Genre filter to VLC.
The Snap smoke test in `tests/snap_smoke.py` checks that VLC's metadata reader
returns the complete combined Album string for both MP4 and MKV.

Unchecking the option stops appending; it does not remove previously saved Album
values by itself. While the option is enabled, changing Genre replaces its old
appended suffix; Clear on Save for Genre removes that suffix with either setting.
Automatic removal requires a valid combined-Album record and a suffix matching
the previously saved Genre values. For unmarked or externally changed Albums,
remove unwanted values explicitly in the Album input. An explicit Album edit
takes precedence. Changing Album with the option off restores normal field
storage and removes the combined-Album record. MP4 fields still
use space-separated display strings and their own value-list records.

The setting is stored in `video_metadata_support/config/settings.txt`:

```text
append_genre_to_album=false
```

Set it to `true` and reopen the extension, or use the checkbox and Save.
Reinstallation preserves this file, just like the preset files.

## Diagnosing a freeze

The installed `video_metadata_support/activity.log` records callback starts,
finishes, and stages such as playlist lookup, helper launch, playback stop, and
VLC metadata refresh. It records no tag contents or video paths. It rotates at
about 128 KiB to `activity.log.1`, retaining the previous log across restarts.
If VLC freezes again, note the approximate time; the last entries can help locate
where it stopped. A completed callback does not prove VLC's subsequent UI update
completed. Worker-specific details remain in `jobs/*/worker.log`.

## Troubleshooting

| What you see | What to do |
|---|---|
| The old video's filename is shown | Click **Load current video** after switching videos, then **Check status**. If prompted about edits, save them or click **Discard edits** first. |
| The filename is correct but fields have not loaded | Click **Check status** and read the status message. Loading runs in the background. |
| “No video is available” | Open the video and pause it, then click **Load current video**. |
| A preset list is empty or missing choices | [Edit the installed preset files](#edit-the-preset-files-directly) or [create presets with one click](#optional-create-a-preset-with-one-click), then click **Refresh presets** if needed. |
| Only one value appears in VLC's Media Information window | Check the extension's text field. VLC may display only part of repeated tags. The optional combined Album mode makes the full Album string available to VLC. |
| Playback stops on Save | This is expected. Loading and typing do not require stopping; Save stops the target video. Reopen it after saving finishes. |
| Genre values still appear in Album after disabling the option | Turning it off does not undo saved metadata. Remove unwanted Album values manually and save with the option off. |
| A job fails or never finishes | The status shows its `worker.log` path. It contains timestamps, operation/file details, and error tracebacks. |
| New controls or fixes do not appear | Follow [Update the extension](#updating-the-extension), then restart VLC. |
| Metadata Pro is missing from the View menu | Update the extension and fully restart VLC. A previous logging change prevented VLC from discovering it; the corrected version supports discovery before Lua's standard libraries are loaded. |

Each job has its own persistent `worker.log` and `result.txt`. For Snap VLC,
find them under:

```text
~/snap/vlc/current/.local/share/vlc/lua/extensions/video_metadata_support/jobs/<job-id>/
```

For conventional VLC, the default is:

```text
~/.local/share/vlc/lua/extensions/video_metadata_support/jobs/<job-id>/
```

A custom `--data-dir` or `XDG_DATA_HOME` changes that base directory. Worker logs
record reads, saves, completion, backup paths, and full Python error tracebacks.
They contain filenames; review them before sharing. Older versions may have empty
worker logs for handled errors; their `result.txt` still contains the URL-encoded
error message. Reinstall and restart VLC to enable the improved logging.

## Version and build date

[release.json](release.json) is the single source for the application version and
build date. Update it when preparing a release, then package and reinstall:

```json
{
  "version": "00.90 RC1",
  "build_date": "2026-10-19"
}
```

The build date identifies the prepared release, not the installation date. Use
`YYYY-MM-DD`; packaging and installation preserve it. The installer embeds both
values in the extension, including the version reported to VLC. Restart VLC after
reinstalling to see the new values. Editing this file alone does not update an
already installed extension.

Versions support two or three numeric components and an optional release-candidate
suffix, such as `00.90 RC1`. Increase the candidate number for each testing release
(`00.90 RC2`, etc.) and remove the suffix for the final release (`00.90`).
Leading zeroes are preserved exactly as written.

The version and build date appear at the top right of the editor.

## Create a clean installation package

From the source checkout, create a new folder containing only the installation
files:

```sh
python3 package.py /path/to/metadata-pro-install
```

The destination must not already exist. The package includes both installers,
the helper, VLC extension, `release.json`, default config templates, and
installation documentation.
Local presets and settings, tests, caches, and development files are excluded.
Copy the resulting folder to the target machine and follow the appropriate
installation steps below from that folder. Dependencies are installed separately;
Snap VLC still requires a compatible staged MKVToolNix runtime.

## Installing the extension

### Conventional Ubuntu/Debian VLC

Run the commands below from this project's directory. They are for conventional
VLC, not Snap VLC.

For conventional Ubuntu/Debian VLC, install the runtime dependencies:

```sh
sudo apt install vlc python3 python3-mutagen mkvtoolnix
python3 install.py
```

Mutagen 1.44.0 is the tested baseline, also pinned in `requirements.txt` for
pip-based environments. For a different interpreter or VLC data directory:

```sh
python3 install.py --python /absolute/path/to/python3 --data-dir /path/to/vlc-data
```

Restart VLC and select **View > Metadata Pro**. Installation copies the helper
and defaults into the VLC data directory; it does not require the source checkout
to stay in place. Reinstall after code changes. User preset files are preserved.

The installer defaults to `$XDG_DATA_HOME/vlc`, or `~/.local/share/vlc`.
It does not install into Snap automatically. Windows, macOS and Flatpak are
outside this MVP.

### Snap VLC

On a machine with a compatible staged MKVToolNix runtime and Mutagen available to
the installer's Python, launch Snap VLC once, close it, then run:

```sh
python3 install_snap.py --runtime /absolute/path/to/mkvtoolnix
```

The runtime directory must contain `usr/bin/mkvextract`, `usr/bin/mkvpropedit`,
`usr/bin/mkvinfo`, and the required libraries under `usr/lib/x86_64-linux-gnu`.
Metadata Pro uses `mkvextract` and `mkvpropedit`; `mkvinfo` is required in the
shared Snap runtime for Super Playlist to read MKV titles and durations. The installer copies
these into the VLC Snap profile and preserves existing presets and settings.

The staged runtime is not included in this repository, and there is no automatic
Snap runtime downloader. See [Advanced Snap installation](docs/snap-installation.md)
for preparation and dependency checks.

## Updating the extension

Wait for any pending save to finish, then close VLC completely. Obtain the latest
project files and run the appropriate commands below from the project directory.
Updates preserve existing presets and `settings.txt`.

### Conventional VLC

```sh
python3 install.py
```

If you originally used `--data-dir` or `--python`, supply the same options again.

### Snap VLC with dependencies already installed

Reuse the installed runtime under `~/snap/vlc/common/video-metadata-runtime`:

```sh
install -m 755 launcher.sh "$HOME/snap/vlc/common/video-metadata-runtime/python-launcher"
python3 install.py \
  --data-dir "$HOME/snap/vlc/current/.local/share/vlc" \
  --python "$HOME/snap/vlc/common/video-metadata-runtime/python-launcher"
```

These commands refresh the launcher, extension, and Python helper package without
copying the runtime again. If you customized the launcher's interpreter or library
paths, carry those changes into `launcher.sh` before copying it.
If the runtime is missing or needs replacement, follow [Snap VLC](#snap-vlc)
and provide a compatible staged runtime to `install_snap.py --runtime`.

Reopen VLC and choose **View > Metadata Pro**. Open a video, click **Load current video**
if needed, then **Check status** to confirm that the updated extension loads it.
Changes in the project directory take effect in VLC only after reinstalling and
restarting VLC.

## Structure

- `vlc/video_metadata.lua`: dialog, presets, field state and background launch.
- `helper/`: Python package with explicit relative imports.
- `run_worker.py`: entry point used by VLC in the checkout and installed support directory.
- `helper/worker.py`: request/result files and locking, with separate functions for
  the Album transformation and verified save transaction.
- `helper/mkv.py`: MKVToolNix extraction and XML merging.
- `helper/mp4.py`: Mutagen MP4 text atoms.
- `helper/album_values.py`: value-list record for the optional combined Album.
- `install.py`: installation and preservation of user configuration.
- `install_snap.py`: installation into Snap using an existing compatible runtime.
- `launcher.sh`: canonical Snap launcher, copied by the installer.
- `tests/fixtures.py` and `tests/vlc_stub.lua`: shared media fixtures and simulated VLC API.

| Field | MP4 atom | New MKV tag / target level |
|---|---|---|
| Artist | `©ART` | `ARTIST` / 30 |
| Album | `©alb` | `TITLE` / 50 |
| Genre | `©gen` | `GENRE` / 30 |

MKV updates preserve unrelated groups, nested information, track-specific and
localized tags. Existing matching scopes and legacy `ALBUM` tags are updated;
Album Artist at level 50 and the segment title are preserved. This is a focused
metadata editor, not a complete Matroska tag browser.

References: [Mutagen MP4 tags](https://mutagen.readthedocs.io/en/latest/api/mp4.html),
[MKVToolNix tag editing](https://mkvtoolnix.download/doc/mkvpropedit.html),
[VLC Lua API](https://raw.githubusercontent.com/videolan/vlc/3.0.x/share/lua/README.txt).

## Keeping the editor accessible

To keep Metadata Pro above other windows, open the **editor's own title-bar
menu** (usually right-click the title bar, or press **Alt+Space** while the
editor is focused) and select **Always on Top** or **Keep Above Others**, if your
Linux desktop provides that option. Select it again to turn it off. This is a
desktop window setting; availability and whether it persists after closing the
editor depend on your desktop. Full-screen windows may behave differently.

While the extension is active, VLC's **View > Metadata Pro** submenu provides:

- **Hide editor**: hide the window while retaining its fields and unsaved edits.
- **Show editor**: show it again without reloading the video or resetting edits.
- **Deactivate**: VLC's built-in action to close the extension and discard
  UI-only edits. The editor's close button and Escape also close the extension;
  use **Hide editor** to preserve edits.

If the editor is behind another window, choose **Hide editor**, then reopen the
submenu and choose **Show editor**. **Show editor** alone does not reliably bring
an already-visible window forward. For a minimized editor, restore it with the
desktop window switcher instead. Reinstall the extension and restart VLC to get
the new submenu.

GUI check on 2026-10-09 with Snap VLC and GNOME/X11: separate **Hide editor** and
**Show editor** actions brought the editor above maximized VLC and preserved an
unsaved Artist value. **Show editor** alone did not recall a covered or minimized
editor. A hide/show refresh inside a single callback also failed to raise the
covered editor; separate Hide/Show actions did not restore a minimized editor.
VLC 3's Lua API has no explicit raise/focus or always-on-top command, so desktop
window management remains necessary for those cases.

To check recall on your desktop: type an unsaved Artist value, cover the editor
with VLC, then choose **View > Metadata Pro > Show editor**. Check that the editor
comes forward with the value intact. If it stays covered, try **Hide editor**, followed by
**Show editor**, and repeat after minimizing the editor. Do not save the test
value; discard it or close the editor afterwards.

## Tests

Test dependencies are FFmpeg/ffprobe, MKVToolNix, Mutagen, and the Lua 5.2 shared
library (for example `liblua5.2-0`). Run:

```sh
python3 -m unittest discover -s tests -v
```

Tests generate disposable videos, exercise multi-value round trips and reductions,
Unicode, legacy whitespace preservation, scoped/nested MKV tags, backups,
changed-file rejection and failed verification. They compare audio/video packet
hashes and timestamps before and after saves. Video-only MP4 is covered.
Removal tests cover each field in both formats, empty fields, backup recovery,
legacy MP4 Genre tags, nested MKV metadata, and Genre-to-Album precedence.
Independent Lua tests use simulated widgets with the real installed background worker,
including preset addition, explicit clearing, unsaved-edit guards, and text and
checkbox changes made during a save.
They do not automate actual Qt widgets or validate Snap confinement.

## Virtual machine installation (experimental)

To install a desktop guest in GNOME Boxes and test Metadata Pro, follow the
[Arch Linux VM guide](docs/arch-linux-vm.md) or the
[Fedora VM guide](docs/fedora-vm.md).
