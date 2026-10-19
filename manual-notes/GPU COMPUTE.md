**Why GPUs Power Modern AI**

While CPUs are designed for general-purpose computing, GPUs are specialized parallel accelerators that excel at the **massive matrix multiplications** required by neural networks.

* **Process thousands of operations simultaneously**, making them ideal for AI workloads  
* Form the backbone of both deep learning training and inference pipelines  
* Essential knowledge for every AI infrastructure engineer

**GPU vs CPU Architecture**

### **CPU Architecture**

* Few powerful cores (4–64)  
* Optimized for sequential tasks  
* **Latency-focused** design  
* Complex control logic and large caches

### **GPU Architecture**

* Thousands of smaller cores  
* Designed for massive parallelism  
* **Throughput-optimized** design  
* Efficiently handles large tensor operations

Modern AI systems often utilize **hybrid architectures** leveraging both CPU and GPU strengths, with CPUs handling control flow and GPUs accelerating compute-intensive operations.

**GPU Cores & Streaming Multiprocessors**

GPU cores are organized into **Streaming Multiprocessors (SMs)** for NVIDIA or **Compute Units (CUs)** for AMD. This architecture enables efficient parallel processing:

* Each SM executes multiple threads concurrently  
* **Warps** (groups of 32 threads) execute in lockstep  
* Designed for SIMD (Single Instruction, Multiple Data) execution  
* Optimized for the matrix/vector operations that power AI

### **Tensor Cores: AI's Secret Weapon**

**Introduction**

Specialized hardware units for accelerating **matrix multiplication operations**, introduced in NVIDIA's Volta (V100) architecture.

**Capabilities**

Dramatically accelerate FP16, BF16, and INT8 matrix operations common in deep learning.

**Impact**

Deliver **10–100x speedups** for key AI workloads, including LLMs and computer vision.

### **1\. What is a Tensor Core?**

A **Tensor Core** is a specialized compute unit inside modern NVIDIA GPUs designed primarily to perform **matrix multiply-accumulate (MMA)** operations extremely quickly.

A fundamental operation in neural networks is:

C=A×B+C

For example:

A × B

where `A` and `B` are matrices containing thousands or millions of values.

Normal CUDA cores can perform these operations, but Tensor Cores are **specifically designed in hardware to execute matrix operations much more efficiently**.

### **2\. Why are matrix multiplications so important for AI?**

Most neural-network computation ultimately involves operations similar to:

Input × Weights → Output

For example, a neural-network layer may perform:

\[batch × features\] × \[features × neurons\]

                    ↓

                 output

For an LLM, this happens repeatedly in:

* Linear layers  
* Attention projections  
* Query/Key/Value transformations  
* Feed-forward/MLP layers  
* Output projections

So if the GPU can make matrix multiplication dramatically faster, **the entire AI workload becomes faster**.

### **3\. Tensor Cores vs CUDA Cores**

Think of it this way:

| CUDA Core | Tensor Core |
| ----- | ----- |
| General-purpose GPU computation | Specialized AI computation |
| Handles individual arithmetic operations | Handles matrix operations |
| Flexible | Highly specialized |
| Good for many types of workloads | Excellent for neural-network workloads |
| Used for general GPU programming | Optimized for MMA |

A simplified view:

GPU  
│  
├── CUDA Cores  
│    └── General GPU computation  
│  
├── Tensor Cores  
│    └── Matrix multiplication / AI  
│  
├── L1 / Shared Memory  
│  
└── Other GPU hardware

### **4\. What does FP16, BF16 and INT8 mean?**

These are different numerical representations used to perform computation.

#### **FP32**

32-bit floating point:

FP32 \= 32 bits

High numerical precision, but requires more memory and computation.

#### **FP16**

16-bit floating point:

FP16 \= 16 bits

Uses half the storage of FP32 and can provide significantly higher throughput on Tensor Cores.

#### **BF16**

Brain Floating Point 16:

BF16 \= 16 bits

Also uses 16 bits but has the **same exponent size as FP32**, making it particularly useful for deep-learning training.

#### **INT8**

8-bit integer:

INT8 \= 8 bits

Much smaller than FP16/FP32 and commonly used for **quantized inference**.

So generally:

FP32 → high precision, expensive

FP16/BF16 → lower precision, very fast AI computation

INT8 → even smaller, extremely efficient inference

| Precision | Meaning | Bits | CUDA Cores — NVIDIA | Tensor Cores — NVIDIA | AMD equivalent / support | Typical AI use |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **FP32** | **Floating Point 32-bit** | 32 | ✅ Yes | ✅ Architecture-dependent | AMD **Stream Processors / ALUs** | High-precision training, general compute |
| **TF32** | **TensorFloat-32** | 32\* | ❌ Not standard CUDA-core FP32 | ✅ NVIDIA Tensor Cores | No direct AMD naming equivalent | AI training with FP32-like range |
| **FP16** | **Floating Point 16-bit** | 16 | ✅ Yes | ✅ Yes | AMD Stream Processors \+ **Matrix Cores** | Training & inference |
| **BF16** | **Brain Floating Point 16-bit** | 16 | ✅ Supported on newer architectures | ✅ Yes | AMD Stream Processors \+ Matrix Cores on supported GPUs | LLM training & inference |
| **FP8** | **Floating Point 8-bit** | 8 | ⚠️ Architecture-dependent | ✅ Newer NVIDIA Tensor Cores | AMD Matrix Cores on supported architectures | LLM training/inference |
| **INT8** | **Integer 8-bit** | 8 | ✅ Supported instructions | ✅ Yes | AMD compute units / Matrix Cores | Quantized inference |
| **INT4** | **Integer 4-bit** | 4 | ⚠️ Architecture-dependent | ✅ Newer architectures | AMD Matrix Cores on supported GPUs | Very-low-precision LLM inference |
| **FP4** | **Floating Point 4-bit** | 4 | ❌ Older architectures | ✅ Blackwell-generation Tensor Cores | AMD support depends on architecture/software | Very-low-precision AI |

# **GPU Memory Hierarchy**

Memory access patterns critically impact AI workload performance. Engineers must understand the GPU memory hierarchy to optimize their code.

### **Memory Hierarchy**

**1\. Registers**

**2\. Shared Memory**

**3\. L1/L2 Cache**

**4\. Global Device Memory (HBM/GDDR)**

### **From top to bottom:**

* Decreasing speed  
* Increasing capacity  
* Wider accessibility across threads

### **Key challenge:**

Optimizing AI workloads requires minimizing memory bottlenecks by maximizing data locality and reducing high-latency transfers.

| Level | Memory | Speed | Capacity | Who uses it? |
| ----- | ----- | ----- | ----- | ----- |
| **1** | Registers | 🚀 Fastest | Very small | Individual thread |
| **2** | Shared Memory | 🚀 Very fast | Small | Threads in the same SM/block |
| **3** | L1/L2 Cache | ⚡ Fast | Medium | Hardware-managed, multiple threads/SMs |
| **4** | HBM/GDDR | 🐢 Slowest | Largest | GPU-wide |

Think of a worker doing calculations:

                FASTEST  
                   ▲  
                   │  
             Registers  
          "In my hand"  
                   │  
            Shared Memory  
          "On my desk"  
                   │  
             L1 / L2 Cache  
          "Nearby cupboard"  
                   │  
           HBM / GDDR Memory  
            "Warehouse"  
                   │  
                SLOWEST

The closer the data is to the **GPU execution unit**, the faster it can be accessed.

**Registers and shared memory are physically much closer to the compute hardware**, while HBM/GDDR is external high-bandwidth device memory.

For an LLM, this becomes extremely important because **GPU performance can be limited either by compute or by memory bandwidth**.

That's why when evaluating GPUs, you should look at both:

**Compute throughput (TFLOPS/TOPS)** \+ **Memory bandwidth (GB/s or TB/s)**.

# **The Roofline Model — Compute-Bound vs Memory-Bound**

Every mention above of "memory bottleneck" or "GPU sits idle waiting for data" is informally pointing at the same formal tool infrastructure engineers actually use: the **roofline model**. It answers one question precisely — *for this specific workload, which ceiling am I actually hitting: the GPU's compute limit, or its memory-bandwidth limit?*

## **1. Arithmetic intensity**

> **Arithmetic Intensity (AI) = FLOPs performed ÷ Bytes moved from memory**

Measured in FLOPs/byte. It's the answer to: **for every byte fetched from HBM, how much math do you get to do with it before you need the next byte?**

## **2. The two ceilings, drawn as a graph**

