# AWS Storage Fundamentals: Block Storage, File Storage, EBS, EFS, and Instance Store

## 1. The Core Mental Model

A useful way to understand AWS storage is to separate **storage media**, **storage access model**, and **file system**.

Think in layers:

```text
Application
    ↓
Files / directories
    ↓
File system (ext4, XFS, NTFS, APFS, ...)
    ↓
Block device / storage service
    ↓
Physical or distributed storage infrastructure
```

The most important distinction is:

- **Block storage** gives a system a block device and lets the operating system manage the file system.
- **File storage** exposes a file-and-directory interface, usually through a network file system protocol.
- **Object storage** exposes objects through an API rather than a mounted block device or traditional file system.

AWS examples:

| Storage model | AWS example | What the client sees |
|---|---|---|
| Block | Amazon EBS | A block device / virtual disk |
| File | Amazon EFS | A shared file system |
| Object | Amazon S3 | Objects accessed through an API |
| Ephemeral block | EC2 Instance Store | A local block device on the host |

---

# 2. Is a Laptop SSD/HDD Block Storage?

**Yes, at the device level.**

A laptop's SSD or HDD is a form of **direct-attached block storage (DAS)**.

For example:

```text
Laptop SSD
   ↓
Block device
   ↓
APFS / NTFS / ext4 / etc.
   ↓
Files and directories
```

The SSD itself does not fundamentally understand concepts such as:

```text
/home/surendra/project/app.py
```

Those concepts are primarily handled by the **file system** and operating system.

The storage device exposes addressable storage regions, while the file system maps human-visible files to those regions.

### Important nuance

It is common to say:

> "My laptop has file storage."

That is perfectly reasonable from a user perspective because you interact with files.

Technically, however, the underlying SSD is a **block storage device**, and the operating system places a file system on top of it.

---

# 3. What Exactly Is Block Storage?

Block storage presents storage as a sequence of addressable blocks.

Conceptually:

```text
+--------+--------+--------+--------+--------+
| Block 0| Block 1| Block 2| Block 3| Block 4| ...
+--------+--------+--------+--------+--------+
```

The operating system can read or write blocks without the storage service needing to understand the application's files.

For example, an application might eventually cause an operation conceptually resembling:

```text
read(block 10500)
write(block 10501)
```

The actual implementation is more sophisticated, but this is the right mental model.

## What happens when you format a block device?

Suppose you attach a new EBS volume.

Initially:

```text
EBS volume
    ↓
Raw block device
```

You can create a partition and/or file system:

```text
EBS volume
    ↓
Partition
    ↓
ext4 / XFS / NTFS
    ↓
Files and directories
```

After mounting it:

```text
EBS
 ↓
/dev/nvme1n1
 ↓
ext4
 ↓
/data
```

Applications can now use normal file operations such as:

```text
/data/database.db
/data/logs/app.log
/data/images/photo.jpg
```

The important point is that **the file system is not EBS itself**.

EBS provides the block storage; Linux, Windows, or another operating system provides the file system.

---

# 4. Amazon EBS

**Amazon Elastic Block Store (EBS)** is AWS's persistent block-storage service designed primarily for use with EC2.

A useful analogy is:

> **EBS is like a virtual hard drive/SSD that you can attach to an EC2 instance.**

Conceptually:

```text
                AWS infrastructure
                       │
                       │ network
                       ↓
              ┌─────────────────┐
              │   EBS Volume    │
              │  Block Storage  │
              └─────────────────┘
                       │
                       │ attached
                       ↓
              ┌─────────────────┐
              │   EC2 Instance  │
              │                 │
              │ Linux / Windows │
              └─────────────────┘
                       │
                       ↓
                 File system
                       │
                       ↓
                   Files
```

## EBS is network-attached — but it looks local to the OS

One of the most important concepts is that EBS is implemented as a network-connected storage service.

However, an EC2 operating system normally sees an attached EBS volume as a **block device**.

So an application generally does not need to know:

> "This disk is physically somewhere else in AWS."

The storage interface abstracts that infrastructure away.

This is similar to how a networked service can provide a local-looking interface while the underlying implementation is remote.

