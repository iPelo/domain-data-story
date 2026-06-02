# [TOPIC] — A Data Story

> A rigorous end-to-end data analysis answering one sharp question, with reproducible pipeline, interactive dashboard, and a written report.

**Status:** 🚧 In development
**Live dashboard:** _coming_
**Writeup:** _coming_
**Tech:** Python · DuckDB · Polars · Streamlit · Quarto

---

## The Question

A data project is only as strong as the question it answers. Most portfolios stop at "what does the data show?" — that's not a question, that's a shrug. Spend real time framing yours.

**Weak:** "Analyzing Berlin rental data."
**Strong:** "After controlling for size, year, and district, what is the rent premium per 100m closer to a U-Bahn station — and has it grown since 2015?"

### Candidate topics (pick one, then sharpen it)

- [ ] **Deutsche Bahn delays** — are long-distance delays trending worse, which routes/hours drive it? (data.deutschebahn.com)
- [ ] **Berlin rental market** — proximity to transit vs. rent psm, controlling for the obvious (Berlin Open Data)
- [ ] **German electricity prices** — how much do wind/solar shifts drive intra-day volatility? (SMARD.de)
- [ ] **Bike-share usage** — what weather/event factors predict daily ridership? (MVG/BVG/Call a Bike data)
- [ ] **Bundesliga performance** — does xG-overperformance regress, and on what timescale? (FBRef / understat)

**Your question (write the final version here):**
_____________________________________________________
_____________________________________________________

### Hypotheses (write 2–3 testable ones before touching data)

1. _____________________________________________________
2. _____________________________________________________
3. _____________________________________________________

## Approach

1. **Frame** — sharp question, falsifiable hypotheses
2. **Collect** — scrape or download, document source + license
3. **Clean** — reproducible pipeline, handle real-world mess
4. **Explore** — visualize before modeling
5. **Analyze** — appropriate stats/modeling, **honest about limits**
6. **Communicate** — dashboard + a writeup that could change someone's mind

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Storage | DuckDB | SQL on local files, zero infra, very fast |
| Wrangling | Polars (heavy) + pandas (familiar) | Polars is the future, learn it here |
| Stats / ML | statsmodels + scikit-learn | The classics |
| Notebooks | Jupyter in DataSpell or VSCode | Either works |
| Dashboard | Streamlit (fast to build) | Free Streamlit Community Cloud |
| Report | Quarto | Publishes Markdown → HTML / PDF beautifully |
| Pkg manager | `uv` | Fast |

## Roadmap

### Phase 1 — Frame and collect (Week 1)
- [x] Finalize the question, write hypotheses **before seeing the data** — see `README.md`
- [x] Locate dataset, read its documentation, check license — `piebro/deutsche-bahn-data`, CC BY 4.0
- [x] Scrape or download (respect robots.txt, rate limit) — `bahn-download`, 12 monthly files for 2025
- [x] Write `docs/data_dictionary.md`: every column, type, meaning, gotchas

### Phase 2 — Clean (Week 2)
- [x] Pipeline as a sequence of DuckDB SQL files OR Polars functions — `sql/02`, `sql/03`
- [x] **Every step idempotent** — re-running produces identical output (`test_pipeline_is_idempotent`)
- [x] Quality assertions at each stage (row counts, null rates, key uniqueness) — `quality.py`
- [x] Handle the real mess: time zones, encoding, schema drift, missingness patterns

### Phase 3 — Explore (Week 3)
- [x] EDA notebook: at least 15 plots, each with a caption stating what it shows — `notebooks/01_eda.ipynb`
- [x] Look for surprises; let them refine your hypotheses — coverage break and long-distance split now drive Phase 4
- [x] **Document things that confused you and how you resolved them** — see `docs/eda_findings.md`

### Phase 4 — Analyze (Week 4)
Pick the right tool for the question:
- [ ] **Causal?** Draw a DAG, regression with controls, then sensitivity analysis (E-values, leave-one-out controls)
- [ ] **Predictive?** Train/test split with appropriate time/group splits, baseline + better model, feature importance, calibration check
- [x] **Descriptive?** Cohort/segment decomposition, trend tests, change-point detection — see `notebooks/02_analysis.ipynb` and `docs/analysis_findings.md`

- [x] State limitations honestly — coverage break, stop-level observations, no weather/strike/construction controls

### Phase 5 — Dashboard (Week 5)
- [ ] Streamlit app with 3–5 *well-chosen* views (not 17 charts)
- [ ] Filters that actually answer follow-up questions
- [ ] Deploy to Streamlit Community Cloud (free, GitHub integration)

### Phase 6 — Write it up (Week 6)
- [ ] 1500–2500 word post for your portfolio site (Quarto → static HTML)
- [ ] Structure: **Question** → **Why it matters** → **Data** → **Method** → **Findings** → **Limitations** → **What I'd do next**
- [ ] Include **the one chart that would change a skeptic's mind** — that's your headline
- [ ] Link repo and dashboard from the post

## Target Project Structure

```
domain-data-story/
├── README.md
├── pyproject.toml
├── data/
│   ├── raw/                 # gitignored
│   └── interim/
├── sql/
│   ├── 01_load.sql
│   ├── 02_clean.sql
│   └── 03_features.sql
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_analysis.ipynb
│   └── 03_post_figures.ipynb
├── src/
│   ├── ingest.py            # scraper / downloader
│   ├── pipeline.py          # orchestrates SQL transforms
│   └── plots.py             # reusable plotting
├── dashboard/
│   └── app.py               # Streamlit
├── docs/
│   ├── data_dictionary.md
│   ├── methodology.md
│   └── post.md              # the writeup
└── tests/
    └── test_pipeline.py     # data quality assertions
```

## What I'm trying to learn / demonstrate

- Asking a sharp, defensible question
- Real data-engineering: pipelines, quality, reproducibility
- Statistical and causal thinking, not just plotting
- Clear written communication — **the** differentiator for DS roles

## Anti-patterns to avoid

- Starting with the data, not a question
- Plotting 30 charts and calling it "exploration"
- Reporting accuracy without a baseline
- Hiding limitations
- A dashboard with no narrative

## Resources

- "The Effect" by Huntington-Klein — free online, causal inference for practitioners
- "Statistical Rethinking" by McElreath — Bayesian + causal mindset
- DuckDB tutorials (10 min and you're productive)
- Polars user guide
- "Storytelling with Data" by Cole Nussbaumer Knaflic

## License

MIT (data licenses noted per source)