Achievable  
performance  
(FLOPs/sec)  
      ▲  
      │                    ┌───────────────────  ← flat ceiling \= Peak Compute (TFLOPS)  
      │                 ⟋  
      │              ⟋       compute-bound region  
      │           ⟋          (more AI doesn't help — GPU math is the limit)  
      │        ⟋  
      │     ⟋    ← the "knee": AI \= Peak Compute ÷ Peak Bandwidth  
      │  ⟋  
      │⟋   memory-bound region  
      │    (sloped ceiling — bandwidth is the limit; more compute doesn't help)  
      └──────────────────────────────────────────► Arithmetic Intensity (FLOPs/byte)

The formula behind the sloped part of the line:

> **Achievable performance \= min( Peak Compute, Peak Bandwidth × Arithmetic Intensity )**

Below the knee, you are memory-bound no matter how fast the Tensor Cores are. Above it, you are compute-bound no matter how fast HBM is.

## **3. Worked example: one decode step vs. a large training batch**

Using the H100 numbers already in this doc (989 TFLOPS BF16 Tensor Core, 3 TB/s HBM3):

Knee AI \= 989,000 GFLOPS ÷ 3,000 GB/s ≈ **330 FLOPs/byte**

**Autoregressive decoding, one new token, batch \= 1:** each step reads essentially the *entire* weight matrix once (≈2 bytes/param in FP16) and performs ≈2 FLOPs per parameter (one multiply-add):

AI ≈ (2 × N) ÷ (2 × N × 2 bytes) \= **0.5 FLOPs/byte**

That's roughly **660× below the knee** — single-sequence decoding is *always* deeply memory-bound, on any modern GPU, regardless of how many TFLOPS the card has. This is exactly the "Tensor Cores sit idle waiting for HBM" diagram from the section above, now with a number attached to *why*.

**Large-batch training/prefill:** the same weights get reused across every sequence in the batch before being re-fetched, so AI scales roughly with batch size. A large enough batch pushes AI past the knee into compute-bound territory — which is precisely why **batch size is the single biggest lever for GPU utilization**, and why small-batch inference and large-batch training behave like completely different workloads on identical hardware.

| Regime | Typical AI | Bound by | Fix |
| ----- | ----- | ----- | ----- |
| Single-sequence decode | \~0.5 FLOPs/byte | Memory bandwidth | Batch requests together, use continuous batching |
| Small-batch training | Tens of FLOPs/byte | Often still memory | Raise batch size, use mixed precision |
| Large-batch training/prefill | Hundreds+ FLOPs/byte | Compute (Tensor Cores) | Higher precision throughput, more/faster GPUs |

> **The roofline model is the diagnostic; batch size, precision, and kernel fusion are the treatments.** Profiling tools mentioned later in this doc (Nsight, PyTorch Profiler) exist largely to locate where a real workload sits on this graph.

# **High-Bandwidth Memory (HBM)**

Modern AI GPUs utilize **High-Bandwidth Memory** technology to address the memory bottlenecks in large model training and inference:

* Next-gen GPUs use **HBM2e and HBM3** technology  
* Provides substantially higher bandwidth than GDDR6  
* Enables training of massive Large Language Models  
* Example: NVIDIA H100 delivers up to **3 TB/s memory bandwidth**

Memory throughput is often the limiting factor in AI workloads, making HBM a critical advancement.

**AI GPUs need extremely fast memory because the GPU can calculate much faster than it can fetch data from memory.** 

### **1\. What is HBM?**

**HBM \= High-Bandwidth Memory.**

It is a type of high-performance memory designed to provide **very high memory bandwidth** to GPUs.

Think of it as the GPU's large, high-speed data store:

GPU Compute  
	│  
│ needs data  
           ▼  
┌───────────────┐  
│     HBM   	                  │  
│ Model weights 	│  
│ Activations   	│  
│ Input data    		│  
└───────────────┘

For AI workloads, the GPU constantly moves:

* Model weights  
* Activations  
* Input tensors  
* Intermediate results

between compute units and memory.

## **2\. What does "bandwidth" mean?**

Memory bandwidth is basically:

> **How much data can the GPU move between memory and compute per second.**

For example:

**3 TB/s** means, theoretically, the memory subsystem can transfer up to roughly:

3 TB of data per second

That's enormous.

Compare:

Typical CPU DDR memory  
       ↓  
\~100 GB/s range

GPU GDDR  
       ↓  
Hundreds of GB/s

GPU HBM  
       ↓  
1+ TB/s

The exact numbers depend on the hardware generation.

## **3\. Why does an LLM need so much bandwidth?**

Imagine you have a huge model:

70B parameter LLM

If using FP16:

70 billion × 2 bytes  
≈ 140 GB

So the GPU needs to continuously work with **hundreds of gigabytes of model data**.

If the GPU's compute units are extremely fast but memory can't feed them quickly enough:

Tensor Cores  
    │  
    │ "Give me more data\!"  
    ▼  
   HBM  
    │  
    │ data arrives too slowly  
    ▼  
GPU sits partially idle

This is called a **memory bottleneck**.

## **4\. HBM vs GDDR**

The slide mentions **GDDR6** and **HBM2e/HBM3**.

Both are GPU memory technologies, but their architectures are different.

### **GDDR**

Typically:

GPU ─────── GDDR chips  
GPU ─────── GDDR chips  
GPU ─────── GDDR chips

GDDR chips are generally placed around the GPU package/board.

### **HBM**

HBM uses vertically stacked memory dies and is placed very close to the GPU package.

Conceptually:

      GPU  
┌──────────────┐  
│ GPU Compute  │  
└──────────────┘  
      ││││  
┌─────┴┴┴┴─────┐  
│   HBM Stack   │  
│   HBM Stack   │  
│   HBM Stack   │  
└───────────────┘

This allows a **very wide memory interface**, which is a major reason HBM can achieve extremely high bandwidth.

## **5\. HBM capacity vs bandwidth**

This distinction is **very important**.

### **Capacity**

How much data can fit:

80 GB HBM

means the GPU has approximately 80 GB of high-bandwidth memory.

### **Bandwidth**

How quickly data can move:

3.35 TB/s

means the memory subsystem can theoretically move around 3.35 TB every second.

So:

> **Capacity \= How much?**

> **Bandwidth \= How fast?**

A GPU can have:

80 GB memory  
\+  
3 TB/s bandwidth

Those are two different specifications.

## **6\. Why HBM is especially important for LLM inference**

Consider an LLM generating tokens.

For each token, the GPU needs to perform enormous amounts of computation involving model weights and KV cache.

If the workload is **memory-bandwidth bound**, having faster HBM can directly improve token-generation performance.

Simplified:

               LLM inference  
                    │  
                    ▼  
             Model weights  
                    │  
                    ▼  
                   HBM  
                    │  
            ┌───────┴───────┐  
            ▼               ▼  
       Tensor Cores     CUDA Cores  
            │               │  
            └───────┬───────┘  
                    ▼  
                 Output

This is why an AI GPU isn't judged only by:

**"How many CUDA/Tensor Cores does it have?"**

You also need to ask:

**"How much HBM does it have and how much bandwidth does it provide?"**

**HBM provides extremely high memory bandwidth, which helps keep the GPU's massive compute capability fed with data.** 

## **7. The KV Cache — why generation memory grows every token**

During autoregressive generation, self-attention at token *T* needs the Key and Value vectors of **every** earlier token. Recomputing all of them from scratch on every new token would be enormously wasteful, so inference servers cache them instead — this is the **KV cache**, and it is frequently the *real* memory bottleneck in LLM serving, not the model weights.

Size formula:

> **KV cache bytes \= 2 × num\_layers × num\_heads × head\_dim × seq\_len × batch\_size × bytes\_per\_value**

(the leading 2 is for storing both K *and* V.)

**Worked example** — a 70B-class model shape (80 layers, 64 heads, head\_dim 128), FP16, one 4,096-token sequence, batch \= 1:

2 × 80 × 64 × 128 × 4,096 × 1 × 2 bytes ≈ **10.7 GB — for a single sequence.**

That's memory spent on *cache*, separate from the \~140 GB of FP16 weights this doc already computed for a 70B model. The reason this number gets serious fast is that it scales with **three independent multipliers at once**:

Sequence length ↑ → KV cache ↑ (linear)  
Batch size (concurrent users) ↑ → KV cache ↑ (linear)  
Model size (layers × heads × head\_dim) ↑ → KV cache ↑ (linear)

Serve 32 concurrent users at 4K context and that single-sequence 10.7 GB becomes \>340 GB of cache alone — which is why production LLM serving is as much a **memory-capacity planning problem** as a compute problem, and why the naive fix ("just pre-allocate the max-length buffer per request") wastes enormous amounts of HBM on requests that finish early. The section on vLLM/PagedAttention later in this doc is the industry's answer to exactly that waste.

# **GPU Interconnects**

### **PCIe**

* Standard connection between CPU and GPU  
* PCIe 4.0/5.0 offers improved but still limited bandwidth  
* Can become a bottleneck in multi-GPU systems

### **NVLink/NVSwitch**

* **Ultra-high bandwidth** GPU-to-GPU connections  
* Up to **900 GB/s bidirectional bandwidth (NVLink 4.0)**  
* Enables efficient multi-GPU communication

### **Impact on AI**

* Critical for **distributed training** of large models  
* Reduces communication overhead in model parallelism  
* Essential for scaling models like GPT and beyond

**900 GB/s NVLink 4.0** figure is for the Hopper generation, such as H100 SXM. The newer Blackwell generation uses **NVLink 5.0 at 1.8 TB/s per GPU**, double the per-GPU bandwidth. 

## **1\. PCIe vs NVLink — simple explanation**

Think of a server with multiple GPUs:

                 CPU  
                  │  
                PCIe  
                  │  
       ┌──────────┴──────────┐  
       │                     │  
     GPU 0                 GPU 1  
       │                     │  
       └────── NVLink ───────┘

**PCIe** is the general-purpose connection between the GPU and the server/CPU.

**NVLink** is NVIDIA's specialized high-speed interconnect for GPU-to-GPU communication.

So:

> **PCIe \= general highway into the GPU**

> **NVLink \= high-speed highway between GPUs**

# **2\. Why does GPU-to-GPU communication matter?**

Suppose you have a model that doesn't fit on one GPU.

For example:

Model \= 400 GB

GPU 0 → 80 GB  
GPU 1 → 80 GB  
GPU 2 → 80 GB  
GPU 3 → 80 GB  
GPU 4 → 80 GB

Now the GPUs have to communicate constantly.

For example:

GPU 0  
 │  
 │ "I need data from GPU 2"  
 ▼  
GPU 2

If this communication is slow, your expensive Tensor Cores can sit idle waiting for data.

That's why **interconnect bandwidth becomes extremely important in multi-GPU AI systems**.

# **3\. PCIe**

> PCIe 4.0/5.0 offers improved but still limited bandwidth.

For example, NVIDIA's H100 has a **PCIe Gen 5 x16 interface with 128 GB/s total bandwidth**, or 64 GB/s in each direction.

Conceptually:

CPU  
│  
│ PCIe Gen 5  
│ \~128 GB/s total  
▼  
GPU

PCIe is excellent for:

* Connecting GPU to CPU  
* Connecting GPU to server infrastructure  
* Host-to-device transfers  
* General I/O

But it isn't ideal for extremely communication-heavy multi-GPU training.

# **5\. And then comes NVSwitch**

This is where things become really interesting.

With only two GPUs, you could imagine:

GPU 0 ←──── NVLink ────→ GPU 1

But what about **8 GPUs**?

You don't want a complicated mesh of connections between every GPU.

That's where **NVSwitch** comes in.

GPU 0 ──┐

GPU 1 ──┤

GPU 2 ──┤

GPU 3 ──┤

       ├── NVSwitch

GPU 4 ──┤

GPU 5 ──┤

GPU 6 ──┤

GPU 7 ──┘

NVSwitch acts somewhat like a **very high-speed switch for GPU communication**.

It allows GPUs to communicate efficiently with other GPUs in the NVLink domain.

NVIDIA's H100 systems use NVSwitch to provide high-bandwidth, all-to-all GPU connectivity.

# **6\. What's newer today?**

Since you're learning this in **2026**, don't stop at the slide's NVLink 4 example.

### **NVIDIA interconnect evolution**

| Generation | GPU architecture | NVLink bandwidth / GPU | Status |
| ----- | ----- | ----- | ----- |
| NVLink 3 | Ampere | \~600 GB/s | Older |
| **NVLink 4** | **Hopper (H100/H200)** | **900 GB/s** | Current/previous generation |
| **NVLink 5** | **Blackwell (B200/GB200/GB300)** | **1.8 TB/s** | **Current newer generation** |
| NVLink 6 | Rubin | **3.6 TB/s** | Next generation |

## **GPU Compute Precision**

Different AI workloads require different numerical precision. Modern GPUs support multiple precision formats, with **Tensor Cores optimized for mixed-precision operations**.

| Format | Bits | Use Case |
| ----- | ----- | ----- |
| **FP32** | 32 | Standard training |
| **FP16/BF16** | 16 | Efficient training |
| **INT8** | 8 | Inference |
| **INT4** | 4 | Efficient inference |

**Engineers must balance accuracy vs. speed when selecting precision formats for their AI workloads.**

The main idea is:

> **Precision determines how accurately we represent numbers, but lower precision generally allows GPUs to process more data faster and use less memory.**

Think of it as:

FP32 → FP16/BF16 → INT8 → INT4  
More precision              Less precision  
More memory                 Less memory  
Lower throughput            Higher potential throughput

But **lower precision does not automatically mean "better."** You trade some numerical accuracy for speed and memory efficiency.

## **1\. FP32 — 32-bit Floating Point**

**FP \= Floating Point**

FP32 uses **32 bits per number**.

Example:

FP32  
↓  
32 bits/value  
↓  
High numerical precision  
↓  
More memory \+ computation

It has traditionally been widely used for training because it provides good numerical accuracy.

However, modern AI training often doesn't need everything to be FP32.

## **2\. FP16 — 16-bit Floating Point**

**FP16 \= 16-bit Floating Point**

It uses half the bits of FP32:

FP32 → 32 bits  
FP16 → 16 bits

That means substantially less memory is required for storing values.

Tensor Cores are highly optimized for FP16 matrix operations.

This makes FP16 very useful for:

* Deep-learning training  
* LLM inference  
* Matrix multiplication

## **3\. BF16 — Brain Floating Point 16-bit**

**BF16 \= Brain Floating Point 16-bit**

It is also 16 bits, but its structure differs from FP16.

The important practical difference is:

**BF16 maintains the same exponent width as FP32**, giving it a much larger numerical range than FP16.

Simplified:

FP32  
│  
├── Large range  
└── High precision

BF16  
│  
├── Large range ≈ FP32  
└── Lower precision

FP16  
│  
├── Smaller range  
└── Higher precision than BF16

This makes **BF16 particularly attractive for modern LLM training** because it is often more numerically robust than FP16 while retaining the efficiency of 16-bit computation.

# **4\. INT8 — 8-bit Integer**

**INT \= Integer**

INT8 uses only:

8 bits/value

Unlike FP32/FP16/BF16, it represents numbers as integers rather than floating-point values.

It is commonly used for **quantization**.

For example, instead of storing:

FP16 weights

you can quantize them approximately into:

INT8 weights

Benefits:

* \~50% less storage than FP16  
* Lower memory bandwidth requirements  
* Faster inference on hardware optimized for INT8  
* More models can fit into GPU memory

This is particularly useful for **LLM inference**.

---

# **5\. INT4 — 4-bit Integer**

INT4 uses only:

4 bits/value

Compared with FP16:

FP16 \= 16 bits  
INT4 \= 4 bits

INT4 uses 1/4 the raw storage

This is extremely useful for **LLM quantization**.

For example, a large model that requires:

140 GB @ FP16

could theoretically require roughly:

35 GB @ INT4

before accounting for quantization metadata, scales, activations, KV cache, etc.

That's a huge difference.

# **6\. Why does lower precision make GPUs faster?**

There are several reasons.

### **Less memory**

FP32 → 4 bytes  
FP16 → 2 bytes  
INT8 → 1 byte  
INT4 → 0.5 byte

So more values can fit into the GPU's memory hierarchy.

### **Less memory bandwidth required**

Suppose you need to read 1 billion values.

FP32:

1B × 4 bytes \= 4 GB

FP16:

1B × 2 bytes \= 2 GB

INT8:

1B × 1 byte \= 1 GB

So the GPU has less data to move from HBM.

This is particularly important for **memory-bandwidth-bound LLM inference**.

### **Higher specialized compute throughput**

Modern NVIDIA Tensor Cores are designed to perform enormous numbers of operations at lower precisions.

Conceptually:

            Tensor Core  
                 │  
      ┌──────────┼──────────┐  
      ↓          ↓          ↓  
    FP16       BF16        FP8  
      │          │          │  
      └──────────┼──────────┘  
                 ↓  
          Matrix Multiply

The exact supported formats and throughput depend on the GPU generation.

---

**What does "mixed precision" mean?**

This is one of the **most important concepts for LLM training**.

It does **not** necessarily mean:

> "The entire model is FP16."

Instead, different operations can use different precisions.

For example:

                LLM Training  
                     │  
       ┌─────────────┼─────────────┐  
       ↓             ↓             ↓  
    FP16/BF16      FP32          FP16/BF16  
    Matrix math    Some state    Matrix math  
       │             │             │  
       └─────────────┼─────────────┘  
                     ↓  
                  Result

A simplified example:

**Matrix multiplication:**

FP16/BF16  
  ↓  
Tensor Core  
  ↓  
FP32 accumulation

This gives you much of the speed/memory benefit of lower precision while retaining higher precision where it matters.

---

# **8\. Training vs inference**

Your slide gives a useful simplified distinction:

|  | Training | Inference |
| ----- | ----- | ----- |
| **FP32** | ✅ | Sometimes |
| **FP16** | ✅ | ✅ |
| **BF16** | ⭐ Very common | ✅ |
| **FP8** | ✅ Increasingly important | ✅ |
| **INT8** | Less common | ⭐ Very common |
| **INT4** | Rare for training | ⭐ Very useful |

For modern LLM infrastructure, a useful mental model is:

TRAINING  
  ↓  
BF16 / FP16  
  ↓  
FP8 increasingly used  
  ↓  
Tensor Cores

while inference often looks like:

INFERENCE  
  ↓  
FP16 / BF16  
  ↓  
FP8  
  ↓  
INT8  
  ↓  
INT4

The choice depends heavily on the model, GPU, framework, and required accuracy.

**Quantization** means taking a model's numbers from a **higher-precision format** and representing them using **fewer bits**, while trying to keep the model's accuracy close to the original.

For example:

Original model  
FP16 weights  
  ↓  
Quantization  
  ↓  
INT8 or INT4 weights

### **Simple example**

Suppose the model has a weight:

FP16:  0.7364

Instead of storing that value with 16-bit floating-point precision, quantization might represent it approximately using an 8-bit integer:

FP16:  0.7364  
       ↓  
INT8:    94       ← encoded/quantized value

The model also keeps **scaling information** so it can approximately recover the original numerical range.

So conceptually:

FP16 value  
  │  
  │ Quantize  
  ▼  
INT8 value \+ scale

It is **not simply rounding everything to an integer**.

---

## **Why do we quantize LLMs?**

The biggest benefit is **memory reduction**.

Imagine a 70-billion-parameter model.

### **FP16**

Each parameter ≈ 2 bytes:

70B × 2 bytes  
≈ 140 GB

### **INT8**

Approximately 1 byte per parameter:

70B × 1 byte  
≈ 70 GB

### **INT4**

Approximately 0.5 byte per parameter:

70B × 0.5 byte  
≈ 35 GB

Real models require additional memory for **scales, metadata, activations, and KV cache**, so these aren't exact total GPU-memory requirements.

But the principle is:

FP16  
 ↓  
\~140 GB

INT8  
 ↓  
\~70 GB

INT4  
 ↓  
\~35 GB

That's a **huge deal for LLM inference**.

## **Why does quantization make inference faster?**

There are two major reasons.

### **1\. Less data to move**

Suppose your model weights are in HBM.

FP16  
2 bytes/value  
     ↓  
More HBM bandwidth required

versus:

INT8  
1 byte/value  
     ↓  
Less data moved

This can be especially beneficial when inference is **memory-bandwidth bound**.

### **2\. Specialized hardware**

Modern GPUs have hardware optimized for low-precision operations.

For example:

FP16/BF16  
   ↓  
Tensor Cores

INT8  
   ↓  
Tensor Cores / specialized integer operations

INT4  
   ↓  
Supported low-precision hardware

So you can potentially get both:

**smaller model \+ faster computation**

---

# **But there's a trade-off**

Quantization introduces **loss of numerical precision**.

Think of:

Original:

0.73125  
0.48291  
0.19273  
0.83742

Quantized:

0.73  
0.48  
0.19  
0.84

The values are slightly different.

If you quantize aggressively:

FP16  
 ↓  
INT8  
 ↓  
INT4

you generally increase the risk of accuracy degradation.

Therefore:

More bits  
  ↓  
Higher numerical fidelity  
  ↓  
More memory  
  ↓  
More bandwidth

Fewer bits  
  ↓  
Lower numerical fidelity  
  ↓  
Less memory  
  ↓  
Less bandwidth  
  ↓  
Potentially faster/cheaper inference  
---

# **Quantization vs Precision**

This distinction is important:

**Precision** \= how numbers are represented.

FP32  
FP16  
BF16  
INT8  
INT4

**Quantization** \= the **process of converting** from one representation to a lower-bit representation.

For example:

FP16 model  
   │  
   │ quantization  
   ▼  
INT8 model

So **INT8 itself isn't "quantization."** INT8 is a numerical format that can be used as the result of quantization.

---

## **In LLMs**

A common deployment flow is:

Train  
 ↓  
BF16 / FP16  
 ↓  
Finished model  
 ↓  
Quantization  
 ↓  
INT8 / INT4  
 ↓  
Deploy  
 ↓  
Lower GPU memory requirement  
 ↓  
Potentially higher inference throughput

This is why you'll hear terms such as **"4-bit quantized LLM"**, **"8-bit quantization"**, **GPTQ**, **AWQ**, and **bitsandbytes** when you're studying LLM inference.

### **One sentence to remember**

> **Quantization is the process of reducing the number of bits used to represent a model's values, mainly to reduce memory usage and bandwidth requirements and potentially increase inference speed, while trying to minimize accuracy loss.**

Quantization makes a trained/ready model smaller and more memory-efficient by using fewer bits to represent its numbers. This can make inference faster and cheaper, especially when the workload is memory-bandwidth limited. 

Trained LLM  
   │  
   │ FP16  
   │ \~140 GB  
   ▼  
Quantization  
   │  
   │ INT8  
   │ \~70 GB  
   ▼  
Smaller model  
   │  
   ├── Less GPU memory  
   ├── Less memory bandwidth  
   └── Potentially faster inference  
FP16 → INT4  
140 GB → \~35 GB

And with INT4:

FP16 → INT4  
140 GB → \~35 GB

Those are approximate **weight-storage** numbers, not total inference memory.

## **Tools used for quantization**

There are several important tools/frameworks you'll encounter in LLMOps:

| Tool / Framework | Common formats | Main use |
| ----- | ----- | ----- |
| **bitsandbytes** | INT8, 4-bit | Easy LLM quantization with Hugging Face |
| **GPTQ** | INT4, INT8 | Post-training quantization for LLM inference |
| **AWQ** | INT4 | Efficient LLM inference |
| **GGUF / llama.cpp** | Various low-bit formats | Local/CPU/GPU LLM inference |
| **TensorRT-LLM** | FP8, INT8, INT4, etc. | NVIDIA production inference |
| **AutoGPTQ** | GPTQ | LLM quantization/inference |
| **Optimum / Intel Neural Compressor** | INT8 and others | Hardware-specific optimization |
| **ONNX Runtime** | INT8, FP16, etc. | Model optimization and inference |
| **torchao** | Various | PyTorch-native quantization/optimization |

**1\. bitsandbytes**

Very easy starting point.

Hugging Face model  
      ↓  
bitsandbytes  
      ↓  
4-bit / 8-bit model  
      ↓  
Inference

**2\. AWQ**

Very important for **LLM inference**, particularly when you're looking at optimized serving.

**3\. GPTQ**

Another major **post-training quantization** approach.

**4\. TensorRT-LLM**

This is particularly important from an **AI infrastructure/GPU engineering** perspective because it goes beyond just quantization. It provides NVIDIA-optimized inference capabilities.

                TensorRT-LLM  
                     │  
       ┌─────────────┼─────────────┐  
       │             │             │  
  Quantization    Kernels       Serving  
       │             │             │  
   FP8/INT8/      Optimized     High-throughput  
    INT4           GPU ops       inference

### **One important distinction**

There are actually **two broad approaches** you'll encounter:

**Post-training quantization (PTQ)**

Train model  
   ↓  
FP16/BF16 model  
   ↓  
Quantize  
   ↓  
INT8/INT4  
   ↓  
Deploy

No retraining or only limited calibration/fine-tuning.

**Quantization-aware training (QAT)**

Training  
  ↓  
Simulate quantization during training  
  ↓  
Model learns to tolerate lower precision  
  ↓  
Quantized model

QAT can preserve accuracy better in some cases, but it is more involved.

So when you hear **"4-bit quantized Llama model"**, you're usually talking about a **trained model that has subsequently been quantized for more efficient inference**. 

# **vLLM, PagedAttention, and Continuous Batching — Modern LLM Serving**

TensorRT-LLM and GGUF/llama.cpp were already covered above as inference tools. **vLLM** is the other major piece of this puzzle — the dominant open-source LLM inference server — and it's worth understanding *why* it exists, because the problem it solves is a direct consequence of the KV cache math above.

## **1. The problem with naive/static batching**

Group several requests into one batch and run them together — but a batch can't return until its **longest** sequence finishes:

Batch of 4 requests, static batching:  
Request A: ▓▓▓▓░░░░░░░░  (finishes early, but GPU slot sits idle/padded)  
Request B: ▓▓▓▓▓▓▓▓▓▓▓▓  (the long one — batch waits for this)  
Request C: ▓▓▓▓▓▓░░░░░░  (finishes early, slot wasted)  
Request D: ▓▓▓▓▓▓▓▓░░░░  (finishes early, slot wasted)

Every `░` above is a GPU compute slot spent on padding, not real work — wasted Tensor Core cycles.

## **2. Continuous (in-flight) batching**

Instead of batching at the *request* level, schedule at the **iteration** level: the instant any sequence finishes, a new request slots into that freed spot immediately, without waiting for the rest of the batch.

Static batching:      [ A B C D ] ── wait for D ──▶ [ E F G H ] ── wait ──▶ ...

Continuous batching:  [ A B C D ] ▶ C done, insert E ▶ A done, insert F ▶ ...
                       (the batch composition changes every single step)

This is what vLLM implements, and what NVIDIA calls **in-flight batching** in TensorRT-LLM — same core idea, different vendor's name for it. The throughput gain is large: vLLM's original paper reports **up to \~24× higher throughput than naive Hugging Face `generate()`** serving, and a **2–4× improvement over prior state-of-the-art orchestration systems** at the time, almost entirely from eliminating this padding waste.

## **3. PagedAttention — fixing KV-cache fragmentation**

Naive KV-cache allocation pre-reserves one large **contiguous** block per sequence sized for the maximum possible length, even though most sequences finish far shorter — the GPU-memory equivalent of internal fragmentation.

**PagedAttention** borrows the idea straight from OS virtual memory: split the KV cache into small fixed-size **pages** (blocks), and give each sequence only as many pages as it actually needs, tracked via a per-sequence **block table** — pages don't even need to be contiguous in physical HBM.

Naive KV cache (per sequence):        PagedAttention (per sequence):  
┌─────────────────────────────┐       ┌───┐  ┌───┐  ┌───┐  
│ reserved for max length      │       │pg0│  │pg3│  │pg7│  ← scattered physical pages,  
│ ███████░░░░░░░░░░░░░░░░░░░░░│       └───┘  └───┘  └───┘     indexed by a block table
│ (used)     (wasted, reserved)│
└─────────────────────────────┘

Because no memory is reserved speculatively, far more concurrent sequences fit in the same HBM — which is what actually lets a server sustain high concurrency under the KV-cache math from the section above, rather than running out of memory after a handful of long-context users.

> **Continuous batching fixes wasted *compute*; PagedAttention fixes wasted *memory*.** Together they're why vLLM (and TensorRT-LLM's equivalent techniques) became the default way to serve LLMs in production rather than a plain `model.generate()` loop.

# **AI Workloads on GPUs**

Different AI tasks place different demands on GPU resources:

### **Training**

Large-scale matrix multiplications requiring dense compute and high memory bandwidth. Often distributed across multiple GPUs.

### **Inference**

Lower computational demands but higher sensitivity to latency. Often requires optimization for throughput per watt.

### **GPU Selection**

Depends on model size, batch size, and workload characteristics. Infrastructure engineers must match hardware to specific use cases.

GPUs accelerate diverse AI domains including computer vision, NLP, speech recognition, reinforcement learning, and large language models.

# **Key Takeaways**

### **Main Points**

* GPUs are fundamentally designed for **parallelism and matrix operations**, making them ideal for AI workloads.  
* **SMs, Tensor Cores, and memory hierarchy** form the backbone of AI acceleration.  
* **HBM and interconnects like NVLink** enable scaling beyond single-GPU limits.  
* **Precision formats** allow engineers to balance accuracy and computational efficiency.

### **Next Steps**

Mastering GPU architecture is essential for optimizing AI infrastructure. Consider:

* **Profiling your workloads** to identify bottlenecks  
* **Experimenting with precision formats**  
* **Optimizing memory access patterns**  
* **Exploring model parallelism** for large model

## **NVIDIA L4 — key specifications**

The L4 is based on the **NVIDIA Ada Lovelace architecture** and is primarily a **low-power, low-profile data-center GPU**, particularly attractive for inference, video AI, and general AI workloads.

| Specification | NVIDIA L4 |
| ----- | ----- |
| **Architecture** | Ada Lovelace |
| **CUDA Cores** | **7,424** |
| **Tensor Cores** | **240** |
| **Tensor Core generation** | 4th generation |
| **GPU Memory** | **24 GB GDDR6 ECC** |
| **Memory bandwidth** | **300 GB/s** |
| **FP32 CUDA Core performance** | **30.3 TFLOPS** |
| **TF32 Tensor Core** | **120 TFLOPS**\* |
| **FP16 Tensor Core** | **242 TFLOPS**\* |
| **BF16 Tensor Core** | **242 TFLOPS**\* |
| **FP8 Tensor Core** | **485 TFLOPS**\* |
| **INT8 Tensor Core** | **485 TOPS**\* |
| **INT4 Tensor Core** | **969 TOPS**\* |
| **TDP** | **72 W** |
| **Form factor** | Single-slot, low-profile |
| **Host interface** | PCIe Gen4 x16 |
| **PCIe bandwidth** | 64 GB/s |
| **NVLink** | ❌ No |
| **MIG** | ❌ No |
| **Memory type** | GDDR6 |
| **ECC** | ✅ |
| **Video encode/decode** | 2 NVENC / 4 NVDEC |
| **Typical use** | AI inference, video AI, graphics, virtualization |

## **Beyond the L4 — The Current NVIDIA Data-Center GPU Lineup**

The L4 table above is one point in a much bigger lineup. Knowing where it sits matters for matching hardware to a workload:

| GPU | Architecture | Memory | Bandwidth | BF16 Tensor Core\* | NVLink | TDP | Typical role |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **T4** | Turing | 16 GB GDDR6 | 320 GB/s | \~65 TFLOPS | ❌ No | 70 W | Light inference, dev/test |
| **L4** | Ada Lovelace | 24 GB GDDR6 | 300 GB/s | 242 TFLOPS | ❌ No | 72 W | Inference, video AI, small-model training |
| **A100** | Ampere | 40/80 GB HBM2e | \~2 TB/s | 312 TFLOPS | ✅ 600 GB/s (NVLink 3\) | 300–400 W | The training workhorse of 2020–2023 |
| **H100** | Hopper | 80 GB HBM3 | 3.35 TB/s | 989 TFLOPS | ✅ 900 GB/s (NVLink 4\) | 700 W (SXM) | Large-model training, high-throughput inference |
| **H200** | Hopper (refresh) | 141 GB HBM3e | 4.8 TB/s | 989 TFLOPS (same compute as H100\) | ✅ 900 GB/s (NVLink 4\) | 700 W | Same H100 compute, memory-capacity-bound workloads (long context, large KV cache) |
| **B200** | Blackwell | 192 GB HBM3e | \~8 TB/s | \~2,250 TFLOPS (vendor-quoted, often includes sparsity) | ✅ 1.8 TB/s (NVLink 5\) | \~1,000 W | Frontier-scale training and inference |

\*Vendor-quoted peak figures — real achieved throughput depends on measured MFU (see below), and some headline numbers assume structured sparsity. Verify dense-only figures before using these for capacity planning.

**The pattern worth noticing:** H100 → H200 is *not* a compute upgrade at all — identical 989 TFLOPS — it's purely a memory-capacity-and-bandwidth upgrade, aimed squarely at the KV-cache and long-context problems described earlier in this doc. Not every GPU generation improves the same ceiling.

### **AMD's Answer: Instinct MI300X and ROCm**

Every precision table in this doc has an "AMD equivalent" column — here's what actually fills it:

* **Instinct MI300X** (CDNA 3 architecture) is AMD's H100/H200-class competitor: 192 GB HBM3, \~5.3 TB/s bandwidth — more raw memory capacity than even an H200, which is AMD's main pitch for large-KV-cache LLM serving.  
* **Matrix Cores** are AMD's Tensor Core equivalent — dedicated matrix-multiply hardware, same purpose as NVIDIA's, different brand name.  
* **ROCm** is AMD's CUDA-equivalent software stack. **HIP** (Heterogeneous-compute Interface for Portability) is largely CUDA-source-compatible via a translation layer (`hipify`), and ROCm ships its own library equivalents: **rocBLAS** (↔ cuBLAS), **MIOpen** (↔ cuDNN), **RCCL** (↔ NCCL).  
* **The honest gap:** CUDA has roughly a 15-year head start in library maturity, framework support, and community tooling. ROCm has closed much of that gap for mainstream PyTorch workloads, but "does this specific kernel/library have a mature ROCm path" is still a real question to check before committing infrastructure — it usually isn't a question with CUDA.

## **From GPU Specs to What You Actually Rent**

Nobody buys a bare chip — infrastructure engineers rent an instance. Mapping specs to cloud instance families:

| GPU | AWS | GCP | Azure | Notes |
| ----- | ----- | ----- | ----- | ----- |
| T4 | `g4dn.xlarge` | N1 \+ T4 | `NCasT4_v3` | Cheapest inference tier |
| L4 | `g6.xlarge` | `g2-standard-*` | `NVadsA10_v5`-adjacent | This project's own AWS runbook uses `g6.xlarge` |
| A10G | `g5.xlarge` | — | — | Common mid-tier training/inference GPU |
| A100 | `p4d.24xlarge` (8×40GB) / `p4de` (8×80GB) | `a2-*` (A2 family) | `NC A100 v4`-series | Multi-GPU by default — these are 8-GPU nodes |
| H100 | `p5.48xlarge` (8×80GB) | `a3-*` (A3 family) | `ND H100 v5`-series | Full NVLink/NVSwitch domain per node |

> Cloud instance names and pricing change often — treat this as a mental map of **which family name corresponds to which GPU**, not a live pricing reference. Always re-check current specs/pricing before provisioning.

## **Model FLOPS Utilization (MFU) — Why Your GPU Never Hits Its Spec Sheet**

`nvidia-smi`'s **GPU-Util%** is one of the most commonly misread numbers in AI infrastructure. It does **not** mean "how efficiently is this workload using the GPU's math throughput." It only means *"was at least one kernel running during this sample window"* — a GPU can read 100% util while doing almost no useful work per cycle (small batch, memory-bound kernel, poor fusion).

The metric that actually answers the efficiency question:

> **MFU \= Achieved FLOPs/sec ÷ GPU's theoretical peak FLOPs/sec (for the precision in use)**

Well-known reference points from published training runs give a sense of scale: Google's **PaLM** paper reported **\~46.2% MFU** on TPU v4; **Megatron-LM**-style training has reported **up to \~52% MFU** on A100 clusters for GPT-3-scale models. These are considered *good* results — not failures.

| MFU range | What it usually means |
| ----- | ----- |
| 60–100% | Exceptional — typically only pure synthetic matmul benchmarks reach this |
| 40–55% | Well-optimized real LLM training (PaLM/Megatron-LM-class references) |
| 15–35% | Typical unoptimized or naive training loop |
| \<15% | Likely memory-bound, batch too small, or poor kernel fusion — profile before scaling to more GPUs |

Tying this doc together: **the roofline model explains *why* MFU tops out where it does** (a memory-bound workload can never reach high MFU no matter how many GPUs you add), and the fixes are the same ones already covered above — larger batch size, mixed precision, ZeRO/FSDP-appropriate sharding, and profiling with the tools in the Benchmarking section later in this doc.

## **Why CUDA for AI?**

**CUDA (Compute Unified Device Architecture)** is NVIDIA's parallel computing platform that:

* Unlocks the **full power of GPUs** for parallel programming  
* Provides a framework for writing **GPU-accelerated code** in C/C++/Python  
* Forms the **backbone of modern AI frameworks** (PyTorch, TensorFlow)

As AI infrastructure engineers, understanding CUDA foundations is essential for optimizing AI workloads.

### **CPU (Host)**

* Few powerful cores (4–64)  
* Optimized for sequential tasks  
* Complex control logic  
* High clock speeds

### **GPU (Device)**

* Thousands of lightweight cores  
* Designed for parallel tasks  
* Simpler control logic  
* Massive throughput

### **CUDA**

CUDA bridges the **host and device**, allowing the CPU to launch **kernels** on the GPU. This architecture is perfectly suited for **matrix/tensor operations** that dominate AI workloads.

## **CUDA Programming Model**

CUDA's execution hierarchy enables massive **Single Instruction, Multiple Data (SIMD)** parallelism:

### **1\. Threads**

Smallest unit of execution.

### **2\. Blocks**

Groups of threads that share resources.

### **3\. Grids**

Collections of blocks that execute a kernel.

When a kernel is launched, it executes across a **grid of thread blocks**, with each thread running the same code but on different data elements.

## **1\. Thread \= one worker**

A **thread** is the smallest execution unit.

Imagine you have 1 million numbers and want to add 10 to every number:

Input:

\[5, 8, 2, 9, 4, ...\]

Thread 0 → 5 \+ 10

Thread 1 → 8 \+ 10

Thread 2 → 2 \+ 10

Thread 3 → 9 \+ 10

...

Each thread works on a different piece of data but executes essentially the **same program/code**.

## **2\. Block \= group of workers**

CUDA doesn't organize millions of threads individually.

It groups threads into **blocks**.

Block 0

├── Thread 0

├── Thread 1

├── Thread 2

├── ...

└── Thread 255

Block 1

├── Thread 256

├── Thread 257

├── ...

└── Thread 511

Threads within the same block can:

* Share **shared memory**  
* Synchronize with each other  
* Cooperate on a computation

This is important because threads in different blocks are designed to be relatively independent.

## **3\. Grid \= collection of blocks**

When you launch a CUDA **kernel**, you tell CUDA how many blocks and threads you want.

For example:

Grid  
│  
├── Block 0 → 256 threads  
├── Block 1 → 256 threads  
├── Block 2 → 256 threads  
├── Block 3 → 256 threads  
└── ...

The entire collection is called a **grid**.

So the hierarchy is:

GPU Kernel  
   │  
  Grid  
   │  
   ├── Block  
   │     ├── Thread  
   │     ├── Thread  
   │     └── Thread  
   │  
   ├── Block  
   │     ├── Thread  
   │     ├── Thread  
   │     └── Thread  
   │  
   └── Block  
         ├── Thread  
         ├── Thread  
         └── Thread

### **The easiest thing to memorize**

> **Grid → Blocks → Threads**

# **4\. What is a Kernel?**

A **kernel** is basically a function/program that you tell the GPU to execute.

For example:

CPU  
│  
│ launch kernel  
▼  
GPU  
│  
├── Block 0  
│    ├── Thread 0  
│    ├── Thread 1  
│    └── ...  
│  
├── Block 1  
│    ├── Thread 0  
│    ├── Thread 1  
│    └── ...  
│  
└── Block 2  
     └── ...

The CPU says:

> "GPU, execute this function across all these data elements."

> ## **A Simple CUDA Kernel**

> \_\_global\_\_ void add(int\* a, int\* b, int\* c) {

>    int i \= threadIdx.x;

>    c\[i\] \= a\[i\] \+ b\[i\];

> }

> ### **Key Components:**

* `__global__` — Specifies the function runs on the **GPU**, callable from the **CPU**  
* `threadIdx.x` — Retrieves the **unique thread ID**  
* Each thread computes **one element** of the result

> ---

## **Vector Addition Pattern:**

This classic example demonstrates the **one-to-one mapping** between threads and data elements that makes CUDA efficient for **data-parallel operations**.

### **Execution Flow**

**Thread Index**  
 `threadIdx.x` selects element index

↓

**Load Inputs**  
 Each thread reads `a[i]` and `b[i]`

↓

**Compute Sum**  
 Perform `c[i] = a[i] + b[i]`

↓

**Write Result**  
 Store sum into `c[i]` in parallel

### **Central concept**

**CUDA Vector Add**

Each GPU thread handles **one element**.

**Launching a CUDA Kernel**

int N \= 256;

add\<\<\<1, N\>\>\>(a, b, c);

### **Execution Configuration:**

The `<<<>>>` syntax defines how the kernel is executed:

* Here: **1 block × 256 threads**  
* Each thread computes one element `c[i]`  
* For larger datasets: use more blocks  
* Can extend to 2D/3D grids for images/tensors

> **CUDA allows up to 1024 threads per block (device-dependent) and millions of blocks in a grid, enabling massive parallelism for AI workloads.**

CPU

 │

 │  1\. Prepare data

 │  2\. Call kernel

 │  3\. Specify grid/block size

 ▼

CUDA Runtime / Driver

 │

 │  submits kernel launch to GPU

 ▼

GPU

 │

 ├── Block 0 → Threads 0..255

 ├── Block 1 → Threads 0..255

 ├── Block 2 → Threads 0..255

 └── ...

For your example:

add\<\<\<1, 256\>\>\>(a, b, c);

### **What actually happens?**

The **CPU is running this line**.

When it reaches:

add\<\<\<1, 256\>\>\>(a, b, c);

the CUDA runtime/driver interprets it roughly as:

> "GPU, execute the `add` kernel using **1 block containing 256 threads**, and use `a`, `b`, and `c` as the arguments."

The CPU doesn't execute `add()` itself. It **launches/submits the GPU work**.

The GPU then schedules those 256 threads on its hardware.

### **Important distinction**

`<<<1, 256>>>` is essentially the **execution configuration**:

\<\<\< number\_of\_blocks, threads\_per\_block \>\>\>

So:

add\<\<\<1, 256\>\>\>(a, b, c);

means:

CPU

↓

Launch "add" kernel

↓

GPU

↓

Create 1 block

↓

Create 256 threads in that block

↓

Execute add() across those threads

And the CPU can continue doing other work while the GPU is executing because a kernel launch is generally **asynchronous**.

For example, if you later do:

add\<\<\<1, 256\>\>\>(a, b, c);

printf("CPU is doing something else");

the CPU doesn't necessarily wait for the GPU kernel to finish before executing the `printf`.

If it needs the GPU result, it can explicitly synchronize, e.g.:

cudaDeviceSynchronize();

So the key concept is:

> **CPU doesn't directly control individual GPU threads. It submits a kernel \+ execution configuration to the CUDA runtime/driver, and the GPU hardware schedules the resulting blocks/threads.**

# **CUDA Memory Hierarchy**

### **Registers**

* Fastest access (\~1 cycle)  
* Per-thread storage

### **Shared Memory**

* Fast access (\~30 cycles)  
* Shared within thread block

### **L1/L2 Cache**

* Medium access (\~300 cycles)  
* Automatic caching

### **Global Memory**

* High latency (\~600 cycles)  
* Accessible by all threads

**Memory optimization is the key to CUDA performance.**

> Specialized memory types like texture and constant memory provide additional optimization opportunities for specific access patterns.

# **CUDA in AI Frameworks**

Modern AI frameworks abstract away CUDA complexity:

import torch  
x \= torch.randn(1000, 1000\)  
x \= x.cuda()  \# Move tensor to GPU  
y \= torch.matmul(x, x)  \# Run on GPU

Under the hood, this activates highly optimized CUDA kernels from libraries like:

* **cuBLAS** — Linear algebra operations  
* **cuDNN** — Deep neural network primitives  
* **NCCL** — Multi-GPU communication

CUDA is the **hidden engine powering deep learning**, handling the complex parallelization needed for efficient AI computation.

# **Parallelism in AI Workloads**

### **Neural Network Training**

Parallel matrix multiplications across thousands of cores

### **CNNs**

Convolutions distributed across thread blocks

### **Transformers**

Parallel attention calculations and tensor operations

Modern GPUs handle **billions of floating-point operations per second**, making previously intractable AI models feasible. CUDA's parallelism model maps perfectly to these workloads, enabling efficient scaling from small models to massive ones.

### **Chart**

* **MatMul:** 30  
* **Conv2D:** 25  
* **Attention:** 20

# **Best Practices for CUDA Programming**

### **Maximize Thread Occupancy**

Keep Streaming Multiprocessors (SMs) busy with sufficient active threads to hide memory latency.

### **Optimize Memory Access**

Minimize global memory operations. Use shared memory for data reuse. Ensure coalesced memory access patterns.

### **Profile Continuously**

Use NVIDIA tools like **nvprof, Nsight Systems, and Nsight Compute** to identify bottlenecks.

### **Avoid Thread Divergence**

Minimize conditional branches that cause threads in a warp to take different paths.

> Always check for race conditions when multiple threads access shared data\!

# **Key Takeaways**

* CUDA provides the **foundation for GPU programming in AI**  
* Threads, blocks, and grids form the CUDA execution model  
* Memory hierarchy optimization is critical for performance  
* AI frameworks abstract CUDA but rely on it heavily  
* Mastering CUDA unlocks custom AI infrastructure optimization opportunities

For AI infrastructure engineers, CUDA knowledge bridges the gap between theoretical understanding and practical implementation of efficient AI systems.

# GPU Memory Hierarchy: Optimizing Usage

**Goal:** Keep data as close to the GPU compute units as possible to reduce latency and maximize GPU utilization.

**Hierarchy:**

 **Registers → Shared/L1 → L2 → VRAM/HBM → CPU RAM → Storage**

* **Higher up:** faster, smaller, more expensive.  
* **Lower down:** slower, larger, cheaper.  
* **Registers/shared memory:** critical for fast kernel execution.  
* **VRAM/HBM:** holds model weights, activations, gradients, etc.  
* **CPU RAM/storage:** mainly for staging, offloading, and datasets.

**Key principle:**

> **Minimize data movement and keep the GPU fed with data.**

Also distinguish **capacity** (how much fits) from **bandwidth** (how quickly it can be accessed).

### **Why Memory Matters in AI**

While GPU compute power continues to increase, **memory bandwidth and access patterns** often create critical bottlenecks in AI workloads.

**AI training involves massive matrix & tensor operations** that require efficient data movement.

**Poor memory usage leads to idle GPU cores and wasted resources.**

**Effective memory optimization can dramatically improve training throughput and cost efficiency.**

### **The GPU Memory Hierarchy**

Modern GPUs feature a complex memory architecture with distinct performance characteristics and use cases.

**Registers**

* Fastest access (1 cycle)  
* Thread-local variables  
* Very limited capacity

**Shared Memory**

* Fast on-chip access  
* Shared across thread block  
* Explicitly managed

**L1/L2 Cache**

* Automatic buffering  
* L1: per-SM, L2: global  
* Not directly controlled

**Global Memory**

* High latency (100s of cycles)  
* High capacity (GBs)  
* Bandwidth-constrained

> Performance optimization requires understanding these layers and their interaction.

# Registers: The First Line of Speed

Registers provide the fastest possible memory access with just **1 cycle latency**, making them critical for performance-sensitive operations.

* Allocated per CUDA thread for local variables  
* Managed automatically by the CUDA compiler  
* Limited resource — typically **255 max per thread** on modern GPUs  
* **Register spilling** occurs when demand exceeds availability, forcing variables into slower memory

Monitoring register pressure and optimizing kernel design can significantly improve throughput for compute-bound operations.

**Side note:** Each SM has thousands of registers that are allocated to active threads.

### **Shared Memory: Collaborative Performance**

**Key Characteristics**

* On-chip memory with access speeds similar to L1 cache (**10–20× faster than global memory**)  
* Shared across all threads within the same thread block  
* Modern GPUs: **48–164 KB per SM**, configurable with L1 cache

**Optimal Use Cases**

* Matrix multiplication tiles that are reused by multiple threads  
* Convolution operations with overlapping input regions  
* Reduction operations requiring inter-thread communication

**Implementation Strategy**

* Explicitly declared and managed in CUDA kernels  
* Requires careful synchronization between threads  
* Can reduce global memory bandwidth requirements by **5–10×**

### **Cache Hierarchy: Automatic Performance Buffers**

#### **L1 Cache**

* Per-SM, typically \~128KB (shared with shared memory)  
* Automatically caches local access patterns  
* Managed by hardware, not directly programmable  
* Delivers \~4× better latency than L2

#### **L2 Cache**

* Shared across all SMs, 3–6MB on modern GPUs  
* Acts as buffer between SMs and global memory  
* Critical for workloads with data reuse across SMs  
* Cache-friendly access patterns improve hit rates

> Unlike CPUs, GPU caches focus more on **bandwidth** than latency hiding. They work best with structured, predictable memory access patterns typical in tensor operations.

# Global Memory: The Capacity Layer

**1\. Characteristics**

* Largest capacity memory (10–80GB on modern GPUs)  
* Highest latency (400–800 cycles)  
* Accessible by all threads across all SMs

**2\. Performance Numbers**

* NVIDIA H100: **3 TB/s** with HBM3  
* A100: **1.5–2 TB/s** with HBM2e  
* RTX 4090: **\~1 TB/s** with GDDR6X

**3\. Optimization Focus**

* Bandwidth utilization is critical  
* Coalesced access patterns essential  
* Minimize unnecessary transfers

> Global memory bandwidth often becomes the primary bottleneck in large-scale AI training. **Memory–compute balance (bytes accessed per FLOP)** determines whether your workload is **memory-bound or compute-bound**.

### **Memory Optimization Techniques**

**1\. Coalesced Access**

* Structure memory access so threads in a warp read **contiguous memory addresses**.

**2\. Shared Memory Tiling**

* Load data blocks once into shared memory, then reuse across multiple threads.

**3\. Mixed Precision**

* Use **FP16/BF16** to halve memory footprint and potentially double effective bandwidth.

**4\. Gradient Checkpointing**

* Trade computation for memory by recomputing activations during backpropagation.

**Bottom note:**  
 Memory pinning and zero-copy techniques can also reduce PCIe transfer overhead for CPU–GPU data movement.

### **Memory Bottlenecks in AI Training**

Modern AI models face several critical memory challenges that limit scaling efficiency:

* **Model \> GPU RAM**  
* **Limited Batch Size**  
* **PCIe Transfer Bottleneck**  
* **Inefficient Memory Tiling**  
* **GPU Memory Fragmentation**

### **Reality Check**

For many large language models, **memory constraints are more limiting than computational power**.

A **65B-parameter model** requires at least **130 GB** just for parameters in **FP16**, exceeding the capacity of even the latest H100s.

### **Tools for Memory Profiling**

#### **Basic Monitoring**

* `nvidia-smi` — Real-time system-level memory usage  
* `torch.cuda.memory_allocated()` — PyTorch runtime allocation  
* `tf.config.experimental.get_memory_info()` — TensorFlow memory tracking

#### **Advanced Profiling**

* **NVIDIA Nsight Systems** — Timeline visualization of memory operations  
* **NVIDIA Nsight Compute** — Kernel-level memory metrics  
* **PyTorch Profiler** — Operation-specific memory allocation tracking

> **Memory profiling should be the first step** in any optimization effort, identifying exactly where your workload spends its memory budget.

### 

### **Key Takeaways**

#### **Understand the Hierarchy**

GPU memory spans from **ultrafast registers** to **high-capacity global memory**.

#### **Optimize Access Patterns**

**Coalescing and tiling** can deliver **5–10× performance improvements**.

#### **Profile First**

Use profiling tools to identify and address your specific bottlenecks.

#### **Memory \> Compute**

Large-scale AI training is increasingly limited by **memory constraints, not compute**.

> “In modern AI infrastructure, the engineers who best understand and optimize for GPU memory hierarchy will deliver the most cost-effective training systems.”

# Multi-GPU Scaling and Interconnects (NVLink)

An essential guide for ML engineers and infrastructure architects building advanced **multi-GPU training systems for large-scale AI workloads**.

### **Why Multi-GPU Scaling?**

Modern AI development faces fundamental constraints that single-GPU solutions simply cannot overcome:

#### **Breaking Physical Limits**

Single GPU memory and compute ceilings constrain **model size and training capability**.

#### **Enabling Scale**

Large AI models (**LLMs, computer vision, reinforcement learning**) demand **distributed computation**.

#### **Accelerating Development**

Multi-GPU configurations deliver **faster training cycles** and support **larger batch sizes**.

> **Multi-GPU systems are the foundation of trillion-parameter model training.**

# Data Parallelism: The Foundation of Multi-GPU Training

#### **Core Principles**

* Mini-batches are **split across multiple GPUs**  
* Each GPU has a **complete model copy**  
* Gradients are computed independently on each device  
* Periodic synchronization combines results

> Data parallelism is the most widely implemented technique in **PyTorch and TensorFlow** training pipelines, forming the cornerstone of distributed training.

Performance critically depends on **high-bandwidth GPU-GPU interconnects** for gradient synchronization.

### **Model Parallelism: Beyond Memory Constraints**

#### **1\. Model \> Single GPU Memory**

When parameters exceed available VRAM, the model must be **partitioned**.

#### **2\. Layer Distribution**

Different model components are distributed across **multiple devices**.

#### **3\. Coordinated Execution**

Each GPU handles specific portions of the **forward/backward pass**.

### **Implementation Approaches**

* **Pipeline Parallelism:** GPipe, PipeDream, DeepSpeed  
* **Tensor Parallelism:** Splitting individual layers  
* **Sequence Parallelism:** Distributing sequence dimensions

> Model parallelism introduces significant **communication complexity** and requires careful orchestration of operations.

### **ZeRO and FSDP: Sharding Optimizer States, Gradients, and Parameters**

Plain **data parallelism** (described just above) has a hidden cost: every GPU keeps a **full, redundant copy** of the model's parameters, gradients, and optimizer states. For AdamW in FP32, that's the same 16-bytes/parameter static memory this doc's precision sections already build toward (4 bytes weights \+ 4 bytes gradients \+ 8 bytes Adam's two running-average buffers) — held identically on *every single GPU*, N times over for N GPUs. Past a certain model size, this redundancy — not compute — is what makes the model simply not fit.

