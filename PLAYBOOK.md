# 30-Day SPM Job Hunt Playbook

Target: Senior Product Manager at Google-tier companies, in the UK, Europe, Australia,
Thailand or Malaysia, plus the Gulf (UAE, Saudi Arabia, Qatar), Canada and New Zealand
(Singapore and India hubs are tracked too). Budget: ₹0. Time: 2 hours a night.

## What "success in 30 days" means

Big-tech hiring is slow. A Google loop alone usually takes 6–10 weeks from application to offer,
and team-matching can add more time. So the goal for these 30 days is a **full pipeline**. Offers
usually come in weeks 6–10, and they only come if the pipeline is full by day 30.

| Metric (by day 30) | Target |
|---|---|
| Tailored applications sent | 60+ (about 2–3 a night, always within 48h of a job being posted) |
| Referral / hiring-manager messages sent | 100+ (about 4 a night) |
| Referrals secured | 15+ |
| Recruiter screens | 8–12 |
| Full interview loops started | 3–5 |

A referral is the single biggest lever. At big tech, a referred application is several times more
likely to reach a recruiter than a cold one. Every application in this plan gets a referral attempt.

## How the system works

```
Every hour (GitHub Actions, free)        Every night, about 21:00 IST        Your 2 hours
────────────────────────────────         ─────────────────────────────       ────────────────────────
79 target companies' career sites  ──►   ntfy digest: "Tonight's      ──►    Command Center dashboard:
+ LinkedIn every 15 min, 21 countries    shortlist: N new roles"             triage → tailor → apply
filter: SPM-level × your countries       Claude routine scores roles          → referral asks → prep
dedupe, score, visa/relocation flags     against your resume and syncs        → log status
instant phone push for target roles      them to the dashboard
```

* **Instant alerts**: a new PM role on LinkedIn at one of the 79 target companies pushes to your
  phone within about 15 minutes through the free **ntfy** app (see README for the 1-minute setup).
  Roles on a company's own careers page push within the hour.
* **LIVE.md**: every PM role LinkedIn posted in the last 48 hours, newest first, to the minute.
* **JOBS.md**: the full, always-current list of roles at target companies, sorted by score.
* Recency matters: roles applied to within a day or two get far more recruiter attention. In the
  Command Center, sort All roles by *Most recent first* and use the *Posted* filter (last hour,
  3 hours, 24 hours).
* **Command Center** (a private claude.ai page): the shortlist, the application tracker, and a
  "Tailor with Claude" button that writes the resume bullets and answers for a specific role.

## The nightly 2 hours (example: 21:30–23:30 IST)

| Time | Block | What you do |
|---|---|---|
| 0:00–0:10 | **Triage** | Open the Command Center. Star tonight's 3 roles: highest score, posted most recently, best fit. Skip roles marked "no sponsorship" unless you already have the right to work there. |
| 0:10–0:55 | **Apply ×3** (15 min each) | Click *Tailor with Claude* → paste the summary and the 3 rewritten bullets into your resume → export PDF → apply on the company's own site (not LinkedIn Easy Apply). Log it as *Applied*. |
| 0:55–1:25 | **Referrals ×4–5** | Open the Command Center's **People** tab. Use its LinkedIn searches to find 2–3 people per role: Indian PMs who moved abroad first, then ex-Policybazaar colleagues, IIM Nagpur alumni and hiring managers. Send the drafted note, then log each person in the role's sheet. |
| 1:25–1:55 | **Interview drill** | One 30-minute drill per night from the rotation below, done with Claude as the interviewer. |
| 1:55–2:00 | **Log** | Update statuses. Anything with no response for 7 days → send one polite follow-up. |

### Drill rotation (one per night)

| Night | Drill | Prompt to give Claude |
|---|---|---|
| Mon | Product sense / design | "Act as a Google L6 PM interviewer. Give me a product design question, let me answer, then grade me on user segmentation, pain points, prioritisation, solutions and metrics." |
| Tue | Analytical / metrics | "Give me a metrics-drop root-cause case (e.g. 'YouTube watch time dropped 8% WoW'), then grade my structure." |
| Wed | Strategy | "Ask me a product strategy question about entering a new market or responding to a competitor, then critique it." |
| Thu | Leadership / behavioural | "Ask me 3 behavioural questions for a Senior PM (conflict, influence without authority, failure). Grade each STAR answer and rewrite the weakest." |
| Fri | Technical for PMs | "Ask me a system-design-for-PMs question (e.g. design a notification system); probe trade-offs, APIs, latency, privacy." |
| Sat | Full mock loop | "Run a 45-minute mock onsite: 1 design, 1 metrics, 1 behavioural question. Give a hire/no-hire verdict with reasons." |
| Sun | Weekly review | Look at the funnel numbers, refresh your resume variants, pick next week's 10 dream roles, and refill the outreach list. |

## The 30 days, week by week

**Week 1 (days 1–7): foundation + first wave**
1. Resume rewrite (night 1–2). Claude rewrites every bullet in Google's X-Y-Z format: *Accomplished X,
   as measured by Y, by doing Z*. Two variants: one led by consumer/growth work, one led by
   platform/B2B work. One page if under 10 years of experience, two pages max otherwise.
2. LinkedIn (night 2). Headline: `Senior Product Manager | <domain> | <2 metrics>`. Set Open to Work
   (visible to recruiters only) with your target cities: London, Dublin, Amsterdam, Berlin, Sydney,
   Bangkok, Kuala Lumpur, Singapore. The About section uses the same 3 headline wins as the resume.