---

# 5. EBS vs Your Laptop Disk

| Property | Laptop SSD/HDD | Amazon EBS |
|---|---|---|
| Storage model | Block | Block |
| Physical attachment | Direct-attached | Network-attached service |
| OS can format it | Yes | Yes |
| OS can mount it | Yes | Yes |
| Can contain a file system | Yes | Yes |
| Can contain OS | Yes | Yes |
| Portable between machines | Limited | Can detach/attach subject to AWS rules |
| Managed by cloud provider | No | Yes |
| Typical latency | Very low local-device latency | Network/service-dependent |
| Durability model | Depends on physical device/backups | Designed as persistent AWS storage |

The **fundamental storage interface is the same category: block storage**.

The major architectural difference is **where the storage is physically implemented and how the computer reaches it**.

---

# 6. Where Does the EC2 Operating System Live?

When you launch a normal EBS-backed EC2 instance, the operating system is stored on a **root EBS volume**.

Conceptually:

```text
EC2 Instance
│
├── CPU
├── Memory
├── Network
└── Root EBS Volume
      │
      ├── Boot files
      ├── OS
      ├── System libraries
      └── Applications
```

For example:

```text
EC2
 └── /dev/root
       └── Linux
            ├── /etc
            ├── /var
            ├── /usr
            ├── /home
            └── ...
```

You can also attach additional EBS volumes:

```text
EC2
├── Root EBS
│    └── Operating system
│
├── EBS volume 1
│    └── Database
│
└── EBS volume 2
     └── Application data
```

This separation is common in production systems because different workloads can have different performance, backup, lifecycle, and capacity requirements.

---

# 7. What Happens When an EC2 Instance Stops?

It is important to distinguish **stopping** an instance from **terminating** it.

### Stop

When an EBS-backed EC2 instance is stopped:

```text
EC2 compute resources
        ↓
      stopped

EBS root volume
        ↓
     remains
```

The EBS data normally remains available.

When you start the instance again, the root EBS volume can be used to boot the operating system.

### Terminate

When an EC2 instance is terminated, the fate of each EBS volume depends on its **DeleteOnTermination** setting.

Typically:

- Root volumes are commonly configured to be deleted when the instance is terminated.
- Additional data volumes may be configured to persist.

Therefore, the statement:

> "EBS always survives EC2 termination"

is **not correct**.

A better statement is:

> **EBS volumes have their own lifecycle, but an EBS volume attached to an EC2 instance may be configured to be deleted when the instance terminates.**

---

# 8. EBS Is Persistent Storage, but It Is Not Automatically a Backup

This distinction is extremely important.

Suppose:

```text
EC2
 ↓
EBS
 ↓
database.db
```

If the database file is accidentally deleted:

```text
database.db → deleted
```

EBS does not automatically restore the deleted file.

Persistence means the storage survives certain compute lifecycle events; it does **not** mean every historical version of your data is retained.

For backups, AWS provides mechanisms such as **EBS snapshots**.

A simplified model:

```text
EBS Volume
     │
     ├── current data
     │
     └── Snapshot
           ↓
        point-in-time
        backup/reference
```

Snapshots are an important part of designing recoverable systems.

---

# 9. EBS Volume vs EBS File System

This is a common source of confusion.

An EBS volume is **not the same thing as a file system**.

For example:

```text
EBS volume
   ↓
/dev/nvme1n1
   ↓
XFS
   ↓
/data
   ↓
myfile.txt
```

Each layer has a different responsibility:

### EBS

Provides the block storage.

### File system

Organizes blocks into files and directories.

### Mount point

Makes the file system accessible at a location such as:

```text
/data
```

### Application

Uses files:

```text
/data/config.json
/data/logs/app.log
```

---

# 10. Amazon EFS

**Amazon Elastic File System (EFS)** is fundamentally different from EBS.

EFS provides a **managed network file system**.

The mental model is:

> **EFS is closer to a shared network folder than to a virtual hard disk.**

Conceptually:

