# Fedora guest in GNOME Boxes

This guide creates an x86_64 Fedora desktop VM for testing Metadata Pro with
native VLC 3. **Host** means your real computer running Boxes; **guest** means
the VM. Run commands in the guest unless marked otherwise. This is a test
procedure, not verified compatibility with every release.

Download a supported **Fedora Workstation Live x86_64 ISO** from the
[Fedora download page](https://fedoraproject.org/workstation/download/) and follow
its verification instructions.

## Create the VM on the host

1. Open **GNOME Boxes**, click **+ → Install from File**, and select the ISO.
   Record its filename and checksum with your test results.
2. Name the VM `fedora-metadata-pro`. Allocate **4 GiB RAM** (8 GiB if available) and a
   **40 GiB** virtual disk. Allow extra host space for snapshots, videos, and
   Metadata Pro's full video backups.
3. Click **Create** and boot the installation medium. Keep the default virtual
   network connection enabled.

Menu labels vary with the Boxes version. See
[GNOME's instructions for creating a box](https://help.gnome.org/gnome-boxes/create.html).
Use an x86_64 ISO on an x86_64 host for this procedure.

## Install Fedora inside the VM

From the live desktop, open **Install Fedora** or **Install to Hard Drive**.
The installer wording varies by release; recent Workstation releases use a
guided web-based interface. Follow these choices:

| Setting | Suggested choice |
| --- | --- |
| Language and keyboard | Your preferred locale and keyboard layout |
| Installation destination | The new 40 GiB virtual disk, usually `/dev/vda` |
| Installation method | Use the entire new virtual disk with automatic partitioning |
| Filesystem layout | Keep Fedora Workstation's default layout |
| Disk encryption | Optional for this test VM; retain the passphrase if enabled |

Partitioning erases the selected disk: select only the newly created VM disk.
Review the summary, start installation, and wait for it to finish. Fedora's
[guided empty-disk installation checklist](https://fedoraproject.org/wiki/QA:Testcase_partitioning_webui_guided_empty)
describes this installer path.

Shut down the live guest, eject the ISO in Boxes' device settings, and start the VM again. Complete the first-boot setup, including
your timezone and a normal user account with administrator access. Log in to
the installed desktop. Networking should use the virtual Ethernet connection;
there is no guest Wi-Fi setup when the host supplies NAT networking.

## Install Metadata Pro in the guest

Run these commands in a terminal **inside the installed Fedora desktop**:

```sh
sudo dnf upgrade --refresh
# Save snapshot 01 here if VLC is not already installed.
sudo dnf install vlc vlc-plugin-lua vlc-plugin-ffmpeg python3 python3-mutagen mkvtoolnix spice-vdagent
```

These are native RPM packages. Metadata Pro's current installer does not support
Flatpak VLC, so launch the RPM-installed VLC when testing.

Fedora provides the [Lua extension plugin](https://packages.fedoraproject.org/pkgs/vlc/vlc-plugin-lua/),
[FFmpeg plugin](https://packages.fedoraproject.org/pkgs/vlc/vlc-plugin-ffmpeg/),
[Mutagen](https://packages.fedoraproject.org/pkgs/python-mutagen/python3-mutagen/),
and [MKVToolNix command-line tools](https://packages.fedoraproject.org/pkgs/mkvtoolnix/mkvtoolnix/)
in its package repositories. The MKVToolNix package is named `mkvtoolnix` on
Fedora, rather than Arch's `mkvtoolnix-cli`.

Reboot after updating, then log back in. The
[SPICE guest agent](https://packages.fedoraproject.org/pkgs/spice-vdagent/spice-vdagent/)
provides guest integration with the SPICE channel present. Clipboard and
automatic resizing behavior can depend on the desktop session; they are not
required to install or use Metadata Pro.

Prepare a clean package on the host using the
[README packaging instructions](../README.md#create-a-clean-installation-package).
Archive the resulting folder and record its SHA-256 checksum. Transfer the
archive by dragging it into the running Boxes guest, or use **Send File** if
available. Inside the guest, check `xdg-user-dir DOWNLOAD` for the destination,
verify the archive's checksum with `sha256sum`, then extract it into
`~/installers`. A transfer notification alone is not proof that the file arrived.

Alternatively, configure a [Boxes shared folder](https://help.gnome.org/gnome-boxes/shared-folders.html)
with `spice-webdavd` installed in the guest. Copy the package and disposable test
media onto the guest's own disk before using them: snapshots cannot undo changes
to host shared folders or USB drives.

In a guest terminal, change to the extracted folder and run:

```sh
python3 -c 'import mutagen; print(mutagen.version_string)'
mkvextract --version
mkvpropedit --version
mkvinfo --version
/usr/bin/vlc --version
python3 install.py
```

Run the installer as your normal desktop user, without sudo. Confirm that VLC
reports version 3, the version targeted by this extension. Fully close VLC,
then launch `/usr/bin/vlc` from the terminal and select **View > Metadata Pro**.
Fedora's Mutagen version may differ from the project's tested 1.44.0 baseline;
this remains an unverified distribution combination.

Copy a small MP4 and MKV into the guest's home directory. Open each in VLC,
load it in Metadata Pro, change a tag, save, and reopen it to check that the
value persists. Use copies for this first check, and confirm playback and
backup creation. A powered-off VM snapshot before testing makes it easy to
return to the clean installation.

## Repeatable tests with Boxes snapshots

For each snapshot, shut down the guest normally and wait until Boxes shows it
stopped. Open **Properties/Preferences → Snapshots**, click **+**, and rename it.
See [creating snapshots](https://help.gnome.org/gnome-boxes/snapshot-create.html)
and [restoring snapshots](https://help.gnome.org/gnome-boxes/snapshot-revert.html).

- **`01-clean-os-no-vlc`**: the installed, updated OS before VLC or either extension
  is installed. Use this to test the complete dependency installation.
- **`02-vlc-ready-no-addins`**: VLC 3 and dependencies pass their version checks,
  both sample videos play with picture and sound, and VLC is fully closed.
  Take this before running `python3 install.py`. You can include uninstalled
  packages and untouched test media in this snapshot.

Test Metadata Pro alone from snapshot 02 first. Then restore 02, install both
projects using their normal-user installers, and test them together: edit and save MP4/MKV tags in Metadata Pro, load those
files in Super Playlist, filter by the saved tags, and export/open an M3U8.
Restart VLC and confirm saved tags still load. Use **Check status** to collect
background results, and verify Metadata Pro's backups exist.

Before restoring a snapshot, export useful logs and screenshots to the host.
Record `/etc/os-release`, `uname -m`, dependency versions, the installer archive
checksum, date, starting snapshot, and pass/fail for each attempt. Restoring
also rolls back guest logs, installer packages, and test media. Reinstalling
without reverting tests upgrades and preserved settings, not a clean install.

## Common problems

- **VM returns to the live installer:** eject the ISO and put the virtual disk
  first in the boot order.
- **No internet:** check the host's internet connection and that Boxes'
  virtual network device is enabled. In the guest, check the wired connection in GNOME Settings
  and run `nmcli device status` to inspect it.
- **Blank viewer but the Boxes tile shows a desktop:** the thumbnail may be
  stale. Close and reopen Boxes, then open the VM again. If it persists, close
  Boxes and launch `gnome-boxes` from a host terminal (or
  `flatpak run org.gnome.Boxes` for Flatpak Boxes) and retain the errors when
  opening the guest. This display problem precedes extension installation.
- **Slow or glitchy desktop:** shut down the guest and try disabling **3D
  Acceleration** under **Properties/Preferences → Resources**, if available.
  See [Boxes graphics settings](https://help.gnome.org/gnome-boxes/3d-acceleration.html).
  When booting the ISO, its **Troubleshooting → Basic graphics mode** option
  is another diagnostic route if the boot menu is visible.
- **Clipboard or resizing does not work:** confirm `spice-vdagent` is installed
  and log out and back in. Use GNOME's display settings to choose a resolution
  if automatic resizing fails. Integration varies with the desktop session.
- **Metadata Pro is missing from View:** confirm `vlc-plugin-lua` is installed,
  rerun `python3 install.py` as the user who launches VLC, fully restart VLC,
  and ensure you opened the native RPM version.
- **A video cannot play because of missing codecs:** confirm `vlc-plugin-ffmpeg`
  is installed. Some codecs require packages beyond Fedora's repositories;
  consult the [Fedora RPM Fusion setup guide](https://docs.fedoraproject.org/en-US/quick-docs/rpmfusion-setup/)
  and [RPM Fusion multimedia instructions](https://rpmfusion.org/Howto/Multimedia)
  for your release if you need those codecs. Switching to Flatpak VLC would
  not preserve this extension installation route.
- **Saving fails:** use a writable video copy in the guest's home directory,
  select **Check status**, and inspect the worker log described in the
  [README](../README.md).
