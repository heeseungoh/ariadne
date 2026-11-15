# Ariadne

**Customer evidence you can defend.**

In Greek myth, Ariadne gave Theseus a clew, a ball of thread, so he could find his way out of
the Labyrinth. It is where the English word "clue" comes from. Product marketing is a labyrinth
of ambiguous questions: where are competitors weak, what do users actually value, is the price
the problem? Ariadne is the thread: it turns customer reviews into positioning backed by
numbers you can trace to the reviews behind them.

It does this with **research packs**. A pack is one PMM question with a fixed recipe: which
reviews to read, a fixed list of themes, calculations done in code, and a finished deliverable.

> Status: early build. One pack works end to end. No case study or accuracy check has been
> run yet. See [Roadmap](#roadmap).

## How it works

1. **Find competitors.** Type one app. Ariadne searches the App Store with its name, its own
   description keywords and any keywords you add, then ranks what comes back by how many searches
   found it, whether it shares the genre, and its number of ratings. An app has to be found by
   at least two searches to count. It prints why each app made
   the list, so you can drop the ones that don't belong.
2. **Collect.** Pulls up to about 500 recent App Store reviews per app from Apple's public feed.
3. **Label.** Claude reads each review and assigns one theme from the pack's fixed list, plus
   the most telling quote.
4. **Count.** pandas computes every share as a count over a stated sample size. The AI never
   does arithmetic.
5. **Report.** Writes a markdown battlecard where each number is followed by the reviews
   behind it.

## Why not just ask Claude?

For a one-time look at a handful of reviews, ask Claude. Ariadne is for when you have to
defend the numbers to someone else.

| | Asking Claude in a chat | Ariadne |
|---|---|---|
| Data volume | Whatever you paste in | About 500 reviews per app, pulled automatically |
| Numbers | Estimated by reading | Counted in code, sample size shown |
| Traceability | A summary with a few quotes | Every share lists the review IDs behind it |
| Consistency | Themes shift between chats | Fixed theme list and a cache: same input, same output |
| Quotes | May be paraphrased | Discarded unless word for word in the review |
| Method | Depends on your prompt | The PMM question and recipe are built into the pack |

What it does not claim: the reading is done by Claude, so it is not smarter than a chat, and a
chat is better for follow-up questions.

## Quick start

```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=your-key

ariadne-pmm packs

# See who Ariadne picks as competitors (free, no API key needed)
ariadne-pmm discover "BeReal" --keyword "photo sharing" --top 5

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

A pack is a YAML file in `ariadne_pmm/packs/`. To add one, copy `weakness_map.yaml`, change
the question, ratings and themes, and pass its path to `ariadne-pmm run`.

## Limits

- Reviews come from existing users with strong opinions. They say little about people who never
  downloaded the app.
- Apple's feed returns only the most recent ~500 reviews per country.
- Competitor discovery is a heuristic built on App Store search. It can miss a competitor that
  doesn't use the same words, or include an app that only shares a keyword. Check the list.
- The output is a first draft for a marketer to edit, not finished positioning.

## Roadmap

- [ ] First case study on a real app category
- [ ] Accuracy check: agreement with 100 hand-labelled reviews
- [ ] `messaging_miner` pack: what happy users say, in their words
- [ ] Compare two snapshots over time
- [ ] Streamlit demo

## Development

```bash
ruff check . && ruff format --check . && pytest
```
