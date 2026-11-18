# Case study: Apple Music

## Question

Where are Apple Music and its closest competitors losing users?

## Apps

| App | App Store ID |
|---|---|
| Apple Music | 1108187390 |
| Spotify | 324684580 |
| YouTube Music | 1017492454 |
| Pandora | 284035177 |
| Amazon Music | 510855668 |
| SoundCloud | 336353151 |

Chosen by competitor discovery from the seed "Apple Music" with the keywords "music streaming"
and "songs", then pinned by ID in `args.txt` so every re-run compares the same six apps.

Two adjustments to what discovery returned:

- **Shazam excluded.** Discovery ranked it fourth, but it identifies songs rather than
  streaming them, and Apple owns it. In the first run 78% of its complaints matched no theme.
- **Pinned because search results vary.** Two runs an hour apart with identical settings gave
  different lists: one dropped Spotify, which other runs ranked first. Pinning keeps the
  comparison stable.

## Method

Pack `weakness_map`: up to 500 most recent US App Store reviews per app, 1-3 star reviews only,
each given one theme from a fixed list of 14 by the free keyword labeller (word rules, no AI).
Shares are counts over each app's sample. Keyword labels are rougher than Claude's: read the
quotes under each number before trusting it.

## Result

The report is added to this folder by the `case-study` workflow.