```text
                  EFS
          ┌─────────────────┐
          │ Shared File     │
          │ System          │
          └─────────────────┘
             ↑     ↑     ↑
             │     │     │
           EC2-A EC2-B EC2-C
```

Multiple compute instances can mount the same EFS file system.

For example:

```text
EFS
└── /shared
     ├── image1.jpg
     ├── image2.jpg
     ├── config.json
     └── reports/
```

EC2-A and EC2-B can access the same file system.

---

# 11. EBS vs EFS

The simplest comparison is:

```text
EBS
 │
 └── Virtual disk
       │
       └── File system created by you
             │
             └── Files

EFS
 │
 └── Managed network file system
       │
       └── Files and directories
```

| Feature | EBS | EFS |
|---|---|---|
| Type | Block storage | File storage |
| Interface | Block device | File system |
| Typical access | Attached to EC2 | Network mount |
| Multiple EC2 instances | Generally one instance at a time; Multi-Attach has specific limits | Designed for concurrent access |
| File system management | You manage it | AWS manages the underlying file system service |
| Scaling | You provision/modify volume capacity | Elastic file-system capacity |
| Typical use | OS, databases, application disks | Shared files, shared content |
| Example analogy | Virtual hard drive | Shared network drive |

---

# 12. Why Can Multiple EC2 Instances Use EFS?

Because EFS is a **shared file system service**.

Imagine:

```text
                 EFS
                  │
       ┌──────────┼──────────┐
       ↓          ↓          ↓
     EC2-A      EC2-B      EC2-C
       │          │          │
       └──────┬───┴──────┬───┘
              ↓          ↓
          same files
```

All clients interact with the same file-and-directory namespace.

For example:

```text
/shared/report.pdf
```

can be accessed from multiple instances.

This makes EFS useful for workloads such as:

- Shared application content
- Shared configuration/data
- User home directories
- Content management systems
- Some container workloads
- Applications that need a common POSIX file system

---

# 13. Why Isn't EFS Just "EBS for Multiple Instances"?

Because the **interface is fundamentally different**.

With EBS:

```text
EC2
 ↓
block device
 ↓
file system
 ↓
files
```

With EFS:

```text
EC2
 ↓
network file-system client
 ↓
EFS
 ↓
files
```

With EBS, the operating system manages the file system on the attached block device.

With EFS, the managed service exposes the file-system interface.

That distinction affects:

- How applications access data
- File-system semantics
- Sharing behavior
- Performance characteristics
- Administration
- Failure modes
- Scaling
- Cost model

---

# 14. What About EBS Multi-Attach?

There is an important nuance to the simple statement:

> "One EBS volume can only be attached to one EC2 instance."

That is not universally true.

Certain EBS volume configurations support **Multi-Attach**, allowing a single volume to be attached to multiple supported EC2 instances simultaneously.

However, this is **not equivalent to EFS**.

Multi-Attach has specific restrictions and requires an appropriate application/file-system design, particularly around concurrent writes.

A traditional file system that assumes exclusive ownership of a disk should not simply be mounted read/write from multiple independent machines without considering its concurrency semantics.

So the useful mental model remains:

> **EBS is primarily a block-storage primitive; EFS is specifically designed as a shared file-storage service.**

---

# 15. EBS and Databases

EBS is commonly appropriate for databases because databases often want control over storage behavior.

For example:

```text
Database
   ↓
File system / raw device
   ↓
EBS
```

A database may care about:

- Predictable I/O behavior
- IOPS
- Throughput
- Latency
- Durability
- Volume size
- Snapshots/backups
- Separation of data and logs

Different EBS volume types are designed for different performance/cost requirements.

The important conceptual point is:

> The database does not need EBS to understand SQL tables. EBS provides the block storage underneath the database's storage layer.

---

# 16. EC2 Instance Store

EBS is not the only block storage associated with EC2.

Some EC2 instance types provide **instance store**, sometimes called **ephemeral storage**.

The architecture is roughly:

```text
EC2 Host
│
├── CPU
├── Memory
├── Network
└── Local NVMe / Instance Store
```

Unlike EBS, instance store is physically local to the host.

This can provide very high local performance, but it has a critical property:

