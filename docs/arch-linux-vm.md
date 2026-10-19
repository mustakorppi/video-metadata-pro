# Arch Linux guest in GNOME Boxes

This guide creates an x86_64 Arch Linux desktop VM for testing Metadata Pro with
native VLC 3. **Host** means your real computer running Boxes; **guest** means
the VM. Run commands in the guest unless marked otherwise. This is a test
procedure, not verified compatibility with every release.

Download a current official **Arch Linux x86_64 ISO** from the
[Arch download page](https://archlinux.org/download/) and follow its verification
instructions. Arch Linux ARM is outside this guide.

## Create the VM on the host

1. Open **GNOME Boxes**, click **+ → Install from File**, and select the ISO.
   Record its filename and checksum with your test results.
2. Name the VM `arch-metadata-pro`. Allocate **4 GiB RAM** (8 GiB if available) and a
   **40 GiB** virtual disk. Allow extra host space for snapshots, videos, and
   Metadata Pro's full video backups.
3. Click **Create** and boot the installation medium. Keep the default virtual
   network connection enabled.

Menu labels vary with the Boxes version. See
[GNOME's instructions for creating a box](https://help.gnome.org/gnome-boxes/create.html).
Use an x86_64 ISO on an x86_64 host for this procedure.

## Install Arch inside the VM

The following commands run in the **guest's live console**, which is already
logged in as root. Check connectivity and time synchronization:

```sh
ping -c 3 archlinux.org
timedatectl set-ntp true
```

If networking fails, check the host connection and Boxes' virtual network
settings. Check firmware mode with `test -d /sys/firmware/efi && echo UEFI || echo BIOS`
and choose a matching bootloader in the installer.

Start the guided installer included on the ISO:

```sh
archinstall
```

Choose the following settings. Labels may vary with the ISO's installer version;
the [upstream archinstall guide](https://github.com/archlinux/archinstall)
documents the current guided installer.

| Setting | Suggested choice |
| --- | --- |
| Language, keyboard, mirrors | Your locale and a nearby mirror region |
| Disk configuration | Best-effort/default partition layout on the new virtual disk, usually `/dev/vda`; ext4 is sufficient |
| Bootloader | systemd-boot for UEFI; GRUB for BIOS |
| Hostname | `arch-metadata-pro` |
| User account | Create a normal user with a password and sudo access |
| Profile | Desktop, then Xfce for a lightweight test desktop |
| Graphics driver | Open-source/default driver suitable for the virtual GPU |
| Display manager | Accept the desktop profile's suggested greeter |
| Audio | PipeWire |
| Kernel | Default `linux` kernel |
| Network configuration | NetworkManager |
| Timezone and NTP | Your timezone; enable time synchronization |

The partitioning step erases the selected disk: select only the newly created
VM disk. Review the summary, choose **Install**, and let installation finish.
When offered a post-install chroot, you can decline for this setup.

Run `poweroff`, eject the ISO in Boxes' device settings,
then start the VM again. Log in to the installed desktop as your normal user.

## Install Metadata Pro in the guest

Run the remaining commands in a terminal **inside the installed Arch desktop**.
Update the guest and install VLC, its Lua and FFmpeg plugins, and the helper's
dependencies:

```sh
sudo pacman -Syu --needed spice-vdagent
# Save snapshot 01 here if VLC is not already installed.
sudo pacman -Syu --needed vlc vlc-plugins-all python python-mutagen mkvtoolnix-cli
```

This broad desktop baseline uses `vlc-plugins-all`, including Lua and FFmpeg.
Arch splits VLC plugins into separate packages: the
[Lua plugin](https://archlinux.org/packages/extra/x86_64/vlc-plugin-lua/)
provides extension support, and the
[FFmpeg plugin](https://archlinux.org/packages/extra/x86_64/vlc/)
adds playback codec support. MKVToolNix's command-line tools come from
`mkvtoolnix-cli`; Mutagen comes from `python-mutagen`.

Always perform full upgrades; do not use `pacman -Sy` followed by individual
package installations. Arch is rolling release: record `pacman -Q` with the
test date. Restoring snapshot 02 without updating preserves the dependency set;
updating after a restore establishes a new baseline.

Reboot after the update, then log in to the desktop again. With the SPICE channel
present, `spice-vdagent` supports desktop integration such as clipboard sharing
and display resizing in an X11 session. See the
[SPICE agent manual](https://man.archlinux.org/man/spice-vdagentd.1.en).

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

Run the installer as your normal desktop user. Confirm that VLC reports version
3, the version targeted by this extension. Restart VLC and select
**View > Metadata Pro**. Arch supplies a newer Mutagen than the project's tested
1.44.0 baseline, so this setup remains an unverified distribution combination.

Copy a small MP4 and MKV into the guest's home directory. Open each in VLC,
load it in Metadata Pro, change a tag, save, then reopen it to check that the
value persists. Use copies for this first check, and confirm that playback and
backup creation work. A powered-off VM snapshot before testing makes it easy
to return to the clean installation.

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

- **VM returns to the installer:** eject the ISO and put the virtual disk first
  in the boot order.
- **No internet after installation:** if you selected NetworkManager, run
  `sudo systemctl enable --now NetworkManager` inside the installed guest.
  Also check the host's internet connection and Boxes' virtual network device.
- **Blank desktop or display glitches:** shut down the guest and try disabling
  **3D Acceleration** in Boxes **Properties/Preferences → Resources**, if the
  switch is available. Try the Xfce X11 session used in this guide.
- **Clipboard or resizing does not work:** confirm `spice-vdagent` is installed in the guest, and log out and back in.
- **Metadata Pro is missing from View:** confirm `vlc-plugin-lua` is installed,
  rerun `python3 install.py` as the same user who launches VLC, and fully restart
  VLC.
- **Video opens but cannot play:** confirm `vlc-plugin-ffmpeg` is installed.
  For save failures, use **Check status** and the worker log described in the
  [README](../README.md).
