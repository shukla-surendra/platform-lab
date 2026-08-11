# Operating Systems, Part 7: The Boot Process — Power-On to Kernel

Parts 1-6 all assumed a running kernel: something had already set up virtual memory
([Part 3](03_virtual_memory_and_paging.md)), established the user/kernel boundary
([Part 5](05_context_switching_and_kernel_boundary.md)), and started the first process. This
part covers how that happens — the chain from applying power to a CPU that knows nothing, to
a kernel scheduling processes.

This part is the **sequence**. [Part 8](08_disk_layout_gpt_and_boot_entries.md) covers the
**disk structures** that sequence depends on. Read them in that order.

## The Problem: A CPU That Knows Nothing

Power arrives at a cold machine. The CPU can execute instructions — but the operating system
is a few gigabytes of files sitting on an SSD, in a filesystem the CPU has no concept of, on a
device that hasn't been initialized, reachable through a controller whose driver is part of
the OS that isn't loaded yet.

That is a genuine chicken-and-egg problem, and every piece of the boot process exists to break
it:

> **The CPU does not know where the operating system is. It only executes instructions.
> Firmware and bootloaders exist to supply the information and code needed to find and start
> the OS.**

The solution is a **chain of increasingly capable loaders**, each one small enough to be found
by the previous stage and smart enough to find the next. That's the shape to hold onto — every
detail below is an instance of it.

## CPU Reset and the Reset Vector

When the CPU is released from reset, its registers hold hardware-defined values, and it begins
fetching instructions from a fixed **reset vector**. On x86-64 that address is:

```text
0xFFFFFFF0
```

The critical subtlety — and the part people get wrong — is what that address *means*. It is an
address in the **CPU's address space**, not a location in RAM. At this instant, DRAM has not
even been initialized; there is nothing there to read.

An address space is a numbering scheme that the platform's address decoding maps onto actual
hardware. Different ranges route to different devices:

```text
CPU issues a fetch for 0xFFFFFFF0
         │
         ▼
  address decoding
         │
         ├── some ranges → DRAM
         ├── some ranges → memory-mapped devices
         └── this range  → firmware flash
                              │
                              ▼
                       first instruction
```

So the rule to carry forward:

> **A CPU address is not necessarily a physical RAM location.**

This is the same idea Part 3 develops for virtual memory — a layer of translation between the
address a consumer names and the hardware that answers. Here the translation is done by the
platform's address decoding rather than an MMU and page tables, but the concept transfers
directly, which is why memory-mapped I/O feels familiar once paging clicks.

## Firmware: Code That Exists Before Any OS

The reset vector routes to **firmware** — on modern PCs, UEFI — stored in non-volatile flash
soldered to the motherboard (typically SPI flash), entirely independent of any disk:

```text
Motherboard
┌──────────────────────────────┐
│  CPU                         │
│  Firmware flash (SPI)        │
│    └── UEFI                  │
│  DRAM                        │
│  Storage controllers         │
└──────────────────────────────┘
```

That physical separation is the whole point: it's why a machine with a blank SSD, or no SSD at
all, still powers on and shows a firmware screen. The firmware is not part of the OS and does
not depend on one existing.

Firmware's job is to turn a barely-functional CPU into a machine capable of loading software:

- initialize CPU and platform features,
- initialize the memory controller and train DRAM (until this finishes, there is no usable RAM),
- discover and initialize storage controllers, disks, and USB devices,
- load the firmware drivers needed to *read* those devices,
- read its own persistent boot configuration.

Only after DRAM works and storage is readable can anything be loaded from disk. Note the
ordering dependency — it explains why a machine with failing RAM often dies before displaying
anything at all.

## The Handoff Chain: Firmware → Bootloader → Kernel

Here is the misconception worth killing early:

> "UEFI scans the disks, finds the installed operating systems, and shows you a menu."

That is **not** what happens. The division of labour is:

