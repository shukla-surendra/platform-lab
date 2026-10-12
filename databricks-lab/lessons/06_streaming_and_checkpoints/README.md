# Lesson 6: streaming and checkpoints

**Idea:** a streaming query with a checkpoint processes each input once; `availableNow` makes it a scheduled incremental batch; deleting the checkpoint re-reads everything.

**Run:** `uv run python lessons/06_streaming_and_checkpoints/lesson.py`

**Watch for:**
- re-running with no new data adds nothing
- the checkpoint folder structure (offsets, commits, sources)
- duplicated rows after deleting the checkpoint
- a windowed aggregate with a watermark

**Exercise:** change the watermark to `0 seconds` and see which windows are emitted.

Concepts: [Ingestion and streaming](../../docs/04-ingestion-and-streaming.md)
