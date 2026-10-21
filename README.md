# SPM Job Radar

A free job-hunting system for a Senior Product Manager move to Google-tier companies in the UK,
Europe, Australia, Thailand and Malaysia, plus the Gulf (UAE, Saudi Arabia, Qatar), Canada and New
Zealand. Singapore and India are tracked too.

* **[LIVE.md](LIVE.md)**: every PM role LinkedIn posted in the last 48 hours, newest first, to the
  minute. Refreshed every 15 minutes.
* **[JOBS.md](JOBS.md)**: every open matching role at the target companies, ranked. Refreshed every hour.
* **[PLAYBOOK.md](PLAYBOOK.md)**: the 30-day plan and the nightly 2-hour routine.
* **[radar/companies.json](radar/companies.json)**: the 97 target companies, with hubs and why each is on the list.

## Get alerts on your phone (1 minute, free)

1. Install **ntfy** ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) /
   [iPhone](https://apps.apple.com/app/ntfy/id1625396347)). No account is needed.
2. Tap **+** and subscribe to the topic `spm-radar-6c5765428ef955ca` (server: ntfy.sh).
3. Done. You'll get a push within about 15 minutes of a PM role appearing on LinkedIn at a target
   company, a push within the hour for roles on a company's own careers page, a quiet hourly
   round-up of every other new PM role on LinkedIn (07:30 to 23:30 IST only), and a "Tonight's
   shortlist" digest at about 20:50 IST every evening. On a laptop, open
   `https://ntfy.sh/spm-radar-6c5765428ef955ca` in a browser for the same feed.

**Optional: the nightly digest by email.** Add a repository secret named `NTFY_EMAIL` holding the
address (GitHub → this repo → Settings → Secrets and variables → Actions → New repository secret).
Keep the address out of the code: this repository is public.

Alerts go only to the ntfy topic (and that email, if set). Runs are set never to fail, so GitHub sends
no failure emails to the repository owner; scan errors arrive on the ntfy topic instead.

## How it works

`.github/workflows/radar.yml` runs `radar/scan.py` every hour on GitHub Actions, which is free for
public repositories. The scanner:

* reads each target company's own careers API (Greenhouse, Lever, Ashby, SmartRecruiters, Workday,
  Google, Amazon, Microsoft, Netflix, Atlassian, Booking.com);
* companies with no public jobs API (Meta, Revolut, Klarna, Zalando, Shopee and others) are covered
  by a nightly Claude web-search sweep (`radar/NIGHTLY.md`);
* keeps senior-level PM roles in the target countries, removes duplicates, and flags descriptions
  that offer or rule out visa sponsorship or relocation;
* scores each role (seniority, company tier, country, visa signal, freshness), then updates
  `data/jobs.json` and `JOBS.md` and sends the phone alerts.

### The 15-minute LinkedIn scanner

`.github/workflows/linkedin.yml` runs `radar/linkedin_scan.py` every 15 minutes. It asks LinkedIn's
public job search for every product-manager posting from the last 90 minutes in 21 countries (the
biggest markets get a second query for senior titles), keeps every level except junior, and records
when each role was posted (minute-level when LinkedIn gives it). State lives in `data/linkedin.json`,
so it never collides with the hourly scan.

* New roles at target companies that score 65 or more push to your phone straight away. Tapping the
  notification opens the LinkedIn job link, which opens the LinkedIn app if it is installed.
* Roles that already came through a company's own careers page are not alerted twice.
* If LinkedIn answers with a rate limit (HTTP 429), the scanner stops for 40 minutes and tries again.
  `data/linkedin.json` shows the last health result.
* To test without phone alerts, run the workflow by hand with `dry` set to `true`.
* **GitHub's free scheduler is best-effort.** Here the hourly radar has fired every 3 to 6 hours rather
  than hourly, and the 15-minute schedule can be delayed the same way. The scanner therefore looks back
  to its last complete pass (not a fixed 90 minutes), so no role is lost, but a phone alert can arrive
  hours after a posting when GitHub is slow. Saying "sync my board" in a Claude Code session starts a
  fresh scan of both workflows first (see `radar/NIGHTLY.md`), so your nightly session always starts
  with current data.

Edit `radar/config.json` to change titles, countries or alert thresholds (`linkedin_fast` holds the 15-minute scanner's settings), and
`radar/companies.json` to add or remove companies. Run `python radar/probe.py` (or the **probe**
workflow) to health-check career-site endpoints.

This repository is public. Keep resumes and personal details out of it.
