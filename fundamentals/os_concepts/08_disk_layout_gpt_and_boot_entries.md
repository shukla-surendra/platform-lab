# Operating Systems, Part 8: Disk Layout — GPT, the ESP, and Boot Entries

[Part 7](07_boot_process_power_on_to_kernel.md) established the boot *sequence* and left one
step deliberately unexplained: how firmware locates the single `.efi` boot application it
executes. This part covers the **data structures** that make that possible — how a disk
describes itself, where boot programs live, and where the firmware's boot configuration is
actually stored (not where you'd guess).

## The Problem: A Disk Is Just Sectors

To firmware, a freshly discovered disk is an undifferentiated sequence of numbered blocks —
**LBAs**, Logical Block Addresses:

```text
LBA 0, LBA 1, LBA 2, ... LBA N
```

There are no partitions, files, or directories in the hardware. Those are conventions imposed
by data written *onto* the sectors. So firmware needs, in order:

1. a **map** saying how the disk is carved up → GPT,
2. a **known partition** where boot programs live → the EFI System Partition,
3. a **filesystem** it can read inside that partition → FAT32,
4. a decision about **which** program to run → UEFI boot entries.

Those four are separate mechanisms that get conflated constantly. Keeping them distinct is
most of the value of this part.

## GPT: A Map, Not a Container

**GPT** — GUID Partition Table — is a partition-table format: a map describing how the disk is
divided. It stores, for each partition, where it starts, where it ends, and what type it is.

```text
Partition 1:  LBA X → LBA Y,  type = EFI System Partition
Partition 2:  LBA A → LBA B,  type = Microsoft Basic Data
Partition 3:  LBA C → LBA D,  type = Linux filesystem
```

> **GPT says where the partitions are. It does not contain an operating system, and it does
> not know what an operating system is.**

The on-disk layout:

```text
┌──────────────────────────────────────┐
│ Protective MBR                       │  LBA 0
├──────────────────────────────────────┤
│ Primary GPT Header                   │  LBA 1
├──────────────────────────────────────┤
│ GPT Partition Entry Array            │  LBA 2-33 (typically)
├──────────────────────────────────────┤
│                                      │
│              Partitions              │
│   ┌──────────────────────────────┐   │
│   │ EFI System Partition (FAT32) │   │
│   │   bootloader.efi             │   │
│   └──────────────────────────────┘   │
│   ┌──────────────────────────────┐   │
│   │ Windows / Linux / ...        │   │
│   └──────────────────────────────┘   │
│                                      │
├──────────────────────────────────────┤
│ Backup GPT Partition Entry Array     │
├──────────────────────────────────────┤
│ Backup GPT Header                    │  last LBA
└──────────────────────────────────────┘
```

Two details worth noticing. The **protective MBR** at LBA 0 is a compatibility shim: it makes
the disk look, to an old MBR-only tool, like one unknown-type partition spanning everything —
so legacy software refuses to touch it rather than cheerfully overwriting it. And GPT keeps a
**full backup** of its metadata at the far end of the disk, because a partition table is a
single point of failure for every byte on the device.

### What a partition entry actually holds

Each entry is exactly 128 bytes:

```text
┌──────────────────────────────┐
│ Partition Type GUID          │ 16 bytes  - what kind of partition
│ Unique Partition GUID        │ 16 bytes  - identity of this one
│ First LBA                    │  8 bytes
│ Last LBA                     │  8 bytes
│ Attributes                   │  8 bytes  - flags
│ Partition Name               │ 72 bytes  - UTF-16, human-readable
└──────────────────────────────┘
```

The **Partition Type GUID** is how firmware recognizes an EFI System Partition — a
well-known constant GUID — without understanding anything else on the disk.

### GPT vs MBR

MBR is the older scheme. The common pairings are:

```text
Modern:  UEFI firmware  +  GPT  +  EFI System Partition
Legacy:  BIOS firmware  +  MBR  +  boot code in the first sector
```

They're conventionally paired but technically independent concepts — the firmware interface and
the partitioning scheme are separate choices. GPT also lifts MBR's hard limits (four primary
partitions, ~2 TB disks), which is why it's now the default.

### GPT does not say "this is Windows"

A disk might report:

```text
Partition 1:  EFI System Partition
Partition 2:  Microsoft Basic Data
Partition 3:  Linux filesystem
Partition 4:  Linux filesystem
```

That is a description of *partitions*, not an inventory of operating systems. "Microsoft Basic
Data" is a generic type used for ordinary data volumes as well as Windows installs. And
critically:

> **The order of GPT partition entries is not boot priority.**

Partition 1 is not "the first OS to try." Boot order lives somewhere else entirely — see below.

## The EFI System Partition

The **ESP** is an ordinary partition with a well-known type GUID, formatted with **FAT32**,
whose job is to hold boot applications:

