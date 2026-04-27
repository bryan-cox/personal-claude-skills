---
name: obsidian-vault
description: Use when user wants to find, create, or organize notes in their Obsidian vault. Triggers on keywords like "note", "vault", "obsidian", "write up", "document this procedure", or references to meetings, procedures, or active work notes.
---

# Obsidian Vault

## Vault Location

`~/Red Hat/`

## Folder Structure

| Folder | Purpose |
|--------|---------|
| Active Work | Current projects and initiatives |
| Meetings | Meeting notes |
| Procedures | How-to guides and reference procedures |
| Education | Learning notes |
| Cursor Logs | Cursor session logs |
| Work log | Daily work log notes, organized by year/month (Work log/YYYY/MM/YYYY-MM-DD.md) |
| zPrevious Work | Archived/completed work |
| zzAttachments | Images and file attachments |

## Naming Conventions

- **Title Case** for all note names (e.g., `Azure HCP CLI Commands.md`)
- No special prefixes or numbering
- Descriptive names that stand alone

## Index Notes

- **Index notes** aggregate related topics within a folder (e.g., `Azure Index.md`, `HyperShift Index.md`)
- An index note is a list of `[[wikilinks]]` grouping related notes by theme
- When creating a note that fits an existing index topic, add a link to the relevant index note
- When a cluster of 3+ related notes exists without an index, create one

## Linking

- Use Obsidian `[[wikilinks]]` syntax: `[[Note Title]]`
- Link to related notes at the bottom of each note
- Link to relevant index notes where applicable
- Attachments go in `zzAttachments/` and are referenced via `![[filename]]`

## Workflows

### Search for notes

```bash
# Search by filename
find ~/Red\ Hat/ -name "*.md" -not -path "*/.obsidian/*" | grep -i "keyword"

# Search by content
grep -rl "keyword" ~/Red\ Hat/ --include="*.md"
```

Or use Grep/Glob tools directly on the vault path.

### Create a new note

1. Choose the appropriate folder based on content type
2. Use **Title Case** for the filename
3. Write content in standard markdown
4. Add `[[wikilinks]]` to related notes at the bottom
5. Place any images/attachments in `zzAttachments/`

### Find related notes

Search for backlinks across the vault:

```bash
grep -rl "\[\[Note Title\]\]" ~/Red\ Hat/ --include="*.md"
```

### Find index notes

```bash
find ~/Red\ Hat/ -name "*Index*" -not -path "*/.obsidian/*"
```

### Move notes to archive

Move completed work notes from `Active Work/` to `zPrevious Work/`.

## Daily Log Format

See [daily-log-format.md](./daily-log-format.md) for the canonical schema of daily work log notes.

---

*Based on [mattpocock/skills/obsidian-vault](https://github.com/mattpocock/skills/blob/main/obsidian-vault/SKILL.md), adapted for local vault structure.*
