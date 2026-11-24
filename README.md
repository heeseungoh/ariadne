# Ariadne

**Turn app reviews into positioning you can actually back up.**

## Why I built this

I'm a Management Engineering student at Waterloo, doing a product marketing internship. One thing
I noticed fast: a lot of PMM work is ambiguous questions. Where are competitors weak? What do users
actually care about? Is the price the problem? Usually the answer ends up being someone's gut
feeling.

I wanted to answer those with data instead. Reviews are the easiest customer data to get, but
reading thousands of them by hand doesn't scale, and asking an AI to "summarize the reviews"
gives you numbers you can't check. So I built Ariadne: you type in an app, it finds the
competitors, pulls their reviews, sorts every complaint into a theme, and counts them. Every
number links back to the actual reviews behind it, so if someone asks "where did that come
from?" you can show them.

**About the name:** in the Greek myth, Ariadne gives Theseus a ball of thread (a "clew") so he
can find his way out of the Labyrinth. That's where the word "clue" comes from. PMM questions
feel like a labyrinth, and this is the thread.

## What I found

### Apple Music vs. Spotify, YouTube Music, Pandora, Amazon Music and SoundCloud

[Full write-up](case-studies/apple-music/study.md) · [Full report with every review behind the numbers](case-studies/apple-music/weakness_map-2026-11-18.md)

I pulled the 500 most recent US App Store reviews for each app and looked at the 1-3 star ones,
which came to between 62 and 373 complaints per app. Three things stood out.

**1. Apple Music's biggest problem right now is Apple Music.** 38% of its complaints (53 of 138)
are about its own recent redesign: the new black-and-white logo, the colours, the new playlist
screens. People are literally writing "change it back to red." No competitor is close; YouTube
Music is next at 12%. This one's tied to a single update, so it might fade. I want to re-run it
in a month and see.

**2. Ads are the biggest gap between Apple Music and everyone else.**

| | Apple Music | Spotify | Pandora | SoundCloud | YouTube Music | Amazon Music |
|---|---|---|---|---|---|---|
| Ads | 1% | 30% | 28% | 35% | 4% | 5% |
| Pricing / paywall | 15% | 31% | 28% | 23% | 26% | 28% |

Ads are a top-two complaint for Spotify, Pandora and SoundCloud, which all have free ad-supported
tiers. Apple Music doesn't have one, and it also gets the fewest pricing complaints of the six.
If I were writing Apple Music's messaging, "no ads, ever" would go straight at the biggest pain
point of free Spotify users. The catch is that those people are on a free tier because they don't
want to pay, so it would need a trial or a price offer next to it.

**3. YouTube Music's weak spot is reliability, not price.** 19% of its complaints (71 of 373)
are bugs: playback stopping, playlists not saving, crashes. That's the highest of the six. Apple
Music is at 6%. So against YouTube Music, "it just works" is a better angle than price.

**How much to trust this:** these labels come from keyword rules, not AI, so they're rough.
About 17-23% of each app's complaints didn't match any theme, and some labels are wrong. That's
why every number in the report has the real reviews under it. Check those before quoting a number.

### BeReal (first test run)

[Report](case-studies/bereal/weakness_map-2026-11-15.md)

BeReal was the first run, mostly to see if the tool worked end to end on real data. A couple of
things showed up: Instagram's top complaint was account and login problems (22% of 314), and
Locket Widget's was bugs (27% of 49). But the bigger lesson was about the tool. 31-64% of
complaints per app didn't match any theme, and some apps had too few reviews for a percentage to
mean anything. That's what led to the small-sample rules and the better keyword rules I used for
Apple Music.

## How it works

1. **Find competitors.** Type one app. Ariadne searches the App Store with its name, keywords
   from its own description, and any keywords you add. An app has to show up in at least two
   searches to count, and it tells you why each one made the list. You can drop the ones that
   don't fit with `--exclude`, or pin the exact apps you want with `--app`.
2. **Collect.** Pulls up to about 500 recent App Store reviews per app from Apple's public feed.
3. **Label.** Every 1-3 star review gets one theme from a fixed list of 14 (pricing, ads, bugs,
   "the update made it worse", and so on). Either free keyword rules do it, or Claude does.
4. **Count.** The counting is plain code (pandas), never the AI. Every share is shown with its
   sample size.
5. **Report.** A markdown battlecard per app, with the reviews behind each number.

## Why not just ask Claude?

Honestly, for a quick look at a few reviews, just ask Claude. Ariadne is for when you have to
defend the numbers to someone else.

| | Asking Claude in a chat | Ariadne |
|---|---|---|
| How much data | Whatever you paste in | About 500 reviews per app, pulled automatically |
| Numbers | Estimated by reading | Counted in code, with the sample size |
| Can you check it? | A summary with a few quotes | Every number lists the reviews behind it |
| Same answer twice? | Themes shift between chats | Fixed theme list, same input gives same output |
| Quotes | Might be paraphrased | Only kept if they're word for word |

What it doesn't claim: when Claude does the labelling, it's not smarter than a chat, and a chat
is better for follow-up questions.

