# A6: same results on real data

**PASS on 2026-10-21.** Exported and replayed inside the Data Core, the real-source pilot gives byte-identical results to the platform that produced it. All 15 checks pass.

## The baseline

The files of the 10 October 2026 pilot could not be found: not in git, on GitHub, on Aleks's machine or in Youcef's home folder. The team approved a replacement: one fresh real-source pilot run with today's platform, frozen, as the baseline for A6 and B4. This proves "the Core gives the same results as today" on real data. It does not compare with the 10 October result (build hash `415879f2…59e2`), which is no longer available.

| | |
|---|---|
| Captured | 2026-10-21, `python -m app.pilot --online --as-of 2026-10-21` |
| Produced by | platform `youcefjerbi/MuniQuant-Aluminium-Trading-Plattform` at commit `26a0bcd` (its `app/pilot.py` is unchanged since the 10 October pilot) |
| Content | 15 plants, 5 companies, 3 publishers (Alcoa, Norsk Hydro, Rio Tinto), 7 official pages, 2 capacity facts (Portland 358,000 t/year, Husnes 197,000 t/year), 4 ownership and operator links |
| Platform quality | WARN, 11 warnings (5 companies without identity locators, 6 pages without a publication date), no BLOCK or ERROR |
| Build hash | `878944013542732000b9efaa80b714d4aeb8e35abac9fa84506b165ca668695e` |
| Manifest | [a6/pilot-baseline-2026-10-21-manifest.json](a6/pilot-baseline-2026-10-21-manifest.json), SHA-256 `1466d814d3210f1134e2eab1dca89bba77928152928d54735ec6d42a28b4871f`: the database, the 7 page copies and the 3 output files |

The baseline files hold copies of third-party pages, so they are not in git. They are kept in `data/pilot-baseline-2026-10-21/` on the machine that captured them; a private copy should go to the team. The manifest above proves any copy is the same.

## Checks

| Check | Result | Detail |
|---|---|---|
| Pilot package passes the Core contract validator | pass | |
| Pilot package carries the recorded build hash | pass | `87894401…695e` |
| Frozen pilot bundle replays equivalently in the Core | pass | replay equivalent, same build hash |
| Frozen bundle package equals the pilot package | pass | |
| Pilot rows copied unchanged into the Core (counts, IDs, fingerprints) | pass | all 26 tables equal |
| Pilot database unchanged by the comparison | pass | SHA-256 `289b6847…bbdb0` before and after |
| Quality status and counts match the pilot | pass | WARN 11 |
| Core export is byte-identical to the pilot export | pass | both SHA-256 `abfc10ff…bd32` |
| Core export build hash equals the recorded pilot hash | pass | `87894401…695e` |
| Every record has the same fact IDs, values, units, dates and evidence fingerprints | pass | 0 field differences |
| Matching decisions are the same (candidates and reviews) | pass | 0 differences |
| Core frozen bundle replays equivalently | pass | replay equivalent, same build hash |
| Core frozen recipe equals the pilot recipe | pass | recipe hash `568cc60a…80305` |
| Core frozen bundle holds the same snapshot bytes | pass | 7 page copies |
| Pilot summary numbers match the Core's | pass | 15 plants, 5 companies, 3 publishers, 7 pages, 2 facts, 4 links |

The platform database keeps one column the Core does not define (`source_access.usage_scope`); all its values equal the column's default, so the import loses nothing.

## The frozen export made by the Core

The handover's frozen pilot export, made by the Core: `core-frozen-evidence.zip`, SHA-256 `360781328ebf8d86457221678a949bb4e665ea4fab48be957c3b825e116eb746`, build hash `87894401…695e`, recipe hash `568cc60a…80305`. A new freeze writes new archive timestamps, so its file hash changes; the build and recipe hashes do not. It also holds the page copies and stays out of git with the baseline.

## Run it again

From the repository root, with the baseline files in place:

```sh
python -m tools.compare_pilot --output data/a6-pilot-comparison-NEW
```

The defaults are the baseline: the tool checks the manifest's own fingerprint, every file against the manifest, then all 15 checks. It reports BLOCKED if a file is missing or differs, and DIFFERENT if the Core's result differs. B4 runs the same command on the Core database the split tool produces.

## B4: the same comparison after the split

**PASS on 2026-10-21.** The Workspace's split tool (DC1 step B3) split the baseline's `real-pilot.db` into a new Core
database and a new Workspace database: every Core row went to the Core unchanged (the pilot holds no lead-feed
material), and the pilot database's SHA-256 was the same before and after. The comparison then ran on that Core
database without copying anything:

```sh
python -m tools.compare_pilot --core-database SPLIT_CORE_DB --output data/b4-pilot-comparison-NEW
```

All 15 checks above pass on it, plus a 16th, "Core database unchanged by the comparison": the export is byte-identical
(`abfc10ff…bd32`), with build hash `87894401…695e`, recipe hash `568cc60a…80305`, the same 7 saved pages, matching
decisions and quality (WARN, 11). The saved pages the split copied for the Core are byte-identical to the baseline's.
