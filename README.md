# SPM Job Radar

A free job-hunting system for a Senior Product Manager move to Google-tier companies in the UK,
Europe, Australia, Thailand and Malaysia (Singapore and India are tracked too).

* **[JOBS.md](JOBS.md)**: every open matching role, ranked. Refreshed every hour.
* **[PLAYBOOK.md](PLAYBOOK.md)**: the 30-day plan and the nightly 2-hour routine.
* **[radar/companies.json](radar/companies.json)**: the 50 target companies, with hubs and why each is on the list.

## Get alerts on your phone (1 minute, free)

1. Install **ntfy** ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) /
   [iPhone](https://apps.apple.com/app/ntfy/id1625396347)). No account is needed.
2. Tap **+** and subscribe to the topic `spm-radar-6c5765428ef955ca` (server: ntfy.sh).
3. Done. You'll get a push within the hour whenever a senior PM role opens at one of the 50 target
   companies, and a "Tonight's shortlist" digest at about 20:50 IST every evening.

## How it works

`.github/workflows/radar.yml` runs `radar/scan.py` every hour on GitHub Actions, which is free for
public repositories. The scanner:

* reads each target company's own careers API (Greenhouse, Lever, Ashby, SmartRecruiters, Workday,
  Google, Amazon, Microsoft, Netflix, Atlassian, Booking.com), and LinkedIn's public job search in
  15 countries;
* keeps senior-level PM roles in the target countries, removes duplicates, and flags descriptions
  that offer or rule out visa sponsorship or relocation;
* scores each role (seniority, company tier, country, visa signal, freshness), then updates
  `data/jobs.json` and `JOBS.md` and sends the phone alerts.

Edit `radar/config.json` to change titles, countries or alert thresholds, and
`radar/companies.json` to add or remove companies. Run `python radar/probe.py` (or the **probe**
workflow) to health-check career-site endpoints.

This repository is public. Keep resumes and personal details out of it.
