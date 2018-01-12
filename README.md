# bootmgr

A configuration framework for EFI boot entries.


### What?

> The Unified Extensible Firmware Interface (EFI or UEFI for short) is a new
> model for the interface between operating systems and firmware. It provides a
> standard environment for booting an operating system and running pre-boot
> applications. It is distinct from the commonly used "MBR boot code" method
> followed for BIOS systems.
>
> – [ArchWiki]

EFI systems can load the Linux kernel directly, obviating the need for a bootloader. In practice however, configuring an EFI to do so can be cumbersome, and thus traditional bootloaders are still commonplace. This largely stems from the fact that bootloaders like GRUB can be easily configured through plain text files while EFI variables are hard to access and binary formats.

bootmgr bridges this gap by defining a sensible configuration file format for EFI boot entries and providing a tool to sync such files with the EFI variables.

[ArchWiki]: https://wiki.archlinux.org/index.php/Unified_Extensible_Firmware_Interface


### Configuration

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

- **Booleans**: Keys whose argument is `true` are passed to the loader directly, and keys whose argument is `false` have the string `'no'` prepended. For example, the line `rw = true` would pass the `rw` argument to the kernel, and the line `initrd = false` would pass the `noinitrd` argument.
- **Scalars**: Scalar values other than booleans are used to pass `key=val` style parameters. For example, you almost certainly want to pass `root = /dev/something` when loading a Linux kernel.
- **Tables**: Table values are used for `module.key=val` style parameters. The line `nvidia-drm = {modeset=1}` will pass the parameter `nvidia-drm.modeset=1`. Tables can have multiple sublines too. For example `foo = {bar=true, baz=qux}` will expand to two parameters: `foo.bar` and `foo.baz=qux`.

This format is quite flexible. For example `nvidia-drm = {modeset=1}` is equivalent to `'nvidia-drm.modeset' = 1`. For more examples of TOML syntax, check out the [spec][TOML].

[TOML]: https://github.com/toml-lang/toml


### Usage

**TODO**: Figure out what I'm doing for the CLI.


### Installation

bootmgr is just a simple Python script. Simply place it somewhere on your path, and optionally remove the `.py` extension. I've provided a PKGBUILD for Arch Linux that does exactly that.

**TODO**: Create the PKGBUILD.


### License

MIT License

Copyright (c) 2018 Chris Barrick

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