> **Instance store is temporary/ephemeral and should not be treated as durable persistent storage.**

If an instance is stopped, terminated, or otherwise loses the underlying host depending on the lifecycle behavior, data in instance store may be lost.

Therefore:

### Good candidates

- Temporary processing data
- Caches
- Scratch space
- Intermediate computation results
- Data that can be recreated

### Poor candidates

- Only copy of a database
- Critical application state
- Important documents
- Data that must survive instance lifecycle events

---

# 17. EBS vs Instance Store

| Property | EBS | Instance Store |
|---|---|---|
| Type | Block | Block |
| Physical location | AWS storage infrastructure | Local EC2 host |
| Persistent | Yes, subject to volume lifecycle settings | No |
| Detachable | Yes | No in the same sense |
| Survives instance lifecycle | Designed for persistence | Ephemeral |
| Typical use | OS, databases, persistent data | Cache, scratch, temporary high-speed data |

This gives a useful architectural spectrum:

```text
Persistent                                      Ephemeral
   │                                                │
   ↓                                                ↓

EBS -------------------------------------- Instance Store
Network-attached                           Physically local
Persistent                                 Temporary
```

---

# 18. Block Storage vs File Storage: The Fundamental Difference

The most useful way to remember this is to ask:

> **What interface does the consumer receive?**

### Block storage

The consumer receives a block device.

```text
Application
    ↓
File system
    ↓
Block device
    ↓
Storage
```

The consumer can typically choose/manage the file system.

### File storage

The consumer receives a file-system interface.

```text
Application
    ↓
Files / directories
    ↓
Network file system
    ↓
Storage service
```

The service manages much more of the underlying storage organization.

---

# 19. Object Storage Is a Third Category

Do not limit the discussion to only block and file storage.

Amazon S3 is **object storage**.

Its mental model is:

```text
Bucket
 │
 ├── object-1
 ├── object-2
 └── object-3
```

Applications interact with S3 through APIs.

For example, conceptually:

```text
PUT object
GET object
DELETE object
```

S3 does not normally appear inside an EC2 instance as:

```text
/dev/nvme1n1
```

nor does it behave like a traditional shared POSIX file system.

So:

| | Block | File | Object |
|---|---|---|---|
| AWS example | EBS | EFS | S3 |
| Interface | Block device | File system | API |
| Filesystem managed by client? | Usually yes | No, service provides it | No traditional filesystem |
| Shared access | Limited/configuration-dependent | Yes | Yes through API |
| Typical use | OS/database disks | Shared files | Backups, media, data lakes, static assets |

---

# 20. A Better Analogy

Imagine a physical office.

### Block storage = empty filing cabinet drawers

You get the storage space and decide how to organize it.

```text
Drawer
 ├── blocks
 ├── blocks
 └── blocks

You create the organization system.
```

### File storage = organized shared filing room

The storage service already provides:

```text
Room
 ├── Folder A
 │    ├── file1
 │    └── file2
 └── Folder B
      └── file3
```

Multiple people can use the same organization.

### Object storage = warehouse with labeled packages

You interact with packages using an inventory system:

```text
PUT package
GET package
DELETE package
```

You don't directly manipulate the warehouse's physical storage blocks.

---

# 21. A Critical Correction to a Common Statement

A statement like:

> "Block storage is raw unformatted disk space."

is useful for beginners, but technically incomplete.

A block-storage device **can be formatted**, partitioned, and used with a file system.

So the better statement is:

> **Block storage exposes addressable blocks to a consumer. A file system can then be created on those blocks to provide files and directories.**

Similarly:

> **File storage is not simply "block storage plus a file system."**

A managed file-storage service such as EFS exposes a higher-level file-system interface and manages the underlying storage infrastructure for you.

---

# 22. The Full AWS EC2 Storage Picture

A typical EC2 system might look like this:

```text
                         EC2
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ↓               ↓                ↓
       Root EBS        Data EBS           EFS
          │               │                │
       Block            Block             File
          │               │                │
       ext4/XFS        ext4/XFS        Managed FS
          │               │                │
          ↓               ↓                ↓
       OS files       DB / data       Shared files
```

