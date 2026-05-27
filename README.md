# LRC Tutoring Dashboard

Interactive tutoring analytics dashboard for the Learning Resource Center at University of Louisville.

## How to update the dashboard

1. Export your semester data as a CSV named after the semester (e.g. `Spring 2026.csv`)
2. Go to the `data/` folder in this repository on GitHub
3. Click **Add file -> Upload files**
4. Upload the CSV and click **Commit changes**
5. GitHub Actions will automatically process the data and update the dashboard
6. The live dashboard will reflect new data within ~1 minute

## Dashboard URL

[View Dashboard](https://UofLREACH.github.io/lrc-dashboard/)

## CSV Format

The CSV export should include these columns:
- Student, Date, Appt Started, Appt Ended, Appt Hours, Seconds
- Appt Subject, Appt Reason, Appt Consultant, Appt Center, Appt Status
- Visit Record #, Visit Time, Visit Subject, Visit Reason, Visit Consultant, Visit Center
- Student ID
