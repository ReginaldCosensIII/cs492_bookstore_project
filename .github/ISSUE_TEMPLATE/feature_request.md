---
name: ✨ Feature Request
about: Propose a new feature or enhancement for Atomic's BookNook.
title: "feat: [Short description of the feature]"
labels: enhancement, needs-triage
assignees: ''
---

## Feature Summary

> One clear sentence describing the feature and the problem it solves.

**As a** [type of user — customer / admin / employee],
**I want to** [perform some action],
**So that** [I achieve some goal / business value].

---

## Problem Statement

> Describe the current gap or pain point. Why does this feature need to exist?

---

## Proposed Solution

> Describe your proposed implementation at a high level. Include UI/UX ideas, API endpoint changes, or business logic changes.

---

## Acceptance Criteria

> Define precisely what "done" looks like. Each item must be testable.

- [ ] Given [context], when [action], then [expected outcome].
- [ ] Given [context], when [action], then [expected outcome].
- [ ] Edge case: [describe edge case and expected behavior].

---

## Technical Scope (Implementation Agent Guidance)

> Complete this section when handing off to an AI agent or developer for implementation.

### Affected Blueprint(s)
- [ ] `main` — General pages
- [ ] `auth` — Login / Registration
- [ ] `cart` — Shopping cart
- [ ] `order` — Order processing
- [ ] `reviews` — Book reviews
- [ ] `admin` — Admin dashboard

### Estimated Files to Modify
| File | Nature of Change |
|---|---|
| `app/services/__.py` | New service function(s) required |
| `app/routes/__.py` | New or modified route(s) |
| `app/templates/__.html` | New or updated Jinja template |

### Database Changes Required
- [ ] No DB changes needed.
- [ ] New table: (describe)
- [ ] New column(s) on existing table: (describe)
- [ ] New raw SQL query required in service layer: (describe)

> **Reminder for Implementation Agent:** All SQL must be raw, parameterized `psycopg2`. No ORM. Verify against `app/models/db.py` connection pattern.

### 🤖 Agentic AI Planning Notes
> If this feature was designed with AI assistance, document it here.

- **AI Tool Used:** (e.g., Antigravity / Gemini)
- **Architect Prompt Summary:** (What directive was given to the AI to generate this plan?)
- **Human Review of Plan:** (Y/N) — Has a human engineer reviewed the AI-generated plan before implementation?

---

## Out of Scope

> Explicitly list what this feature request does NOT include to prevent scope creep.

- This request does not include [X].

---

## Additional Context / References

> Attach mockups, screenshots, links to related issues, or external references.

- Related Issue: #
- Mockup: (link or attach)