And possibly:

```text
                 EC2
                  │
                  ↓
             Instance Store
                  │
                  ↓
            Scratch / cache
```

And outside EC2:

```text
                   S3
                    │
                    ↓
             Object storage
                    │
                    ↓
       backups / media / data lake
```

---

# 23. How to Decide Which One to Use

A simple decision tree:

```text
Do I need storage?
       │
       ├── Need a virtual disk for one compute system?
       │        ↓
       │       EBS
       │
       ├── Need a shared file system across compute instances?
       │        ↓
       │       EFS
       │
       ├── Need temporary, very local storage?
       │        ↓
       │       Instance Store
       │
       └── Need API-based storage for large amounts of
           objects/files, backups, media, etc.?
                ↓
               S3
```

This is a simplified decision tree; specialized AWS services may be better for particular workloads.

---

# 24. The Most Important Concepts to Remember

### Concept 1 — Block vs File is about the interface

```text
Block → blocks
File  → files/directories
Object → objects/API
```

### Concept 2 — A physical SSD can be block storage

Your laptop SSD is fundamentally a block device.

```text
SSD
 ↓
Block storage
 ↓
APFS
 ↓
Files
```

### Concept 3 — EBS is cloud block storage

```text
EBS
 ↓
Block device presented to EC2
 ↓
File system
 ↓
Files
```

### Concept 4 — EFS is cloud file storage

```text
EFS
 ↓
Network file-system interface
 ↓
Files/directories
```

### Concept 5 — EFS is designed for shared access

Multiple supported clients can mount the same EFS file system.

### Concept 6 — EBS is not automatically a backup

Persistence and backup are different concepts.

### Concept 7 — Instance Store is different from EBS

Both are block storage, but:

```text
EBS             → persistent
Instance Store  → ephemeral/local
```

### Concept 8 — Storage location and storage interface are different dimensions

This is perhaps the most important architectural insight.

A storage device can be:

```text
Local + Block
Network + Block
Network + File
```

Examples:

```text
Laptop SSD      → Local + Block
EBS             → Network + Block
EFS             → Network + File
Instance Store  → Local + Block
```

---

# 25. One Final Mental Model

If you remember only one diagram, remember this:

```text
                 STORAGE INTERFACES

       ┌──────────────┬──────────────┬──────────────┐
       │              │              │              │
       ↓              ↓              ↓
     BLOCK           FILE          OBJECT
       │              │              │
       ↓              ↓              ↓
     EBS             EFS            S3
       │              │              │
       ↓              ↓              ↓
   disk-like       shared FS      API-based
   interface       interface      interface


                 EC2 LOCAL STORAGE

              Instance Store
                    │
                    ↓
              Local + Block
              + ephemeral
```

And for an EC2 instance:

```text
                   EC2
                    │
        ┌───────────┼────────────┐
        ↓           ↓            ↓
     Root EBS    Data EBS       EFS
        │           │            │
      Block       Block         File
        │           │            │
     ext4/XFS    ext4/XFS      EFS FS
        │           │            │
        ↓           ↓            ↓
       OS        Database      Shared data
```

## In one sentence

> **EBS is persistent cloud block storage that behaves like a virtual disk attached to EC2; EFS is a managed shared network file system; instance store is local ephemeral block storage; and S3 is API-based object storage.**

---

# Quick Revision Cheat Sheet

| Term | Remember it as |
|---|---|
| Block storage | "Give me blocks; I'll manage the file system." |
| File storage | "Give me a shared file system." |
| Object storage | "Store/retrieve objects through an API." |
| EBS | "Virtual persistent disk for EC2." |
| EFS | "Managed shared network file system." |
| Instance Store | "Fast local temporary disk." |
| S3 | "Massively scalable object store." |
| ext4/XFS/NTFS/APFS | File systems |
| `/dev/nvme...` | Example block-device representation on Linux |
| Mount | Make a file system accessible at a directory |
| Snapshot | Point-in-time storage backup mechanism |
| DAS | Direct-attached storage |
| NAS | Network-attached file storage |
| SAN | Networked block-storage architecture |

