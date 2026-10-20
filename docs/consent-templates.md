# Consent and notice templates

Status: drafts, 2026-10-21. These are **not legal advice**. They must be reviewed by the controller's DPO and counsel and adapted to the jurisdiction. Plain-language targets follow EDPB 05/2020 §3.3 (informed consent: controller identity, purpose, data, withdrawal right, Art. 22 information, transfers) (edpb2020consent).

Placeholders are written as `[LIKE THIS]`.

---

## 1. Pilot participant information sheet and consent form

**Study title.** Continuous typing-rhythm risk signal: same-device feasibility pilot.
**Researcher / controller.** `[NAME, ORGANISATION, CONTACT]`. **DPO.** `[CONTACT]`.

### 1.1 What the study is about

We are testing whether software can notice, from *how* (not *what*) someone types, that a different person has started using a computer. You will type on your own computer and on other participants' computers, and they will type on yours.

### 1.2 What we collect

- **Timing of key presses and releases, grouped into "zones":** left hand, right hand, space bar, modifier keys.
  - We never record which letter or character you typed.
  - Raw timings stay in memory for about one minute and are then reduced to 21 summary numbers per window. Only these window summaries are stored.
- **The copy-typing task only, and only if you tick box C below:** per-key zone timings while you type a **text we provide**. That text contains nothing about you.
- **Small facts:** your participant code, the type of keyboard (laptop or external), and, **if you choose to tell us**, age band, handedness, typing language, and whether you have any condition that affects typing. These facts are used **only** to check that the system is fair across groups. Each question has a "prefer not to say" option.
- **Not collected:** what you type, screen contents, the applications you use, websites, or your location.

### 1.3 Why typing timing is sensitive

Typing rhythm can be used to recognise people. In law it can count as **biometric data**, which is a special category. Detailed timing streams can also reveal something about the text typed; that is why we store only window summaries, except in the copy task.

### 1.4 What happens to the data

- Stored under a participant code on `[SERVER, REGION]`, accessible only to the research team.
- Deleted `[N]` months after the study ends (at most 12).
- Results are published only as group statistics. No individual can be identified in publications.
- Data is never used to judge your work, health or abilities. It is never given to your employer.

### 1.5 Your rights

- Taking part is **voluntary**. Not taking part, or stopping, has no consequences for you.
- `[If participants are colleagues:]` The research team is independent of your line management. Your manager will not know whether you took part.
- You can withdraw at any time, without giving a reason, by `[EMAIL / BUTTON IN THE APP]`. Your data is then deleted, except results already aggregated into published statistics.
- You have the right to access, correct and erase your data, and to complain to `[SUPERVISORY AUTHORITY]`.

### 1.6 Consent (tick each box you agree to)

- [ ] **A.** I have read this sheet and had the chance to ask questions.
- [ ] **B.** I agree to the processing of my typing-timing window summaries, which may be biometric data, for this study (GDPR Art. 9(2)(a) explicit consent).
- [ ] **C.** *(optional)* I agree to per-key zone timings being stored while I type the provided copy text.
- [ ] **D.** *(optional)* I agree to answer the fairness questions (age band, handedness, language, typing-related condition). I may skip any of them.
- [ ] **E.** I agree that other participants type on my computer during the scheduled sessions, using a separate study account (no access to my files).

Name / code: `[ ]`   Date: `[ ]`   Signature: `[ ]`

---

## 2. End-user notice (product, short layered notice)

**Layer 1 (shown at enrolment, ≤ 60 words).**
> **Typing-rhythm protection (optional).** If you turn this on, this device learns *how* you type (timing only, never the letters). If someone else seems to be typing, `[SERVICE]` may ask you to confirm it's you with your security key or passkey. Your typing pattern stays on this device. **[Turn on]** **[No thanks]** **[Learn more]**

"No thanks" MUST be as prominent as "Turn on". It leads to the same service without ZTBE (non-biometric alternative; EDPB 3/2019 §5.1, NIST 800-63B-4).

**Layer 2 ("Learn more").**
- **What:** key-press timing, grouped by hand zone, summarised every minute on this device. No text, screen, app or website data.
- **Where:** your template is sealed on this device (by its security chip where available). `[SERVICE]` receives only "low / medium / high" risk changes and signed device proofs, and keeps them ≤ 30 days.
- **Why:** to notice if someone else uses your unlocked session. It is **not** a login method and never locks you out by itself.
- **Accuracy:** it can be wrong. You may occasionally be asked to confirm with your passkey, typically less than once per hour of typing (`[UPDATE FROM PILOT]`).
- **Accessibility:** on-screen keyboards, dictation and similar tools are not analysed and never count against you. You can turn the feature off at any time in `[SETTINGS]` without giving a reason.
- **Legal basis:** your explicit consent (GDPR Art. 9(2)(a)). Withdraw at any time; your template and our records are then deleted.
- **Contact / DPO / complaints:** `[ ]`.

**Not for employee monitoring.** If `[SERVICE]` is your employer, this notice MUST NOT be used until the DPIA (`docs/dpia-outline.md`) and a legal opinion confirm a lawful basis. Consent is generally not valid at work (EDPB 05/2020 para 21).