```text
EFI System Partition  (FAT32)
└── EFI/
    ├── Microsoft/
    │   └── Boot/bootmgfw.efi
    ├── ubuntu/
    │   └── grubx64.efi
    └── BOOT/
        └── BOOTX64.EFI      ← the fallback path
```

Why FAT32? Because every UEFI implementation is *required* to be able to read it. Firmware has
to parse this filesystem with a driver baked into flash, before any OS exists — so the standard
mandates something simple and universal. It's a deliberately boring choice, and that's the
point.

Note that each OS gets its own vendor directory. Installing Linux alongside Windows adds a
directory to the shared ESP; it does not replace what's there. This is also why an ESP that's
too small (some vendors ship 100 MB) causes trouble after a few kernel updates.

Keeping the layers straight:

| Layer | What it is |
|---|---|
| GPT | describes where partitions are |
| EFI System Partition | a partition that holds boot programs |
| FAT32 | the filesystem inside that partition |
| `.efi` file | an executable UEFI application |
| Bootloader | what that executable usually is |
| Kernel | what the bootloader loads next |

## Boot Entries Live on the Motherboard, Not the Disk

This is the single most surprising fact in this part, and the one most worth internalizing.

Firmware does not decide what to boot by inspecting the disk. It reads **UEFI boot variables**
stored in **NVRAM on the motherboard**:

```text
UEFI NVRAM

BootOrder:  Boot0002, Boot0001

Boot0001:   Disk 1 → ESP → \EFI\Microsoft\Boot\bootmgfw.efi
Boot0002:   Disk 1 → ESP → \EFI\ubuntu\grubx64.efi
```

So there are **two independent data structures**, in two different physical places, answering
two different questions:

```text
        DISK                          MOTHERBOARD
        ────                          ───────────
        GPT                           UEFI NVRAM
         ├── partition 1               ├── Boot0001
         ├── partition 2               ├── Boot0002
         └── partition 3               └── BootOrder

  "Where are the partitions?"    "Which program should I run?"
```

Several confusing real-world behaviours fall straight out of this split. Moving a disk to a
different motherboard can leave it unbootable even though every byte is intact — the NVRAM
entries stayed behind. Clearing CMOS/NVRAM can "lose" a working OS install. And a firmware
boot menu can list entries for disks that are no longer plugged in, because the entry is
firmware state, not disk state.

## The Fallback Path: Why a USB Boots on Any Machine

If boot entries live in NVRAM, how does a USB stick you made on one laptop boot on a different
one that's never seen it?

Via a standardized **fallback path**. When firmware tries a removable device with no matching
boot entry, it looks for one specific hard-coded location. On x86-64:

```text
\EFI\BOOT\BOOTX64.EFI
```

Any removable device with a FAT32 ESP containing that exact path is bootable on any compliant
UEFI machine, with no prior registration. That convention is the whole reason a Linux
installer USB is portable — and the reason `dd`-ing an ISO to a stick produces something
bootable, since the ISO already contains that layout.

## Putting It Together: Two Disks and a USB

```text
Disk 1:  Windows + Ubuntu
Disk 2:  Fedora + Windows
USB:     Linux installer

BootOrder:
  1. Disk 1 → \EFI\ubuntu\grubx64.efi
  2. Disk 1 → \EFI\Microsoft\Boot\bootmgfw.efi
  3. Disk 2 → Fedora bootloader
  4. USB fallback → \EFI\BOOT\BOOTX64.EFI
```

Firmware walks BootOrder and executes the first entry that loads successfully. Suppose that's
GRUB on Disk 1. Firmware's job is now finished. GRUB — which *can* read filesystems — scans
both disks, finds four OS installations, and presents a menu. Firmware never enumerated those
four; the bootloader did.

That's Part 7's division of labour, made concrete: **firmware picked a program, the program
picked an OS.**

## Secure Boot

Secure Boot layers verification over this structure. Firmware holds a set of trusted keys, and
before executing any `.efi` application it checks the file's cryptographic signature against
them. An unsigned or tampered bootloader is refused.

This is why Linux distributions ship a small first-stage loader called **shim**, signed by a
key that Microsoft's widely-trusted CA has countersigned — shim is what firmware will accept,
and shim then vouches for GRUB. It's the [chain of trust](07_boot_process_power_on_to_kernel.md#why-this-matters-in-practice)
from Part 7, implemented at the ESP.

The practical consequence: hand-built or self-modified bootloaders need their key enrolled in
firmware, or Secure Boot turned off. "It boots with Secure Boot disabled but not enabled" is a
signature problem, never a partition problem.

## Try It: Build a Disk You Can Safely Break

This material sticks far better when you've made one and destroyed it. Do it on a **virtual**
disk, not your machine's SSD.

A virtual disk is just a file — `disk.img`, `.vdi`, `.vmdk`, `.qcow2`. A raw `.img` is the most
instructive because it is literally the disk's sectors in a file, so you can inspect it with
ordinary tools.

