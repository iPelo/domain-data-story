# Analysis Findings

`notebooks/02_analysis.ipynb` uses descriptive decomposition rather than causal modeling. The dataset has a known coverage break and does not include controls for weather, strikes, construction, vehicle availability, or passenger volume.

## Method

- Use the stable 107-station panel for trend claims.
- Compare January and October 2025 to avoid the November/December coverage
  expansion.
- Decompose added estimated 6+ minute late stops by service segment, train type,
  station, hour of day, and route/service.
- Report cancellation separately from delay.
- Use contribution rankings alongside rate rankings.

## Core Findings

1. **Delays worsened materially on the stable panel.** Late share rises from
   January to October for both long-distance and other services.
2. **Long-distance trains are much later, but not the whole story.** ICE and IC
   have much higher late-share rates, while RE, S, and RB create many added late
   stops because of their high stop volume.
3. **The largest train-type contributors are RE, S, RB, ICE, and IC.** These are
   the first candidates for dashboard filters and writeup charts.
4. **The station contribution story is hub-driven.** Added late stops concentrate
   at major hubs including Stuttgart, München, Hamburg, Köln, Berlin, Dortmund,
   and Hannover.
5. **The time-window story is afternoon/evening.** The biggest added late-stop
   contribution is roughly 14:00-21:00, avoiding the low-volume overnight cells
   that looked extreme in EDA.
6. **Route examples need minimum-stop floors.** The route/service outlier list is
   sensitive to the stop-count threshold. Use at least a 1,000-stop floor for
   examples, and avoid presenting small service groups as system-level causes.
7. **Cancellation is not a delay proxy.** Cancellation-share changes are smaller
   and follow different patterns from late-share changes.

## Draft Headline

Use a stable-station trend chart as the headline:

> On the stable 107-station panel, Deutsche Bahn stop-level lateness worsened
> substantially from January to October 2025, with long-distance trains showing
> the highest late rates and high-volume regional/S-Bahn services contributing
> many of the added late stops.

## Dashboard Implications

Build 3-5 focused views:

- Stable-station monthly trend by long-distance versus other services.
- Train-type contribution ranking.
- Station contribution ranking.
- Hour-of-day contribution view.
- Route/service outliers with a configurable minimum-stop floor.

## Limitations To Keep In The Writeup

- The project scope is 2025 only. The headline trend compares January and
  October on the stable station panel, avoiding the November/December coverage
  expansion.
- Stop-level observations are not passenger-weighted.
- One delayed train contributes multiple delayed stop observations.
- No controls for weather, strikes, construction, vehicle availability, or
  passenger demand are included.
- The November/December station coverage expansion should not be interpreted as
  an operational performance shock.