3. Story bank (night 3). Write 12 STAR stories with Claude, covering a launch, a failure, a conflict,
   a data-driven pivot, influence without authority, a hard prioritisation call, leading through
   ambiguity, and mentoring. Every interview draws on these.
4. Applications 4–7 nights × 3 roles, plus referral asks for each one.

**Week 2 (days 8–14): volume**
* 3 applications a night, 5 referral asks a night.
* Google rule: Google lets you apply to at most **3 roles in any 30-day window**. Use those slots
  only on the best-fitting roles, and ideally with a referral already in hand.
* Message 5 recruiters a week who post SPM roles in your target cities (template below).

**Week 3 (days 15–21): screens begin**
* Before each recruiter screen, have Claude write a one-page brief on the company: products, recent
  launches, likely questions, and your best 3 stories mapped to that role.
* Do a full mock loop twice this week.
* Follow up on anything 7+ days old.

**Week 4 (days 22–30): loops + keep the funnel full**
* Keep 15+ roles active at all times. Don't stop applying because one loop is going well.
* Get documents ready for visa paperwork: degree certificates, experience letters, passport validity,
  police clearance (some countries need it).
* If an offer comes, ask Claude to prepare a negotiation plan using relocation package, sign-on bonus,
  and level as the levers.

## Outreach templates

**Connection note (LinkedIn, under 300 characters)**
> Hi {name}, I'm a Senior PM ({domain}, {1 headline metric}). I just applied to {role} ({job ID}) on
> your team in {city}. Would you be open to a quick look at my profile and, if it fits, a referral? Happy to send a 3-line summary.

**After they accept**
> Thanks {name}! Short version: {years} yrs PM; led {biggest win with number}; {second win}. Role:
> {link}. Resume attached. If it looks like a fit, a referral would mean a lot. If not, any pointer
> to the right person is just as helpful.

**Recruiter note**
> Hi {name}, I saw you're hiring Senior PMs in {city}. I've {headline metric} at {company} and I'm
> relocating for the right role. Visa sponsorship would be needed. Would a 15-minute call make sense?

**Follow-up (7 days later, once only)**
> Hi {name}, just bumping this in case it got buried. Still very keen on {role}. Thanks either way!

## Visa and relocation by country

Rules change often. Before you rely on any detail here, check the official page linked in each row.

| Country | Usual route | What to check |
|---|---|---|
| UK | Skilled Worker visa (employer must be a licensed sponsor) | Employer is on the [UK register of licensed sponsors](https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers); salary meets the current threshold |
| Ireland | Critical Skills Employment Permit | [enterprise.gov.ie](https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/) salary thresholds |
| Netherlands | Highly Skilled Migrant via a recognised sponsor; 30% tax ruling | [IND public register](https://ind.nl/en/public-register-recognised-sponsors) |
| Germany | EU Blue Card | [make-it-in-germany.com](https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card) |
| Sweden | Work permit with an employer offer | [migrationsverket.se](https://www.migrationsverket.se) |
| Australia | Employer-sponsored Skills in Demand visa | [immi.homeaffairs.gov.au](https://immi.homeaffairs.gov.au) |
| Singapore | Employment Pass (COMPASS points) | [mom.gov.sg](https://www.mom.gov.sg/passes-and-permits/employment-pass) |
| UAE (Dubai, Abu Dhabi) | Employer-sponsored work permit and residence visa; Golden Visa for some skilled professionals | [u.ae](https://u.ae/en/information-and-services/visa-and-emirates-id) · no personal income tax in the UAE, check each offer's package |
| Saudi Arabia / Qatar | Employer-sponsored work visa (Saudi: through the Qiwa platform) | [qiwa.sa](https://qiwa.sa) · [hukoomi.gov.qa](https://hukoomi.gov.qa) |
| Canada | Employer-supported work permit (the Global Talent Stream can apply to tech roles); Express Entry as the long-term route | [canada.ca](https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada.html) |
| New Zealand | Accredited Employer Work Visa (employer must be accredited) | [immigration.govt.nz](https://www.immigration.govt.nz/new-zealand-visas/visas/visa/accredited-employer-work-visa) |
| Malaysia | Employment Pass (employer applies through ESD) | [esd.imi.gov.my](https://esd.imi.gov.my) |
| Thailand | Non-B visa + work permit, or the LTR "highly-skilled professional" visa | [ltr.boi.go.th](https://ltr.boi.go.th) |

The radar flags jobs whose description mentions sponsorship or relocation (✅) or rules it out (⛔).
Agoda (Bangkok), Booking.com, Adyen and Netflix (Amsterdam), Wise (London/Tallinn), Grab (KL/Singapore),
Atlassian/Canva (Sydney), Okta and Cohere (Toronto) and Scale AI/Ebury (Dubai) are known for hiring
internationally. Check each posting's wording before assuming sponsorship.

## Google SPM loop: what to expect

1. Recruiter screen (30 min): background, level calibration (L6 = Senior PM), location and visa.
2. 1–2 phone interviews: product sense and analytical.
3. Onsite (virtual, 4–5 × 45 min): product design, analytical/metrics, strategy, technical, and
   "Googleyness & Leadership".
4. Hiring committee → team match → offer. Team matching can take 2–6 weeks; keep other loops running.

Prepare with the drill rotation above, and practise answering out loud. Claude can grade you against
Google's rubric: structure, user focus, creativity, data-driven trade-offs, technical depth, and
collaboration.