**ZeRO (Zero Redundancy Optimizer, from Microsoft DeepSpeed)** removes the redundancy in three increasing stages:

| Stage | What gets sharded across GPUs | Effect |
| ----- | ----- | ----- |
| **ZeRO-1** | Optimizer states only | Optimizer-state memory shrinks by \~4× (roughly N×, capped by state's share of the 16 bytes) |
| **ZeRO-2** | \+ Gradients | Gradient memory also sharded |
| **ZeRO-3** | \+ Parameters themselves | Each GPU permanently holds only 1/N of the actual weights |

**FSDP (Fully Sharded Data Parallel)** is PyTorch's own native implementation of the same idea as ZeRO-3.

Plain data parallelism (per GPU):              ZeRO-3 / FSDP (per GPU):  
┌─────────────────────────────┐                ┌─────────────────────┐  
│ Full Params                  │                │ Params  (1/N shard)  │  
│ Full Gradients                │                │ Grads   (1/N shard)  │  
│ Full Optimizer State          │                │ Opt state (1/N shard)│  
└─────────────────────────────┘                └─────────────────────┘  
        × N GPUs, fully redundant                        ↓  
                                              gathered on-demand, layer by  
                                              layer, during forward/backward,  
                                              then freed again immediately

The trade-off: ZeRO-3/FSDP need to **all-gather** each layer's full parameters right before using them and **reduce-scatter** gradients right after computing them — every layer, every step. That's a lot more network traffic than plain data parallelism's once-per-step gradient sync.

> **This is the real reason NVLink/NVSwitch bandwidth matters so much for large-model training** — not just periodic gradient averaging, but continuous, per-layer parameter gather/scatter traffic. A ZeRO-3/FSDP job on PCIe-only GPUs can spend more time moving shards around than computing on them; this is the concrete workload the "Interconnect Saturation" bottleneck described below is usually about.

### **Interconnect Comparison: PCIe vs NVLink**

#### **PCIe (Peripheral Component Interconnect Express)**

* Industry-standard interconnect for **CPU ↔ GPU communication**  
* Bandwidth ceiling of **\~64 GB/s** (PCIe 5.0 ×16)  
* Higher latency, limited peer-to-peer capabilities  
* Can become a **bottleneck in multi-GPU training workloads**

#### **NVLink (NVIDIA's High-Speed Interconnect)**

* Purpose-built for **GPU-to-GPU communication**  
* Bandwidth up to **900 GB/s** with H100 GPUs  
* \~**14× faster than PCIe** in peak scenarios  
* Dramatically reduces **synchronization overhead**

### **NVLink Architecture**

#### **Direct GPU-to-GPU Communication**

NVLink creates **high-bandwidth, low-latency point-to-point connections** between GPUs, enabling:

* Direct memory access between GPUs (**peer-to-peer**)  
* Elimination of CPU as a communication middleman  
* Significant reduction in data transfer overhead  
* Support for **Unified Memory Addressing (UMA)**

> NVLink's direct connections unlock **near-linear scaling** for communication-intensive workloads like transformer training.

**Bottom note:**  
 Each NVLink connection provides **dedicated bandwidth between GPU pairs**.

### **NVSwitch: The Multi-GPU Fabric**

#### **Extending NVLink's Reach**

* Functions like a **network switch for GPUs**, enabling scaling beyond direct NVLink connections.

#### **All-to-All Communication**

* Enables any GPU to communicate with any other GPU at **full NVLink bandwidth**.

#### **AI Supercomputing**

* Powers **NVIDIA DGX and HGX systems** and forms the backbone of modern AI supercomputers.

> **NVSwitch removes communication bottlenecks in large GPU clusters, allowing hundreds of GPUs to function as a single computational unit.**

### **Multi-GPU Topologies**

**Axes:**

* Vertical: **High Local Bandwidth ↕ Low Local Bandwidth**  
* Horizontal: **Low Interconnect Reach ↔ High Interconnect Reach**

**Examples:**

* **Single-node DGX** — 8 GPUs via NVLink/NVSwitch  
* **Multi-node Cluster** — GPUs across servers via InfiniBand  
* **Hybrid Topology** — NVLink locally \+ RDMA between nodes  
* **Considerations** — latency, bandwidth, and scaling trade-offs

### **Bottom Sections**

**Single Node, Multi-GPU**

* Up to **8× A100/H100 GPUs** in systems like NVIDIA DGX, connected via NVLink/NVSwitch

**Multi-Node Clusters**

* GPUs distributed across multiple servers, connected via high-speed networking (**InfiniBand, RoCE**)

**Optimization Layer**

* **NCCL (NVIDIA Collective Communications Library)** optimizes operations for specific topologies.

> **The topology selection directly impacts training throughput, scalability, and hardware utilization efficiency.**

### **Bottlenecks in Multi-GPU Training**

#### **1\. Communication Overhead**

Gradient synchronization becomes increasingly expensive as GPU count grows, potentially negating computational benefits.

#### **2\. Latency Limitations**

When communication latency exceeds computation speed, GPUs spend time **waiting rather than computing**.

#### **3\. Workload Imbalance**

Uneven distribution of computation across GPUs creates **stragglers** that delay synchronization steps.

#### **4\. Interconnect Saturation**

PCIe-only configurations can severely underutilize GPU computational capacity, creating **bandwidth bottlenecks**.

> Effective multi-GPU scaling requires **high-bandwidth, low-latency interconnects** to minimize these bottlenecks.

### **Chart**

**Multi-GPU GPU Scaling Efficiency**

The chart compares **PCIe, NVLink, and NVSwitch** as GPU count increases. The general trend shown is that scaling efficiency/performance decreases as more GPUs are added, with **NVLink and NVSwitch maintaining better scaling than PCIe**, particularly at larger GPU counts.

### **Best Practices for Multi-GPU Scaling**

* Prioritize **NVLink/NVSwitch-enabled hardware** when budget permits  
* Optimize **batch size** to balance computation and communication  
* Implement **mixed precision (FP16/BF16)** to reduce communication volume  
* Leverage **NCCL** for topology-aware collective operations  
* **Benchmark at small scale** before deploying to hundreds of GPUs

> For large clusters, **gradient accumulation** can help reduce synchronization frequency while maintaining effective batch size.

### **Key Takeaways**

**Necessity of Scale**  
 Multi-GPU configurations are no longer optional for large-scale AI training—they're essential infrastructure.

**Interconnect Hierarchy**  
 PCIe provides baseline connectivity, while NVLink enables high-performance scaling with up to **14× higher bandwidth**.

**Network Fabric**  
 NVSwitch technology extends NVLink capabilities to create GPU superclusters with **full-bandwidth connectivity**.

**System Architecture**  
 The combination of physical topology and communication libraries determines overall training efficiency.

> Understanding GPU interconnect technologies is the foundation of **mastering multi-GPU infrastructure**.

**Next steps:** Evaluate your workloads, benchmark on different configurations, and design your infrastructure to balance **performance and cost**.

### **Multi-Instance GPU (MIG) Configurations**

**Optimizing GPU resource allocation for AI workloads in production environments**

### **Why Multi-Instance GPUs?**

Modern GPUs like NVIDIA's **A100 and H100** deliver immense computational power, but not all AI workloads require the full capacity of these powerful accelerators.

#### **Resource Underutilization**

Running small workloads on full GPUs wastes resources and significantly increases cloud costs.

#### **Multi-Tenant Requirements**

Enterprise environments need to support **multiple users and workloads simultaneously**.

### **What Is MIG?**

**Multi-Instance GPU (MIG)** is a hardware partitioning feature available on NVIDIA's **A100, H100, and L40S GPUs**.

#### **1\. Hardware Partitioning**

Divides a physical GPU into **isolated slices** that function as independent mini-GPUs.

#### **2\. Dedicated Resources**

Each slice has its own **memory and compute resources**, with no sharing or overlap.

#### **3\. Complete Isolation**

Provides **performance predictability** with hardware-enforced boundaries between instances.

> MIG transforms a single powerful GPU into multiple smaller GPUs that can be allocated to different users or workloads independently.

### **Example – A100 MIG Profiles**

**1g.5gb**

* 1 compute slice  
* 5 GB memory  
* \~1/7 of full GPU

**2g.10gb**

* 2 compute slices  
* 10 GB memory  
* \~2/7 of full GPU

**3g.20gb**

* 3 compute slices  
* 20 GB memory  
* \~3/7 of full GPU

**7g.40gb**

* 7 compute slices  
* 40 GB memory  
* Full GPU

The A100 GPU can be configured in multiple ways to meet diverse workload requirements. For example, you could create:

* **7 × 1g.5gb** instances for small inference jobs  
* **3 × 2g.10gb \+ 1 × 1g.5gb** for mixed workloads  
* **2 × 3g.20gb \+ 1 × 1g.5gb** for balanced computing needs

### **Benefits of MIG**

**Cost Efficiency**  
 Share expensive GPU resources across teams, reducing the need for additional hardware purchases.

**Multi-tenancy**  
 Run multiple isolated workloads with guaranteed performance and QoS for each user.

**Higher Utilization**  
 Improve GPU utilization rates from typical **15–30% to 80%+** through appropriate sizing.

**Fault Isolation**  
 Prevent failures in one instance from affecting other workloads on the same physical GPU.

### **MIG Use Cases**

**Inference Microservices**  
 Deploy multiple inference endpoints for chatbots, recommendation engines, and image processing services on a single GPU.

**Small-Scale Training**  
 Enable academic labs and startups to run multiple parallel experiments with limited GPU resources.

**Multi-Tenant GPU Clusters**  
 Create shared infrastructure for data science teams with guaranteed resource isolation.

**AI SaaS Applications**  
 Optimize cost structure for AI-powered software services with varying workload demands.

### **Enabling MIG**

Setting up MIG involves a simple CLI workflow that creates isolated logical GPUs:

\# Enable MIG mode  
sudo nvidia-smi \-mig 1

\# Create GPU instances (example: two 19% slices)  
sudo nvidia-smi mig \-cgi 19,19 \-C

\# List MIG devices  
nvidia-smi \-L

> After enabling MIG mode, the GPU requires a **reboot** to apply the changes. Different MIG profiles can be created to match your specific workload requirements.

Once configured, the MIG instances appear as **separate GPUs** to the operating system and container platforms, enabling fine-grained resource allocation.

### **MIG \+ Kubernetes**

NVIDIA GPU Operator seamlessly integrates MIG with Kubernetes orchestration:

* Kubernetes scheduler views MIG instances as **distinct GPUs**  
* Enables **fine-grained job placement** across GPU resources  
* Supports declarative configuration of MIG profiles via **CRDs**  
* Automates MIG instance lifecycle management  
* Integrates with **resource quotas and namespace isolation**  
* Compatible with **Slurm and other HPC schedulers**

> This integration is critical for building scalable **MLOps pipelines** that efficiently utilize GPU resources across teams.

### **Limitations of MIG**

#### **Limited Hardware Support**

Only available on **Ampere and Hopper architecture GPUs** (A100, H100, L40S).

#### **No NVLink Between Instances**

MIG instances on the same GPU **cannot communicate via high-speed NVLink**.

#### **Not for Large Models**

Unsuitable for large training jobs that require the **full GPU memory and compute capacity**.

### **Additional Considerations**

* Once partitioned, GPU requires reconfiguration to change the MIG profile  
* Potential resource waste if workloads don't fully utilize their allocated slice  
* More complex monitoring and management requirements  
* Limited support in older CUDA applications and frameworks

### **Key Takeaways**

**Resource Optimization**  
 MIG transforms a single GPU into multiple isolated mini-GPUs, dramatically improving **utilization and cost efficiency**.

**Enterprise Ready**  
 Essential for **multi-tenant environments and cloud providers** looking to maximize GPU infrastructure ROI.

**Kubernetes Integration**  
 Works seamlessly with **container orchestration** for scalable, efficient AI infrastructure.

**Next steps:** Evaluate your current GPU utilization patterns and identify workloads that could benefit from MIG to reduce infrastructure costs.

### **Benchmarking AI Workloads on GPUs**

A comprehensive guide for ML engineers and infrastructure teams **evaluating GPU performance for AI workloads**.

### **Why Benchmark GPUs for AI?**

**Performance Varies by Task**  
 Not all GPUs perform equally across different AI workloads — architecture matters for specific operations.

**Informed Decision Making**  
 Benchmarks guide **hardware selection & optimization**, preventing underutilization of costly GPU resources.

**Deployment Strategy**  
 Helps compare **cloud vs on-prem performance** to optimize total cost of ownership (TCO).

**Future Planning**  
 Essential for AI infrastructure planning, scaling roadmaps, and capacity forecasting.

### **Types of GPU Benchmarks**

**Synthetic**  
 Raw FLOPs, memory bandwidth (Geekbench, CUDA samples)

**AI Framework**  
 TensorFlow/PyTorch training speed on standard datasets

**Model-Specific**  
 ResNet, BERT, GPT benchmarks with real architecture

**Inference**  
 Latency & throughput tests under production conditions

> A comprehensive benchmarking strategy combines **all four types** to build a complete performance profile.

### **Key Metrics to Track**

**32T — FLOPs**  
 Floating point operations per second — raw computational power.

**1250 — Throughput**  
 Samples/sec or tokens/sec processed during training or inference.

**15ms — Latency**  
 Response time per inference — critical for real-time applications.

**24GB — Memory**  
 VRAM utilization per batch — often the limiting factor for large models.

**3.5× — Energy Efficiency**  
 Performance/watt ratio — particularly important for LLM training and HPC.

> Effective benchmarking tracks **all metrics across different model sizes and batch configurations**.

### **Benchmarking Tools**

**MLPerf**  
 Industry-standard benchmark suite for **training & inference** with peer-reviewed methodologies.

**NVIDIA Nsight Systems**  
 Low-level profiling at the **kernel level** with detailed execution timeline analysis.

**PyTorch/TensorFlow Profilers**  
 Framework-specific tools for detailed **operation timing and memory tracking**.

**nvidia-smi**  
 Basic but essential tool for **live utilization monitoring and thermal tracking**.

### **Benchmarking Training Workloads**

**1\. Choose Representative Models**  
 **ResNet-50, BERT, GPT-2** provide diverse architecture profiles (CNN, Transformer).

**2\. Measure Key Metrics**  
 **Time per epoch, samples/sec** across different batch sizes and precision formats.

**3\. Test Precision Impact**  
 Compare **FP32 vs FP16/BF16** precision to evaluate Tensor Core utilization.

**4\. Evaluate Scaling**  
 Test **scaling efficiency (1 GPU vs multi-GPU)** to identify communication bottlenecks.

> Effective training benchmarks detect whether your workload is **memory-bound or compute-bound**.

### **Benchmarking Inference Workloads**

#### **Key Inference Metrics**

**1\. Latency per request** — p50, p95, p99 percentiles under various loads

**2\. Throughput (QPS)** — queries per second at maximum sustainable load

**3\. Batch size optimization** — finding optimal response time vs. throughput

#### **Optimization Tools**

* **NVIDIA Triton Inference Server**  
* **TensorRT** for CUDA optimization  
* **ONNX Runtime** for cross-platform deployment  
* **DeepSpeed** for large model inference  
* **Tensor parallelism** for LLMs

> Inference optimization is critical for production deployments where **latency impacts user experience and cost**.

### **GPU Memory Benchmarks**

**Bandwidth Tests**  
 Measure copy speeds: **host ↔ device ↔ device** using CUDA `bandwidthTest`.

**VRAM Capacity**  
 Determine maximum **batch size and model size** before OOM errors.

**Memory Fragmentation**  
 Identify wasted GPU memory space during long-running training jobs.

**Profiling Tools**  
 PyTorch memory profiler, **Nsight Compute** memory analysis.

> **Memory is often the true bottleneck in LLM training and high-resolution computer vision.**

### **Benchmarking Multi-GPU Scaling**

**Linear vs. Actual Scaling**  
 Compare **theoretical linear scaling** vs. real-world performance with communication overhead.

**Communication Fabric**  
 Test **PCIe vs NVLink vs InfiniBand** topologies using **NCCL AllReduce benchmarks**.

**Distributed Training**  
 Benchmark **DDP (DistributedDataParallel)** and model parallelism efficiencies.

> Multi-GPU scaling reveals the true efficiency of your infrastructure at scale and helps identify **communication bottlenecks**.

### **Key Takeaways**

**Strategic Value**  
 Benchmarking ensures **right GPU choice & efficiency** for your specific AI workloads.

**Comprehensive Metrics**  
 Measure **FLOPs, throughput, latency, and memory usage** across diverse scenarios.

**Professional Tools**  
 Leverage **MLPerf, Nsight, and AI framework profilers** for detailed insights.

### **Benchmarking is the science of matching AI workloads to hardware**

Implementing a rigorous benchmarking strategy will:

* Reduce infrastructure costs  
* Improve model training time  
* Optimize inference latency  
* Support informed scaling decisions

