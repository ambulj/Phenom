# PHASE 4: Long-Term Memory and File Search

Everything here respects privacy labels.

## Objective
Phenom remembers past conversations, indexes user notes and documents with local vector embeddings, integrates with an Obsidian vault, searches photos by description without ever modifying them, extracts learned rules from corrections, and provides reversible Downloads organization.

## Build

1. **Local embeddings and a vector index** over folders the user chooses, stored encrypted at rest, with incremental updates when files change.
2. **Search** across documents, notes, and past conversations with sources shown for every answer.
3. **Photo indexing**: captions and tags generated locally, searchable by description. Phenom never moves, renames, edits, or deletes photos, enforced by a tool-level block.
4. **Obsidian vault** inside the project folder (`vault/`). Phenom writes notes, summaries, and daily logs there as plain Markdown.
5. **Learned rules**: when the user corrects Phenom, extract a rule, apply it automatically, and show it in the learned-rules panel for editing or deletion. Log every rule application.
6. **Long PDF and lecture-note summaries**: local 8B by default and for private files; cloud Nemotron for long non-private files after the previewed approval. Chunk long files and show progress.
7. **Scheduled cleanup**: auto-organize Downloads by file type and date and move duplicates to the recycle bin. Every move is logged and can be undone from the log. Run a dry run first and show it to the user before the first real run.

## Tests
- Retrieval quality on a small test folder with known answers.
- A cleanup dry run and an undo.
- A test that photos are never modified.
- A rule add, edit, and delete round trip.

## Done criteria
- [ ] Search returns the right sources
- [ ] Nothing private reaches the cloud without approval
- [ ] Cleanup is reversible with undo
- [ ] Photos are untouched by construction
- [ ] Learned rules auto-extracted and applied

## Finish
Follow the finish protocol in AGENTS.md section 7 and stop.
