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
each labelled with one theme from a fixed list of 14. Shares are counts over each app's sample.

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

At 500 reviews, Locket Widget will likely fall under the pack's 30-review minimum and Foto will
be close to it. The report flags low samples; treat those two apps as directional.

## Result

The report is added to this folder by the `case-study` workflow.
