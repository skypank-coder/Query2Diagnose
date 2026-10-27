# Source documents

Troubleshooting text used for the hypothesis model, the retrieval index and the
benchmark's source passages.

**Policy:** iFixit pages (CC BY-NC-SA 3.0) and U.S. public-domain pages only.
No manufacturer manuals or service guides, not even as local copies.

| Path | Contents | Licence |
|---|---|---|
| `manifest.yaml` | Pages to fetch | MIT (project file) |
| `raw/ifixit/*.json` | iFixit pages, trimmed, pinned to `revisionid` | CC BY-NC-SA 3.0 |
| `raw/public_domain/*.json` | Kept sections of U.S. government pages | Public domain |
| `passages.jsonl` | Section-level passages with stable IDs | CC BY-NC-SA 3.0 (iFixit rows) / public domain |
| `passage_faults.yaml` | Which passages describe which fault (hand annotation) | MIT (project file) |
| `LICENSES.md` | Per-page URL, revision, access date, authors (generated) | — |

## Rebuild

```bash
mingw32-make sources    # downloads only pages missing from raw/ (3 s between requests)
mingw32-make passages   # rewrites passages.jsonl and LICENSES.md
```

`python -I -m bench.fetch_sources --refresh` re-downloads everything. That can
change passage text and IDs, so rerun the tests and check `passage_faults.yaml`
and `data/hypothesis_model.yaml` citations afterwards.

## Adding a source

1. Confirm its terms allow non-commercial research reuse and redistribution,
   and record them in `docs/design_decisions.md` ("Data sources").
2. Add it to `manifest.yaml` (iFixit: namespace + title; public-domain page:
   URL + headings to keep).
3. Run `make sources passages test`.

Passage IDs: `ifx-<wikiid>-<heading path slug>` for iFixit,
`pd-<id>-<heading slug>` for public-domain pages.