## Quick start

```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=your-key

ariadne-pmm packs

# See who Ariadne picks as competitors (free, no API key needed)
ariadne-pmm discover "BeReal" --keyword "photo sharing" --top 5

# Drop an app that isn't a real competitor; the next best one moves up
ariadne-pmm discover "Apple Music" --keyword "music streaming" --exclude "Shazam"

# Pull the reviews and see counts by star rating (free, no API key needed)
ariadne-pmm fetch --seed "BeReal" --keyword "photo sharing" --top 5

# Run the pack on the app plus its top 5 competitors
ariadne-pmm run weakness_map --seed "BeReal" --keyword "photo sharing" --top 5

# Or name the apps yourself
ariadne-pmm run weakness_map --app "1111111111:Competitor A" --app "2222222222:Competitor B"
```

The app ID is the number in an App Store URL (`apps.apple.com/us/app/name/id1111111111`).
The report lands in `reports/`. Raw reviews, the label cache and snapshots stay in `data/`,
which is git-ignored so raw review text is never republished.

## Research packs

| Pack | Question | Deliverable |
|---|---|---|
| `weakness_map` | Where is each competitor losing users? | Battlecard per competitor |
| `messaging_miner` | What do happy users value, in their own words? | Praise themes with quotes, for messaging |

`weakness_map` reads 1-3 star reviews; `messaging_miner` reads 4-5 star reviews. A case study runs
the packs listed in its `packs.txt` (just `weakness_map` if there isn't one).

A pack is a YAML file in `ariadne_pmm/packs/`. To add one, copy `weakness_map.yaml`, change
the question, ratings and themes, and pass its path to `ariadne-pmm run`.

## Two labellers

| | `--tagger claude` (default) | `--tagger keywords` |
|---|---|---|
| Cost | A few cents per run, needs `ANTHROPIC_API_KEY` | Free, no key |
| How it labels | Reads each review for meaning | Counts keyword matches from the pack's rules |
| Accuracy | Higher | Lower: it matches words, not meaning, and leaves more in "other" |
| Repeatable | Yes, through the cache | Yes, always |

The report states which labeller was used. Start with `keywords` to see the shape of a market
for free, then use `claude` for numbers you plan to present.

```bash
ariadne-pmm run weakness_map --seed "BeReal" --keyword "photo sharing" --tagger keywords
```

## Small samples

A percentage on a handful of reviews mostly reflects who happened to write one. So each app is
checked before anything is labelled, and the report only claims what the sample supports:

| Reviews the pack can read | What the report shows |
|---|---|
| 0 | The app is left out, and the report says so |
| 1 to 9 | The reviews themselves, with no themes. They are not sent for labelling |
| 10 to 29 | Counts only ("4 of 17"), marked as directional |
| 30 or more | Full percentages |

The two cut-offs are set per pack (`min_reviews`, `min_sample`). `ariadne-pmm fetch` prints this
check for free, so you can see it before spending API credits.

## Checking the labels yourself

The keyword labeller is rough, so you can measure how rough. Label a random sample by hand, then
compare:

```bash
# 1. Draw 100 labelled reviews from a run. Your sheet has an empty human_theme column;
#    the tool's labels go to a separate key file so you label blind.
ariadne-pmm sample data/snapshots/weakness_map-2026-11-18.csv --n 100

# 2. Fill in human_theme for each review in data/accuracy/...-sheet.csv, then:
ariadne-pmm agree data/accuracy/weakness_map-2026-11-18-sheet.csv --out accuracy.md
```

The report gives overall agreement, precision and recall per theme, and the most common mix-ups.
The same seed always draws the same sample, so a second person can label the same reviews.

## Tracking a market over time

Re-run a study later and compare the two runs:

```bash
ariadne-pmm compare data/snapshots/weakness_map-2026-11-18.csv data/snapshots/weakness_map-2026-12-18.csv
```

It lists each theme's share before and after, and marks a change **likely real** only when both
runs have at least 30 reviews and the change is bigger than sample noise (two-proportion z-test,
about 95% confidence). For example: is Apple Music's redesign backlash fading, or just noise?

## Limits

- Reviews come from existing users with strong opinions. They say little about people who never
  downloaded the app.
- Apple's feed returns only the most recent ~500 reviews per country, and it's not always
  reliable. Sometimes it returns fewer, like 350 of Amazon Music's 500 on one run. Ariadne retries
  a failed page twice before giving up, and prints a note when an app comes back short.
- Competitor discovery is a heuristic built on App Store search. It can miss a competitor that
  doesn't use the same words, or include an app that only shares a keyword. Check the list.
- The output is a first draft for a marketer to edit, not finished positioning.

## Roadmap

- [x] First case studies: BeReal (test run) and Apple Music
- [x] Accuracy check tooling (`sample` and `agree`)
- [ ] Run the accuracy check: label 100 Apple Music reviews by hand
- [x] `messaging_miner` pack: what happy users say, in their words
- [x] Compare two runs over time (`compare`)
- [ ] Streamlit demo

## Development

```bash
ruff check . && ruff format --check . && pytest
```