```text
UEFI  ──finds and executes──►  a boot application (.efi)
                                       │
                                       ▼
                          Bootloader ──finds and selects──►  an operating system
```

**UEFI finds a program. The bootloader finds an OS.** Firmware does not need to understand
NTFS or ext4, does not enumerate your Windows installs, and does not know what "Ubuntu" is. It
locates one executable file and jumps to it. Everything OS-aware happens after that.

The bootloader — GRUB, `systemd-boot`, Windows Boot Manager — is the first component with real
knowledge of operating systems. It can read filesystems, inspect multiple disks, parse its own
config, and present a menu:

```text
GRUB
─────────────────
Ubuntu
Fedora
Windows
─────────────────
```

*How* firmware locates that one `.efi` file is the subject of
[Part 8](08_disk_layout_gpt_and_boot_entries.md) — it involves boot entries stored on the
motherboard, not on the disk, which surprises most people.

## Getting the Kernel into RAM

Once the bootloader knows which OS to start, it reads the kernel from storage into RAM and
jumps to it. It typically loads three things:

- the **kernel image** itself,
- the **kernel command line** (root device, boot parameters),
- an **initramfs** (initial RAM filesystem).

That third item deserves a moment, because it resolves a second chicken-and-egg problem. The
kernel needs to mount the root filesystem to get going — but the driver required to talk to
that disk (an exotic RAID controller, an NVMe device, an encrypted or network volume) may
itself live *on* the root filesystem it can't yet read.

The initramfs breaks the loop: it's a small, self-contained filesystem the bootloader loads
directly into RAM, containing exactly the drivers and tools needed to reach the real root.
The kernel mounts it first, uses it to set up access to the real filesystem, then pivots to
that and discards the initramfs.

The same "load a minimal capable thing first" pattern appears at every stage of boot. Once you
see it in the firmware → bootloader step, initramfs stops looking like an arbitrary Linux
quirk.

## The Complete Sequence

One canonical version — the chain from cold silicon to a login prompt:

```text
 1. Power on
 2. CPU reset; registers at hardware defaults
 3. CPU fetches from the reset vector
 4. Firmware (UEFI) begins executing from flash
 5. UEFI initializes CPU, memory controller, DRAM
 6. UEFI initializes and discovers storage / USB devices
 7. UEFI reads its boot configuration (NVRAM boot entries)
 8. UEFI selects a boot entry per BootOrder
 9. UEFI reads the target partition and loads the .efi application
10. CPU executes the bootloader
11. Bootloader discovers available OS installations
12. Default chosen, or the user picks one
13. Bootloader loads kernel + initramfs into RAM
14. Bootloader transfers control to the kernel
15. Kernel initializes memory management, CPU, drivers, filesystems, networking
16. Kernel mounts the real root filesystem and starts the first user-space process
17. init/systemd brings up services; login or desktop appears
```

Compressed to the two chains worth memorizing:

> **CPU → firmware → bootloader → kernel → OS**
> **(disk side) GPT → EFI System Partition → `.efi` bootloader → OS files**

## Why This Matters in Practice

**Containers don't boot — and that's the entire reason they start in milliseconds.** A
container is a process on the host kernel, isolated with namespaces and cgroups. Steps 1-16
above have already happened, once, on the host. No firmware, no bootloader, no kernel
initialization, no device discovery. A VM does all of it, which is why VM start is measured in
tens of seconds and container start in tens of milliseconds. If you can explain that
difference *mechanically* rather than as "containers are lighter," you're answering the
question an infra interviewer actually asked.

**Cloud instance cold start is this sequence, virtualized.** An EC2 or GCE instance still runs
firmware (commonly OVMF, a UEFI implementation, or a stripped-down equivalent in
microVMs like Firecracker), still loads a bootloader, still initializes a kernel. Firecracker's
headline start times come largely from *deleting stages* — skipping legacy device probing and
booting a kernel directly — not from making each stage faster. Serverless cold-start latency is
this chain, and the optimizations are all "which stage can we skip or pre-warm."

