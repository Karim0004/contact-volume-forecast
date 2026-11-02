# Notes

## Initial exploration, 2 Nov 2026

2,386,138 HPD requests from NYC 311, created between 1 Nov 2023 and 30 Oct 2026. 6 columns, no missing values, and unique_key is unique.

1. Five days have no rows at all: 11 to 14 Apr 2024 and 13 Jul 2024. The day after the April gap (15 Apr 2024) has 7,398 requests, one of the highest in the data, so it looks like a feed outage and then a backlog. These days need handling before any model sees them.
2. Volume is very seasonal. January 2026 had 129,816 requests, while the summers of 2024 and 2025 ran at about 40,000 to 47,000 a month (summer 2026 sits higher, at about 47,000 to 56,000). That fits HEAT/HOT WATER being the biggest complaint type, with 38% of all requests.
3. A day averages 2,189 requests (median 1,937), from 473 on 4 Jul 2025 to 8,228 on 8 Feb 2026. Weekdays average between 2,186 (Fri) and 2,626 (Mon), and weekends about 1,540 to 1,590.
4. Phone and online are almost level overall (47% and 46%, mobile 7%), but phone fell by a third from Nov to Dec 2025 (50,340 to 33,509) while online more than doubled. Phone stayed flat over the same months in 2024 (45,918 to 44,506), so the drop isn't seasonal.
5. A couple of small data issues: one row has complaint_type "Safety" next to the usual SAFETY, and 3 rows have borough "Unspecified".

Still to decide: forecast all channels or phone only. Point 4 matters for that, since a phone-only series has a level shift in Dec 2025.
