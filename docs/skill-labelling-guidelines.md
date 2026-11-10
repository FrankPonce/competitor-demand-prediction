# Skill labelling guidelines (Sprint 11)

One page, used for three things: the LLM's instructions, the gold-set pre-labels, and your verification.
A label is a **span of text** in one sentence from a job posting.

## Label it: a skill span

A **skill** is a capability, body of knowledge, tool or method that the candidate must have or will use in the role.

| Type | Examples (span in **bold**) |
|---|---|
| Tools, languages, frameworks, platforms | **Python**, **PyTorch**, **Kubernetes**, **Salesforce**, **SAP**, **CUDA** |
| Technical methods and knowledge | **distributed training**, **reinforcement learning**, **RTL design**, **thermal modelling**, **GAAP** |
| Domain expertise | **medium-voltage distribution**, **export controls**, **revenue recognition**, **contract negotiation** |
| Professional skills, when stated as a requirement | **stakeholder management**, **technical writing**, **people management**, **solution selling** |
| Certifications and licences | **PE license**, **CISSP**, **CPA** |
| Spoken languages, with a proficiency cue | fluent **Japanese** |

## Do not label

| Not a skill | Example |
|---|---|
| Teams, functions, customers, partners | partner with the **Sales** team · sell to **startup founders** |
| Products or companies as context | our **Claude** API · customers on **Azure** (unless they must *use* Azure) |
| Generic or vague phrases | strong **skills** · **experience** · **best practices** · **innovative solutions** |
| Personality traits and attitudes | **curious**, **humble**, **passionate**, **self-starter** |
| Years, degrees and seniority | **5+ years**, **BS degree**, **senior** |
| Outcomes and responsibilities that are not a capability | **drive revenue** · **own the roadmap** |

## Span boundaries

- **Shortest complete name**, without filler: "experience with **distributed systems**", not "experience with distributed systems".
- **Keep modifiers that change the meaning:** **medium-voltage distribution**, **enterprise SaaS sales**, **large-scale pretraining**.
- **Lists:** label each item separately: **Python**, **Go**, or **Rust**.
- **Parenthetical acronyms** belong to the span when attached: **battery energy storage system (BESS)**.
- **Coordinated phrases:** split when each part is a skill on its own: **ad networks**, **payment processing**. When the shared head word only appears once, label the full phrase: **medium-/high-voltage distribution**.
- **When unsure**, ask: would a recruiter search a CV for this exact phrase? If yes, it is a skill.

Gold labels were pre-labelled by the assistant following this page, then verified by the project owner.
