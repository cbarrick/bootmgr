bootmgr
==================================================

A configuration framework for EFI boot entries.


Status
--------------------------------------------------

This project is in early development, but is already useful. I currently use it on an Arch box instead of a bootloader. Once I give it enough time to stabilize for my use, I'll push it to the AUR.


What?
--------------------------------------------------

> The Unified Extensible Firmware Interface (EFI or UEFI for short) is a new
> model for the interface between operating systems and firmware. It provides a
> standard environment for booting an operating system and running pre-boot
> applications. It is distinct from the commonly used "MBR boot code" method
> followed for BIOS systems.
>
> – [ArchWiki]

EFI systems can load the Linux kernel directly, obviating the need for a bootloader. In practice however, configuring an EFI to do so can be cumbersome, and thus traditional bootloaders are still commonplace. This largely stems from the fact that bootloaders like GRUB can be easily configured through plain text files while EFI variables are hard to access and binary formatted.

bootmgr bridges this gap by defining a sensible configuration file format for EFI boot entries and providing a tool to sync such files with the EFI variables.

[ArchWiki]: https://wiki.archlinux.org/index.php/Unified_Extensible_Firmware_Interface


Configuration
--------------------------------------------------

Boot entries are specified in a file `bootmgr.toml` in the root of your EFI system partition, typically `/boot` or `/boot/efi`. The syntax of this file is [TOML], an INI-like configuration file format with a simple, formal spec. Here's an example:

```toml
['Arch Linux']
loader = '/vmlinuz-linux'
root = '/dev/sdb2'
initrd = '/initramfs-linux.img'
rw = true
nvidia-drm = {modeset=1}

['Arch Linux (fallback)']
loader = '/vmlinuz-linux'
root = '/dev/sdb2'
initrd = '/initramfs-linux-fallback.img'
rw = true

['UEFI Shell']
loader = '/shellx64_v2.efi'
```

This file specifies three boot entries named Arch Linux, Arch Linux (fallback), and UEFI Shell respectively. The order of entries corresponds to the EFI boot order. Every boot entry is required to have a `loader` line which specifies the path to the EFI application to boot (e.g. the kernel) relative to the EFI system partition. Additional lines are transformed into command line parameters to be passed to the loader. These parameters come in a few different flavors:

- **Booleans**: Keys whose argument is `true` are passed to the loader directly, and keys whose argument is `false` have the string `'no'` prepended, e.g. `initrd = false` yields the parameter `noinitrd`.

- **Strings** and **Numbers**: Scalar values other than booleans are used to pass `key=val` style parameters, e.g. `root = '/dev/sdb2'` yields the parameter `root=/dev/sdb2`.

- **Tables**: Table values are used for `module.key=val` style parameters, e.g. `nvidia-drm = {modeset=1}` yields the parameter `nvidia-drm.modeset=1`. Alternatively, these types of parameters can be specified by using a quoted key, e.g. `'nvidia-drm.modeset' = 1`. Table values have quite a bit of flexibility in how they are expressed. For examples of alternative syntax, check out the [spec][TOML].

[TOML]: https://github.com/toml-lang/toml


### Examples

| Config Line                 | Kernel Parameters       |
|-----------------------------|-------------------------|
| `foo = true`                | `foo`                   |
| `foo = false`               | `nofoo`                 |
| `foo = 1`                   | `foo=1`                 |
| `foo = 'bar'`               | `foo=bar`               |
| `'foo.bar' = 1`             | `foo.bar=1`             |
| `foo = {bar=1, baz=2}`      | `foo.bar=1 foo.baz=2`   |


Usage
--------------------------------------------------

```
usage: bootmgr [-h] [-V] [-v] [-D] [-d DISK] [-p PART] [PATH]

Sync EFI boot entries with bootmgr.toml

Global Options:
  -h, --help            Print this help message and exit.
  -V, --version         Print the version and exit.
  -v, --verbose         Log actions to stderr.
  -D, --delete          Delete entries which are not listed in the config.
  -d DISK, --disk DISK  Override the disk containing the loaders.
  -p PART, --part PART  Override the partition containing the loaders.
  PATH                  Override the path to the config.
```


Installation
--------------------------------------------------

bootmgr is a single Python script. You can use it as-is by copying it to your PATH (optionally without the `.py` extension).

For package maintainers, I have supplied a simple makefile which copies the file to `/usr/bin` and marks it executable. The installation prefix can be overridden with the DESTDIR and PREFIX environment variables.

I have also provided a PKGBUILD script for packaging on Arch Linux.


### Dependencies

- **Python** >= 3.6 because f-strings are dope.
- **[efibootmgr]** to read and update the boot entries.
- **[toml]** package for Python to read the config file.

[efibootmgr]: https://github.com/rhboot/efibootmgr
[toml]: https://github.com/uiri/toml


Prior work
--------------------------------------------------

bootmgr is essentially a config file based frontend to [efibootmgr], a CLI tool for reading and updating boot entries. I love the ease and simplicity of efibootmgr, but I was frustrated by the lack of a persistent, readable configuration for my boot entries. And thus bootmgr was born.

[efibootmgr]: https://github.com/rhboot/efibootmgr