**Knowing the stage boundaries makes boot failures diagnosable.** "It won't boot" is useless;
*which stage* it reached is nearly the whole diagnosis. No firmware screen points at power, CPU,
or RAM training. A firmware screen but "no bootable device" means firmware ran and found no boot
application — a disk or boot-entry problem, not an OS problem. A GRUB prompt means the
bootloader loaded and failed to find a kernel. A kernel panic mentioning the root filesystem
means the kernel ran and the initramfs didn't get it to the real root. Four different teams,
four different fixes.

**Secure Boot is a chain of trust laid over this chain of loaders.** Each stage
cryptographically verifies the next before executing it — firmware checks the bootloader's
signature, the bootloader checks the kernel. That only works because boot is a strict handoff
sequence; a chain of trust needs a chain. It's also the foundation for measured boot and remote
attestation, which is how confidential-computing offerings prove what a machine is running.

## Quick Self-Check

- Why is the reset vector `0xFFFFFFF0` *not* a RAM address, and what would go wrong if the
  firmware assumed it were?
- What is the one-sentence division of labour between firmware and the bootloader?
- Why does an initramfs exist at all — what specific problem would you hit without one?
- A colleague says containers are fast because "they're lightweight VMs." Correct them using
  the sequence above.
- A machine shows the firmware splash screen and then "no bootable device found." Which stages
  definitely succeeded, and which one failed?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Chain-of-loaders framing (the default):** "I'd frame boot as a chicken-and-egg problem: the
  CPU can execute instructions but has no idea where the OS is, and the driver needed to read
  the disk is itself on the disk. The whole process is a chain of increasingly capable loaders
  — each stage small enough to be found by the one before it and smart enough to find the next.
  Firmware in flash finds a boot application, the boot application finds a kernel, the kernel
  finds the real root filesystem via initramfs."
- **Division-of-labour framing (good for correcting the common misconception):** "People
  usually think UEFI scans the disks and lists the installed operating systems. It doesn't —
  firmware locates and executes exactly one program, and everything OS-aware happens after
  that. UEFI finds a program; the bootloader finds an OS. That split is why firmware never
  needs to understand NTFS or ext4."
- **Contrast framing (good when the interviewer's real interest is containers or cloud):** "The
  cleanest way to show what boot actually costs is to compare it with what a container skips. A
  container reuses the host's already-booted kernel, so firmware init, DRAM training, device
  discovery, and kernel init have all happened once, elsewhere. That's the mechanical reason
  container start is milliseconds and VM start is tens of seconds — not that containers are
  'lighter' in some vague sense."

### Vocabulary Builder

- **reset vector** (n. phrase) — the fixed address a CPU begins fetching from when released
  from reset; on x86-64, `0xFFFFFFF0`. *"The reset vector is an address-space location, not a
  RAM location — firmware is mapped there."*
- **firmware** (n.) — code stored in non-volatile motherboard flash that runs before, and
  independently of, any operating system.
- **initramfs** (n.) — a minimal filesystem loaded into RAM by the bootloader, holding the
  drivers needed to reach the real root filesystem. *"The initramfs is what breaks the
  'the driver for the disk is on the disk' loop."*
- **chain of trust** (n. phrase) — each boot stage cryptographically verifying the next before
  executing it; the mechanism behind Secure Boot and remote attestation.
- **"the chicken-and-egg problem here is…"** — a reusable opener for any bootstrapping question
  (boot, compilers, certificate authorities, cluster leader election). Naming the circularity
  before describing the fix signals you understand *why* the machinery exists.

---

**Previous:** [Part 6: Inter-Process Communication (IPC)](06_interprocess_communication.md)  |  **Next:** [Part 8: Disk Layout — GPT, the ESP, and Boot Entries](08_disk_layout_gpt_and_boot_entries.md)
