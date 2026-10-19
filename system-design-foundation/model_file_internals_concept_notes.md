# Model File Internals — What's Actually Inside a Checkpoint

One continuous story, in order: what a model's weights really are → what's literally on disk →
how to poke at that file yourself → why that's dangerous if done carelessly → the wider zoo of
formats → how one model can span multiple files → what fine-tuning does to the file → how it
all comes packaged in a real downloaded model folder.

---

## 1. The mental model: numbers under labels, not stored "nodes"

**Layman version:** a trained model is really just **millions of numbers, organized under
labels.** Picture an enormous spreadsheet: each row has a name (`layer1.weight`, `layer1.bias`,
`layer2.weight`, ...) and, under that name, a giant grid of decimal numbers — that grid *is*
what the layer learned. Nothing more mystical than that. There's no code, no "logic," no
instructions in there (normally) — just labeled number-grids, plus some bookkeeping (each
grid's shape and number type).

The instinct that a model is "millions/billions of interconnected nodes, each with a weight" is
the right picture for what a neural net *computes* — but one detail matters: **the nodes
themselves are never saved.** A node (neuron) is just a number flowing through the network
*while it's running* — recomputed fresh every time, on new input, then thrown away. Nothing
about a specific node persists between runs.

What *is* saved is the weights of the connections — and even those aren't stored as billions of
individual little "node A → node B: 0.5" records. They're packed into **one matrix per layer**
that represents *all* the connections between two layers at once. A layer connecting 4096 nodes
to 4096 nodes doesn't store 16.7 million separate connection objects — it stores one
`[4096, 4096]` tensor, and matrix multiplication does "every node talks to every node" in one
shot.

This is also where "7B model" actually comes from: **7 billion = the count of weights
(connections), not neurons.** The actual neuron count in a model is comparatively tiny
(thousands per layer, tens to low-hundreds of layers) — the billions come from how densely
those layers connect to each other, not from billions of separate saved neuron objects.

**One line worth having ready:** *"a checkpoint file is a small number of large matrices, each
one packing millions of connection-weights at once — not a literal list of billions of
individual connections, and not the neurons themselves, which are never saved at all."*

---

## 2. What a checkpoint file actually is, mechanically

A `.pth` (or `.pt`) file holds a **`state_dict`** — a Python dictionary mapping layer names to
**tensors** (PyTorch's name for a multi-dimensional array of numbers). `torch.save(model.state_dict(), "model.pth")`
walks the model, pulls out every layer's weight/bias tensor, and serializes that dictionary to
disk. Since PyTorch 1.6, the file format is literally **a ZIP archive** — one entry holding the
pickled dictionary structure (names, shapes, dtypes), another holding the raw tensor bytes.

**"Weights" isn't guaranteed by the extension — check what's actually inside.** `.pth` just
means "whatever dictionary got handed to `torch.save()`." Most of the time that's weights-only
(`model.state_dict()`), but training code often saves a bigger bundle instead:

```python
torch.save({
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),   # momentum/variance, needed to resume training exactly
    "epoch": epoch,
    "loss": loss,
}, "checkpoint.pth")
```

Still a `.pth` file, but not *just* weights — it's a resumable training checkpoint. Loading it
needs `checkpoint["model_state_dict"]` to reach the weights, not `torch.load()` directly. Quick
way to tell which kind you're holding: `torch.load(path).keys()` — top-level keys like
`state_dict`/`optimizer`/`epoch` mean a full checkpoint; keys that look like layer names
directly (`layer1.weight`, `layer1.bias`, ...) mean weights-only.

---

## 3. Reading, seeing, and modifying it yourself

**Can you read it?** Yes, two ways:

- **The intended way:** `torch.load("model.pth")` in Python gives you back the dictionary.
  `list(state_dict.keys())` shows every layer name; `state_dict["layer1.weight"].shape` shows
  that layer's dimensions.
- **The blunt way, no PyTorch needed:** `unzip model.pth -d out/` — because it's a real ZIP
  file, you can list and extract its contents with any zip tool. You'll see the raw tensor data
  as binary, not readable numbers, but it confirms there's no mystery format underneath.

**Can you see the weights?** Yes — literally. `state_dict["layer1.weight"]` is a tensor; print
it and you see actual floating-point numbers, e.g. `[[0.0231, -0.1187, ...], [...]]`. That grid
of numbers **is** what the model learned — there's no separate "meaning" layer to decode. A
weight of `0.9` next to a weight of `0.0001` really does mean the model learned to weight that
input 9,000x more than the other in that layer's computation.

**Can you modify it?** Yes, and this isn't a hack — it's the normal mechanism behind several
real techniques:

- **Quantization** — rewrite each float32 number as a lower-precision int8/int4 approximation,
  save it back. Smaller file, faster inference, tiny accuracy loss.
- **LoRA merging** (see [`finetuning_concept_notes.md`](finetuning_concept_notes.md)) — load the
  base `state_dict` and the LoRA adapter's small tensors, compute `W_merged = W_base + B @ A`
  per matching key, write the result back out as one merged `state_dict`. That's the entire
  merge step: dictionary lookups and tensor math, no training involved.
- **Pruning** — zero out (or physically remove) weights below some magnitude threshold, save the
  smaller result.
- **Manual "model surgery"** — e.g. resizing an embedding layer when adding vocabulary, or
  swapping in a fine-tuned layer from a different checkpoint. All just dictionary edits.

The general pattern: `state_dict = torch.load(...)`, edit the tensors however you need, then
`torch.save(state_dict, "modified.pth")`.

---

## 4. The safety catch — pickle, and why `.safetensors` exists

`torch.load()`'s default deserializer is Python's **pickle**, and pickle can be made to execute
arbitrary code during loading, not just reconstruct data — a malicious `.pth` file can be
crafted to run attacker code the moment someone calls `torch.load()` on it. Layman version: it's
like a shipping container that's supposed to hold furniture parts, but the pickle format also
lets the container include a hidden robot that starts assembling itself — running code — the
moment you open the box, whether you wanted that or not. This is a real, known attack surface
for "download a checkpoint from the internet and load it," not a theoretical one.

- **Mitigation 1:** `torch.load(path, weights_only=True)` (PyTorch 2.0+) — restricts
  deserialization to plain tensors/dicts, refuses to unpickle arbitrary objects/code.
- **Mitigation 2:** **`.safetensors`** — a newer file format built specifically to hold *only*
  tensor data, no pickle, no code-execution path by construction, and faster to load. Here's the
  actual mechanism: think of it like a shipping manifest plus boxes. A small text header (plain
  JSON) lists every tensor's name, shape, and exactly which byte-range it occupies in the file;
  the raw number bytes follow right after, back to back, with nothing wrapped around them.
  Because the header states exactly where each tensor's bytes start and end, a program can jump
  straight to the bytes it needs and read them directly — **memory-map** the file — instead of
  reconstructing Python objects the way pickle does. That single design choice explains both
  properties at once: no reconstruction step means nothing gets a chance to *execute* (the
  safety), and "jump to byte offset X, read Y bytes" is far cheaper than deserializing a pickle
  stream (the speed). This is why most model hubs now publish both `.bin`/`.pth` and
  `.safetensors`, and why `.safetensors` is the one to prefer when pulling third-party weights.

**Follow-up worth being ready for:** *"How would you inspect an untrusted checkpoint's contents
without risking code execution?"* → Prefer a `.safetensors` version if one exists; otherwise
`torch.load(..., weights_only=True)`, or inspect the ZIP structure/tensor metadata directly
without ever unpickling.

---

## 5. The wider format landscape

**Layman version:** this is like photos coming as `.jpg`, `.png`, `.heic` — different tools save
"the model's learned numbers" under different extensions, and the extension alone doesn't tell
you what's safe to load or what's actually packed inside. What matters is the format
underneath, not the three letters after the dot.

| Extension | Framework / origin | What's actually inside | Pickle-based (code-exec risk)? |
|---|---|---|---|
| `.pth` / `.pt` | PyTorch | `state_dict`, or a full checkpoint bundle (§2) | Yes |
| `.bin` | PyTorch (HuggingFace's older convention, `pytorch_model.bin`) | Same format as `.pth` in practice — just a different extension by convention | Yes |
| `.safetensors` | Framework-agnostic (HF-driven standard) | Tensors *only*, no arbitrary objects (§4) | **No** — built specifically to remove this risk |
| `.ckpt` | PyTorch Lightning, TensorFlow, Stable Diffusion models | Usually a full bundle — weights + optimizer + epoch + hyperparams, like §2's checkpoint example | Usually yes (still pickle underneath in the PyTorch cases) |
| `.h5` / `.hdf5` | Keras / TensorFlow | A tree-structured file (groups/datasets), not a flat dict — different serialization mechanism entirely, not pickle | No |
| `.onnx` | ONNX (cross-framework exchange format) | Not just weights — the full **computation graph** (architecture + weights), so a model trained in PyTorch can run in a different runtime (ONNX Runtime, TensorRT) without the original code | No |
| `.gguf` | llama.cpp / Ollama | Quantized LLM weights, self-describing (bundles architecture metadata in the same file so nothing extra is needed to run it) | No |
| `.msgpack` | Flax / JAX | JAX's native parameter serialization (a "pytree" structure) — same role as PyTorch's `state_dict` | No |

**The mental model that ties the table together:** every format is a tradeoff along the same
few axes — (1) does the file hold just weights, or the architecture too, (2) is it tied to one
framework or portable across runtimes, (3) is it pickle-based (flexible, but a real
code-execution risk on untrusted files) or a restricted tensor-only format (safe, and usually
faster to load since it can be memory-mapped instead of deserialized). `.safetensors` and
`.gguf` both exist specifically because `.pth`/`.bin`/`.ckpt`'s pickle flexibility turned out to
be a liability, not a feature, once people started downloading checkpoints from strangers on the
internet.

---

## 6. Splitting a model across multiple files — does it still work as one system

Yes — this is the normal way very large models are stored and run, not an edge case. **Layman
version:** two different things get called "splitting," and they're as different as cutting a
finished puzzle into pieces for shipping (still one complete picture once reassembled) versus
having two painters paint different halves of the *same* canvas at the *same* time, constantly
coordinating brush strokes so the middle lines up.

### 6a. Splitting for storage/transfer — still one logical model, just packaged differently

A checkpoint is just a dictionary (`layer name → tensor`). Nothing stops writing half the keys
to one file and half to another, as long as something records which key went where. This is
exactly what large-model hosting does:

```
model-00001-of-00005.safetensors
model-00002-of-00005.safetensors
...
model.safetensors.index.json      ← the manifest: {"layer1.weight": "model-00001...", ...}
```

Loading reads the index, opens each shard, reassembles the *same single dictionary* it would've
been in one file — the split is undone before any computation happens. Reasons to split this
way: file-size limits on hosting, faster parallel downloads, loading one shard without pulling
the ones not needed yet. **Still logically one model** — pure packaging. (This is the puzzle
cut into shipping pieces.)

### 6b. Splitting the actual math — the model genuinely runs as pieces, on purpose

The deeper case: how a model too big for one GPU actually gets served. Instead of splitting by
*layer*, split **one weight matrix itself** across devices — a `[4096, 4096]` matrix cut
column-wise into two `[4096, 2048]` halves, one per GPU (**tensor parallelism**), or whole
layers assigned to different GPUs in sequence (**pipeline parallelism**). No single GPU ever
holds the full matrix. (This is the two painters sharing one canvas.)

The catch: since the matrix multiply is genuinely split, each GPU's partial result has to be
**combined mid-computation** — a communication step (`all-reduce`/`all-gather`) that stitches
partial answers into the mathematically correct full answer, every forward pass, not just once
at load time. This communication step is the actual reason multi-GPU inference frameworks
(vLLM, DeepSpeed, Megatron) exist.

### What has to hold for either to still work as one system

- **Storage split:** the index/manifest must exactly match the shard files — a missing shard, or
  a key pointing at the wrong file, breaks the reassembled dictionary before the model runs at
  all.
- **Math split:** shapes/dtypes must split cleanly, and every device must agree on *how* it was
  split (row-wise vs. column-wise) so the communication step recombines it correctly — get this
  wrong and it doesn't crash loudly, it silently produces wrong numbers.

---

## 7. Does fine-tuning modify the original file, or produce a new one

**No — the file on disk is never touched during training; only what's in memory changes, and
only an explicit save writes anything back to disk.** Layman version: it's like editing a copy
of a document versus the original sitting on a shelf — nothing happens to the shelf copy until
you deliberately print/save a new one.

`torch.load()` copies the numbers from disk into live tensors in RAM/GPU memory. Every training
step (forward pass → loss → backward pass → optimizer step) updates *those in-memory numbers
only* — the original file sits on disk, frozen, completely unaware training is happening.
Nothing changes on disk until `torch.save()` is called again, and at that point **the filename
is a choice, not something training decides**:

- Save to the **same** path → overwrites the original; the pre-fine-tune weights are gone unless
  a separate copy was kept.
- Save to a **new** path (the normal, recommended pattern) → both versions exist side by side.

This splits differently depending on the fine-tuning method:

- **Full fine-tuning** — every number in the `state_dict` changes in memory over training.
  Saving produces a complete new file, same size/shape as the original, just with different
  numbers throughout. Standard practice: never overwrite the base file — save as
  `finetuned_model.pth`, or periodic `checkpoint-step-1000.pth`, `checkpoint-step-2000.pth`,
  etc., specifically so a bad later update (loss spike, overfitting) doesn't destroy the only
  copy of a good earlier state.
- **LoRA fine-tuning** — the base weights are **frozen the entire time**, in memory and on disk —
  they never change. Only the small adapter matrices train, and those get saved as their own
  tiny, separate file (a few MB, not GBs), fully decoupled from the base `.pth`. A large part of
  why LoRA caught on: one small delta file per fine-tune, not a full duplicate of the whole model
  each time.

---

## 8. Anatomy of a real downloaded model folder (e.g. a ViT checkpoint from HuggingFace)

A downloaded model folder splits **how to build it**, **what the numbers are**, and **how to
prep input for it** into separate files, on purpose. Layman version: flat-pack furniture ships
an instruction booklet (architecture), the actual hardware (weights), and a prep note ("sand the
edges first" — how to prepare your raw material before assembly). Three different kinds of
information, three different files.

- **`config.json`** — the **architecture blueprint**: number of layers, hidden size, attention
  heads, and for a ViT specifically `image_size`, `patch_size`, `num_channels`. Not weights — the
  recipe needed to build the *empty* model structure (correctly shaped, unfilled tensors) before
  any numbers get poured in. Small, plain text, human-readable, diffable in git.
- **`model.safetensors`** — the actual weights (§4/§5): tensor name → numbers, memory-mappable,
  no pickle risk.
- **`preprocessor_config.json`** — how to turn a **raw input image into the exact tensor** the
  model expects: resize dimensions, per-channel normalization mean/std, rescale factor (pixel
  values 0–255 → 0–1), center-crop settings. For a text model the equivalent role is played by
  `tokenizer_config.json`/`vocab.txt` — same job (raw input → the tensor format the model was
  trained on), just for pixels instead of tokens.

**Load order matters:** `config.json` has to be read first — without knowing the architecture,
`model.safetensors` is an unlabeled bag of numbers with no idea how to arrange itself into
layers.

```
config.json               → AutoConfig builds the empty model skeleton (shapes only, nothing filled in)
model.safetensors         → AutoModel.from_pretrained loads weights into that skeleton
preprocessor_config.json  → AutoImageProcessor learns how to turn a raw image into the right tensor
```

**Where mismatches bite:** same failure shape as the tokenizer/chat-template mismatch noted in
[`finetuning_concept_notes.md`](finetuning_concept_notes.md) — if `preprocessor_config.json`'s
normalization values don't match what the model actually trained on, nothing crashes. The model
runs, predictions just get silently worse, because the input pixels are scaled differently than
what the weights learned to expect.
