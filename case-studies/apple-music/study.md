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

## Findings

Full numbers and the reviews behind them: [`weakness_map-2026-11-18.md`](weakness_map-2026-11-18.md).
Shares are of each app's 1-3 star reviews, labelled with keyword rules v3.

### 1. Apple Music's biggest problem right now is its own redesign

38% of Apple Music's complaints (53 of 138) are about a recent change: the black-and-white
logo, the new colours, the new playlist screens. No competitor comes close; YouTube Music is
next at 12%. Reviewers ask to "change it back to red", and some say they are cancelling.

**So what:** this is a short-term risk, not a positioning weakness. It is tied to one release
(v3.18), and the reviews read are the 500 most recent, so the spike may fade. Worth re-running
in a month to see whether it does.

### 2. Ads are the clearest gap between Apple Music and its rivals

| | Apple Music | Spotify | Pandora | SoundCloud | YouTube Music | Amazon Music |
|---|---|---|---|---|---|---|
| Ads | 1% | 30% | 28% | 35% | 4% | 4% |
| Pricing and paywall | 15% | 31% | 28% | 23% | 26% | 26% |

Ads are a top-two complaint for Spotify, Pandora and SoundCloud, all of which have free,
ad-supported tiers. Apple Music has no ad tier, and it also draws the fewest pricing
complaints of the six.

**So what:** "no ads, ever" is a message aimed directly at the most common pain of free
Spotify, Pandora and SoundCloud users, and Apple Music's reviews give no evidence against it.
The trade-off is that those users are on a free tier because they don't want to pay, so the
message needs a trial or price offer next to it.

### 3. YouTube Music's weak spot is reliability

19% of YouTube Music's complaints (71 of 373) are bugs: playback stopping, playlists not
saving, crashes. That is the highest of the six; Apple Music is at 6%.

**So what:** against YouTube Music, the stronger angle is "it just works", not price.

## Limits

- **Keyword labels.** The free labeller matches words, not meaning. 17-23% of each app's
  complaints still match no theme, and some labels are wrong. Read the quotes before quoting a
  number.
- **A snapshot.** Each app's sample is its 500 most recent US reviews. For apps this size that
  covers about two weeks: the quoted reviews in the report are dated Oct 29 to Nov 15, 2026.
- **Complaints only.** 1-3 star reviews say where apps lose users, not why people choose them.
- **Shazam excluded and apps pinned.** See "Apps" above.
