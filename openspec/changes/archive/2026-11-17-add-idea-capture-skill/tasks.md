# Tasks

## 1. Template

- [x] 1.1 Add a `Dependencies` field to the idea template in `docs/ideas/README.md` — a bullet list placed between `Constraints / conflicts` and `Open questions`, each line a reference marked `— known` or `— dependency unknown` — and verify by reading the file back that the template is coherent and the field is in the right place.

## 2. Skill

- [x] 2.1 Create `.opencode/skills/idea-capture/SKILL.md` with frontmatter (`name`, `description`) and a body that states the lifecycle, the template, and the dependency rule (verify a reference exists before marking it `known`), and verify the file has a non-empty `description` and references `docs/ideas/README.md` as the template source.

## 3. Subagent

- [x] 3.1 Create `.opencode/agent/idea-capture.md` with frontmatter (`description`, `mode: subagent`, `model` selected via `opencode models`, `permissions`) scoped to write `docs/ideas/**` and read `docs/adr/**` and `docs/bdr/**`, and verify the file parses and grants no write permission outside `docs/ideas/**`.

## 4. Integration check

- [x] 4.1 Run `openspec validate add-idea-capture-skill --strict` and verify it reports no errors.