A worthwhile progression:

1. Create a VM with a blank virtual disk (VirtualBox, UTM, or QEMU).
2. Boot any Linux ISO in it and use `gdisk`/`parted` to write a GPT and create an ESP.
3. Look at the raw bytes: LBA 0 (protective MBR), LBA 1 (GPT header), the entry array.
4. Mount the ESP and inspect `\EFI\`; note it really is plain FAT32.
5. Install a distro, then run `efibootmgr` to print the NVRAM boot entries — the motherboard
   side of the split above, made visible.
6. **Break it deliberately**: rename the `.efi` file, or delete a boot entry, and observe
   exactly which stage fails and what the error looks like. Then recover it.

Step 6 is the one that converts this from reading into knowledge. Predict the failure *before*
you cause it, and check whether you were right.

## Why This Matters in Practice

**A cloud machine image is exactly this layout in a file.** An AMI, a GCP image, or a
`qcow2` is a disk image with a GPT, an ESP, and a bootloader. When you build golden images or
debug why a custom image won't boot, you are working directly with these structures. "The
instance never reached the console" almost always means firmware couldn't find or execute the
boot application.

**Boot repair is stage identification.** Knowing that GPT, the ESP, and NVRAM boot entries are
three separate things turns a vague "won't boot" into a specific question: is the partition
table intact, is the `.efi` file present, does a boot entry point at it? Those have three
different fixes, and the backup GPT header at the end of the disk means a corrupt primary table
is often recoverable.

**Immutable infrastructure depends on this being uniform.** Predictable boot is what lets a
provisioning system stamp out thousands of identical machines. PXE/network boot substitutes a
network-fetched loader for the ESP one — the same chain, a different source for stage two.

## Quick Self-Check

- What are the four separate mechanisms firmware needs to get from "a disk exists" to
  "executing a program," and which one does GPT provide?
- Where is BootOrder stored, and what does that imply if you move a working disk to a different
  motherboard?
- Why must the ESP be FAT32 rather than ext4 or NTFS?
- A USB stick has never been plugged into this machine and there's no boot entry for it. What
  exact path makes it bootable anyway?
- Someone says "partition 1 boots first because it's first in the GPT." What's wrong with that?
- A system boots with Secure Boot off and fails with it on. Which layer is at fault, and which
  layers are definitely fine?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Layer-separation framing (the default):** "There are four distinct mechanisms people tend
  to merge into one: GPT is a map of where partitions are; the EFI System Partition is a
  specific partition that holds boot programs; FAT32 is the filesystem inside it, mandated
  because firmware must be able to read it with a driver in flash; and the UEFI boot entries
  that decide *which* program runs aren't on the disk at all. Keeping those four apart is most
  of understanding UEFI boot."
- **Surprising-fact framing (good for showing depth quickly):** "The part that surprises people
  is that boot configuration lives in NVRAM on the motherboard, not on the disk. GPT answers
  'where are the partitions,' UEFI variables answer 'which program should I run,' and they're
  physically different storage. That's why a perfectly intact disk can become unbootable just by
  moving it to another motherboard — every byte is fine, but the boot entry stayed behind."
- **Portability framing (good if the interviewer asks something practical):** "Take a question
  like 'why does a Linux installer USB boot on any machine when the firmware has never seen
  it?' It's the fallback path: with no matching boot entry, UEFI looks for one hard-coded
  location — `\EFI\BOOT\BOOTX64.EFI` on x86-64. That single convention is what makes bootable
  media portable across vendors, and why `dd`-ing an ISO to a stick just works."

### Vocabulary Builder

- **LBA** (n., Logical Block Address) — a disk's numbered sectors; the only structure the
  hardware itself provides. *"Before a partition table is written, a disk is nothing but LBAs."*
- **GPT** (n., GUID Partition Table) — the modern partition-table format; a map of the disk,
  not a container of operating systems.
- **EFI System Partition / ESP** (n. phrase) — the FAT32 partition, identified by a well-known
  type GUID, that holds `.efi` boot applications.
- **protective MBR** (n. phrase) — the compatibility record at LBA 0 that makes a GPT disk look
  occupied to legacy tools so they don't overwrite it.
- **fallback path** (n. phrase) — the hard-coded `\EFI\BOOT\BOOTX64.EFI` location firmware tries
  when no boot entry matches; what makes removable media portable.
- **"those are two different data structures in two different places"** — a reusable line for
  any question where people conflate co-located concerns. Naming the split, then what each side
  answers, is a compact way to show you've actually looked.

---

**Previous:** [Part 7: The Boot Process — Power-On to Kernel](07_boot_process_power_on_to_kernel.md)  |  **Next:** [System Design Foundation, Part 3: Communication and Resilience](../system_design_foundation/00_prerequisite_concepts/03_communication_and_resilience.md)
