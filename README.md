# Housing Decision Simulator
**A financial simulator comparing two housing paths for a newly married couple in Muscle Shoals, AL starting November 2026.**

---

## What It Does

This program runs 1,000 versions of the next 15 years of your financial life — one for each option — and tells you which path leaves you with more money, how often, and by how much. Instead of one fixed prediction, it simulates thousands of slightly different futures (some where gas is expensive, some where repairs are cheap, some where the rental sits empty for a few months) and shows you the full range of outcomes.

---

## The Two Options

**Option A — Trailer First, Then Buy**
Live in a trailer on the parents' property for about 2 years to save money, then buy a permanent home. Lower upfront cost, but a long commute every day means higher gas bills for two cars. Builds zero equity during the trailer phase. Pays closing costs twice — once when buying the permanent home.

**Option B — Buy Now, Then Rent It**
Buy the $98,500 house immediately. Live in it for about 3 years while building equity and saving on gas (shorter commute). Then move out, let a tenant rent it, and use that rental income to help buy a second permanent home. End up owning two properties. Also pays closing costs twice — but the second purchase is partially funded by rental income already collected.

---

## What a Monte Carlo Simulation Is

Real life is unpredictable. Gas prices go up and down. Some months a repair bill is $80, some months it's $900. Sometimes a rental sits empty. A simple calculator ignores all of that and gives you one answer based on everything going perfectly as planned.

This simulator instead runs the full 15 years 1,000 separate times. Each run uses slightly different random numbers — a different gas price this month, a different repair bill that month — just like real life. The result is 1,000 different outcomes. You can then see: in the typical future, which option wins? What about the bad futures? What about the good ones? How often does Option B win — is it 60% of the time or 95%?

---

## What It Measures

- **Net worth** — cash in the bank plus all home equity, tracked every month for 15 years
- **Break-even month** — when Option B's net worth first pulls permanently ahead of Option A
- **Passive income** — monthly profit from the rental (rent collected minus mortgage minus repairs)
- **Goal achievement** — when passive income first hits $500/mo and stays there
- **Equity** — how much of each home is actually yours (value minus remaining loan)
- **Gas costs** — cumulative spending difference over 15 years between the two commutes

---

## How To Change the Numbers

Open `config.json` in this repo. Every setting is labeled clearly. Change any value, click commit, then go to the **Actions** tab and click **Run Workflow**. In about 60 seconds your updated PDF report and all 11 charts will be saved to the `results/` folder in this repo.

---

## Output Files (in `results/` folder after each run)

| File | What it is |
|---|---|
| `housing_analysis_report.pdf` | Full report with parameters, results tables, milestone snapshots, all charts, and analyst verdict |
| `chart01_networth.png` | 15-year net worth projection for both options with uncertainty bands |
| `chart02_nw_gap.png` | The gap between Option B and Option A over time |
| `chart03_passive_income.png` | Option B monthly passive income growth toward the $500/mo goal |
| `chart04_equity.png` | Equity comparison — 1 property vs 2 properties |
| `chart05_breakeven.png` | Distribution of when Option B overtakes Option A across all 1,000 runs |
| `chart06_goal.png` | Distribution of when the passive income goal is achieved |
| `chart07_gas.png` | Cumulative gas spending difference over 15 years |
| `chart08_spending.png` | Monthly spending breakdown for each option |
| `chart09_scenarios.png` | What happens under different income growth scenarios |
| `chart10_amortization.png` | House 1 mortgage breakdown — interest vs principal vs equity |
| `chart11_upfront.png` | Total upfront costs each option pays across its full lifecycle |

---

*Built with Python — numpy, matplotlib, reportlab. Runs automatically on GitHub Actions.*
