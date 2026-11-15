# Case study: BeReal

## Question

Where are BeReal and its closest competitors losing users?

## Apps

Picked by `ariadne-pmm discover "BeReal" --keyword "photo sharing" --keyword "friends" --top 5`
on 2026-11-15 (live result in pull request #2):

| App | Why it was picked |
|---|---|
| BeReal | The seed app |
| Locket Widget | Found by 3 searches, same genre |
| Snapchat | Found by 3 searches |
| Instants | Found by 2 searches, same genre |
| Instagram | Found by 2 searches |
| Foto | Found by 2 searches, same genre |

## Method

Pack `weakness_map`: up to 500 most recent US App Store reviews per app, 1-3 star reviews only,
each given one theme from a fixed list of 14 by the free keyword labeller (word rules, no AI).
Shares are counts over each app's sample. Keyword labels are rougher than Claude's: read the
quotes under each number before trusting it.

## Known limits before running

A 100-review sample per app (pull request #2) shows how uneven the 1-3 star samples will be:

| App | 1-3 star reviews out of 100 |
|---|---|
| BeReal | 17 |
| Locket Widget | 4 |
| Snapchat | 64 |
| Instants | 52 |
| Instagram | 67 |
| Foto | 12 |

Apps under 30 reviews get counts instead of percentages, and apps under 10 have their reviews
listed without themes. Locket Widget will likely be one of those.

## Result

The report is added to this folder by the `case-study` workflow.
