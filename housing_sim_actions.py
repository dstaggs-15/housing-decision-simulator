#!/usr/bin/env python3
"""
Housing Decision Simulator v2.1 — GitHub Actions Edition
Reads all parameters from config.json instead of interactive prompts.
Option A (Trailer on parents' property) vs Option B (House purchase)
Muscle Shoals, AL — Analysis starting Nov 2026
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                 Table, TableStyle, PageBreak, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# =============================================================================
# LOAD CONFIG
# =============================================================================

with open('config.json') as f:
    cfg = json.load(f)

# Simulation
MONTHS    = int(cfg['simulation']['months'])
MC_RUNS   = int(cfg['simulation']['mc_runs'])

# Income & savings
MONTHLY_INCOME = float(cfg['income_and_savings']['monthly_income'])
STARTING_CASH  = float(cfg['income_and_savings']['starting_cash'])

# Option B house
HOME_PRICE    = float(cfg['option_b_house']['home_price'])
DOWN_PCT      = float(cfg['option_b_house']['down_pct']) / 100
CLOSING_PCT   = float(cfg['option_b_house']['closing_pct']) / 100
MORTGAGE_APR  = float(cfg['option_b_house']['mortgage_apr']) / 100
MORTGAGE_TERM = int(cfg['option_b_house']['mortgage_term_months'])

DOWN_PAYMENT    = HOME_PRICE * DOWN_PCT
CLOSING_COSTS   = HOME_PRICE * CLOSING_PCT
TOTAL_UPFRONT   = DOWN_PAYMENT + CLOSING_COSTS
LOAN_AMOUNT     = HOME_PRICE - DOWN_PAYMENT
MONTHLY_RATE    = MORTGAGE_APR / 12
MONTHLY_PAYMENT = (LOAN_AMOUNT * MONTHLY_RATE /
                   (1 - (1 + MONTHLY_RATE) ** -MORTGAGE_TERM))

# Expenses
A_FIXED_INFLATING = float(cfg['monthly_expenses']['option_a']['fixed_base'])
A_GAS_BASE        = float(cfg['monthly_expenses']['option_a']['gas'])
A_REPAIR_MEAN     = float(cfg['monthly_expenses']['option_a']['repair_mean'])
A_REPAIR_STD      = float(cfg['monthly_expenses']['option_a']['repair_std'])

B_FIXED_INFLATING = float(cfg['monthly_expenses']['option_b']['fixed_base'])
B_GAS_BASE        = float(cfg['monthly_expenses']['option_b']['gas'])
B_REPAIR_MEAN     = float(cfg['monthly_expenses']['option_b']['repair_mean'])
B_REPAIR_STD      = float(cfg['monthly_expenses']['option_b']['repair_std'])
B_REPAIR_CAP      = float(cfg['monthly_expenses']['option_b']['repair_cap'])

# Rental income
RENTAL_START = int(cfg['rental_income']['rental_start_month'])
RENT_MIN     = float(cfg['rental_income']['rent_min'])
RENT_MAX     = float(cfg['rental_income']['rent_max'])
VACANCY_RATE = float(cfg['rental_income']['vacancy_rate_pct']) / 100

# Rates & growth
GAS_VOLATILITY       = float(cfg['rates_and_growth']['gas_volatility_pct']) / 100
ANNUAL_APPRECIATION  = float(cfg['rates_and_growth']['annual_appreciation_pct']) / 100
ANNUAL_INFLATION     = float(cfg['rates_and_growth']['annual_inflation_pct']) / 100
ANNUAL_INVEST_RETURN = float(cfg['rates_and_growth']['annual_invest_return_pct']) / 100

MONTHLY_APPRECIATION  = (1 + ANNUAL_APPRECIATION)  ** (1/12) - 1
MONTHLY_INFLATION     = (1 + ANNUAL_INFLATION)      ** (1/12) - 1
MONTHLY_INVEST_RETURN = (1 + ANNUAL_INVEST_RETURN)  ** (1/12) - 1

# Commute
HOURLY_TIME_VALUE       = float(cfg['commute']['hourly_time_value'])
EXTRA_COMMUTE_HRS_MONTH = float(cfg['commute']['extra_commute_hrs_per_month'])

# Print loaded config summary
print("\n" + "=" * 60)
print("  HOUSING DECISION SIMULATOR v2.1 — GitHub Actions Edition")
print("=" * 60)
print(f"\n  Config loaded:")
print(f"    Months:           {MONTHS}  ({MONTHS//12} years)")
print(f"    MC runs:          {MC_RUNS:,}")
print(f"    Monthly income:   ${MONTHLY_INCOME:,.0f}")
print(f"    Starting cash:    ${STARTING_CASH:,.0f}")
print(f"    Home price (B):   ${HOME_PRICE:,.0f}")
print(f"    Down payment:     ${DOWN_PAYMENT:,.0f}  ({DOWN_PCT*100:.1f}%)")
print(f"    Closing costs:    ${CLOSING_COSTS:,.0f}  ({CLOSING_PCT*100:.1f}%)")
print(f"    Total upfront:    ${TOTAL_UPFRONT:,.0f}")
print(f"    Loan amount:      ${LOAN_AMOUNT:,.0f}")
print(f"    Monthly payment:  ${MONTHLY_PAYMENT:.2f}")
print(f"    Cash after close: ${STARTING_CASH - TOTAL_UPFRONT:,.0f}")
print(f"    Rental starts:    Month {RENTAL_START}")
print(f"    Rent range:       ${RENT_MIN:.0f}–${RENT_MAX:.0f}/mo")
print(f"    Time value:       ${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo")

# =============================================================================
# OUTPUT DIRECTORIES
# =============================================================================
OUTPUT_DIR = "./outputs"
CHART_DIR  = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# =============================================================================
# VISUAL STYLE
# =============================================================================
plt.rcParams.update({
    'figure.facecolor': '#FAFAFA',
    'axes.facecolor':   '#F5F5F5',
    'axes.grid':        True,
    'grid.color':       '#DDDDDD',
    'grid.linestyle':   '-',
    'grid.linewidth':   0.5,
    'font.family':      'DejaVu Sans',
    'axes.spines.top':  False,
    'axes.spines.right':False,
})

COL_A    = '#3B5FA0'
COL_B    = '#2E8B57'
COL_WARN = '#C0392B'
COL_ACC  = '#E67E22'
DOLLAR   = FuncFormatter(lambda x, _: f'${x:,.0f}')
KDOLLAR  = FuncFormatter(lambda x, _: f'${x/1000:.0f}k')


# =============================================================================
# AMORTIZATION
# =============================================================================

def amortize_one_month(balance, monthly_rate, payment):
    interest  = balance * monthly_rate
    principal = min(payment - interest, balance)
    new_bal   = max(0.0, balance - principal)
    return interest, principal, new_bal


# =============================================================================
# CORE SIMULATION (SINGLE PATH)
# =============================================================================

def run_one_path(use_time_value=False, income_growth_annual=0.0):
    a_cash       = STARTING_CASH
    b_cash       = STARTING_CASH - TOTAL_UPFRONT
    b_loan_bal   = LOAN_AMOUNT
    home_value   = HOME_PRICE
    monthly_inc  = MONTHLY_INCOME
    inc_growth   = (1 + income_growth_annual) ** (1/12) - 1

    out = {k: [] for k in [
        'a_cash', 'a_nw',
        'b_cash', 'b_equity', 'b_nw',
        'a_expenses', 'b_expenses',
        'a_gas', 'b_gas',
        'rental', 'b_loan_bal', 'home_value',
        'a_monthly_savings', 'b_monthly_savings',
    ]}

    for month in range(1, MONTHS + 1):
        if month > 1:
            monthly_inc *= (1 + inc_growth)

        inf = (1 + MONTHLY_INFLATION) ** (month - 1)

        a_gas_inf = A_GAS_BASE * inf
        b_gas_inf = B_GAS_BASE * inf

        shock = 1 + np.random.uniform(-GAS_VOLATILITY, GAS_VOLATILITY)
        a_gas = a_gas_inf * shock
        b_gas = b_gas_inf * shock

        a_repair = max(0, np.random.normal(A_REPAIR_MEAN * inf, A_REPAIR_STD * inf))
        b_repair = min(max(0, np.random.normal(B_REPAIR_MEAN * inf, B_REPAIR_STD * inf)),
                       B_REPAIR_CAP)

        a_exp = A_FIXED_INFLATING * inf + a_gas + a_repair
        if use_time_value:
            a_exp += HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH

        b_exp = MONTHLY_PAYMENT + B_FIXED_INFLATING * inf + b_gas + b_repair

        rent = 0.0
        if month >= RENTAL_START:
            if np.random.rand() > VACANCY_RATE:
                rent_base = np.random.uniform(RENT_MIN, RENT_MAX)
                rent = rent_base * (1 + MONTHLY_INFLATION) ** (month - RENTAL_START)

        a_flow = monthly_inc - a_exp
        b_flow = monthly_inc - b_exp + rent

        a_cash += a_flow
        b_cash += b_flow

        a_cash *= (1 + MONTHLY_INVEST_RETURN)
        b_cash *= (1 + MONTHLY_INVEST_RETURN)

        _, principal_paid, b_loan_bal = amortize_one_month(b_loan_bal, MONTHLY_RATE, MONTHLY_PAYMENT)

        home_value *= (1 + MONTHLY_APPRECIATION)
        equity = home_value - b_loan_bal

        a_nw = a_cash
        b_nw = b_cash + equity

        out['a_cash'].append(a_cash)
        out['a_nw'].append(a_nw)
        out['b_cash'].append(b_cash)
        out['b_equity'].append(equity)
        out['b_nw'].append(b_nw)
        out['a_expenses'].append(a_exp)
        out['b_expenses'].append(b_exp)
        out['a_gas'].append(a_gas)
        out['b_gas'].append(b_gas)
        out['rental'].append(rent)
        out['b_loan_bal'].append(b_loan_bal)
        out['home_value'].append(home_value)
        out['a_monthly_savings'].append(a_flow)
        out['b_monthly_savings'].append(b_flow)

    return out


# =============================================================================
# MONTE CARLO ENGINE
# =============================================================================

def monte_carlo(use_time_value=False, income_growth_annual=0.0, label=""):
    all_a_nw     = np.zeros((MC_RUNS, MONTHS))
    all_b_nw     = np.zeros((MC_RUNS, MONTHS))
    all_a_cash   = np.zeros((MC_RUNS, MONTHS))
    all_b_cash   = np.zeros((MC_RUNS, MONTHS))
    all_b_equity = np.zeros((MC_RUNS, MONTHS))
    all_rental   = np.zeros((MC_RUNS, MONTHS))
    be_months    = []

    for i in range(MC_RUNS):
        p = run_one_path(use_time_value, income_growth_annual)
        all_a_nw[i]     = p['a_nw']
        all_b_nw[i]     = p['b_nw']
        all_a_cash[i]   = p['a_cash']
        all_b_cash[i]   = p['b_cash']
        all_b_equity[i] = p['b_equity']
        all_rental[i]   = p['rental']

        diff = np.array(p['b_nw']) - np.array(p['a_nw'])
        be   = None
        for j in range(len(diff) - 2):
            if diff[j] > 0 and diff[j+1] > 0 and diff[j+2] > 0:
                be = j + 1
                break
        be_months.append(be if be is not None else MONTHS + 1)

    within = [b for b in be_months if b <= MONTHS]
    be_pct = len(within) / MC_RUNS * 100
    be_med = float(np.median(within)) if within else float('nan')

    return {
        'label':         label,
        'a_nw_mean':     np.mean(all_a_nw, axis=0),
        'a_nw_p10':      np.percentile(all_a_nw, 10, axis=0),
        'a_nw_p90':      np.percentile(all_a_nw, 90, axis=0),
        'b_nw_mean':     np.mean(all_b_nw, axis=0),
        'b_nw_p10':      np.percentile(all_b_nw, 10, axis=0),
        'b_nw_p90':      np.percentile(all_b_nw, 90, axis=0),
        'a_cash_mean':   np.mean(all_a_cash, axis=0),
        'b_cash_mean':   np.mean(all_b_cash, axis=0),
        'b_equity_mean': np.mean(all_b_equity, axis=0),
        'rental_mean':   np.mean(all_rental, axis=0),
        'be_months':     be_months,
        'be_median':     be_med,
        'be_pct':        be_pct,
        'final_a_nw':    float(np.mean(all_a_nw[:, -1])),
        'final_b_nw':    float(np.mean(all_b_nw[:, -1])),
        'final_a_p10':   float(np.percentile(all_a_nw[:, -1], 10)),
        'final_b_p10':   float(np.percentile(all_b_nw[:, -1], 10)),
        'final_a_p90':   float(np.percentile(all_a_nw[:, -1], 90)),
        'final_b_p90':   float(np.percentile(all_b_nw[:, -1], 90)),
    }


# =============================================================================
# CHART HELPERS
# =============================================================================

def months_to_date(m):
    year  = 2026 + (m - 1) // 12
    month = ((10 + m - 1) % 12) + 1
    names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return f"{names[month-1]} {year}"

X        = np.arange(1, MONTHS + 1)
X_LABELS = [months_to_date(m) if m % 12 == 1 else '' for m in X]


# =============================================================================
# CHART 1 — NET WORTH PROJECTION
# =============================================================================

def chart_networth(base, tv):
    tv_label = f'${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo'
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    fig.suptitle(f'Net Worth Projection — Option A (Trailer) vs Option B (${HOME_PRICE:,.0f} House)',
                 fontsize=14, fontweight='bold', y=1.01)

    for ax, res, title in zip(axes,
                               [base, tv],
                               ['Without Time Value of Commute',
                                f'With Time Value of Commute ({tv_label})']):
        ax.fill_between(X, res['a_nw_p10'], res['a_nw_p90'], alpha=0.18, color=COL_A)
        ax.fill_between(X, res['b_nw_p10'], res['b_nw_p90'], alpha=0.18, color=COL_B)
        ax.plot(X, res['a_nw_mean'], color=COL_A, lw=2.5, label='Option A (Trailer)')
        ax.plot(X, res['b_nw_mean'], color=COL_B, lw=2.5, label='Option B (House)')

        ax.yaxis.set_major_formatter(KDOLLAR)
        ax.set_xlabel('Month (from Nov 2026)', fontsize=10)
        ax.set_ylabel('Net Worth', fontsize=10)
        ax.set_title(title, fontsize=11)
        ax.legend(fontsize=9)

        diff = res['b_nw_mean'] - res['a_nw_mean']
        crossings = [i for i in range(1, len(diff)) if diff[i-1] <= 0 < diff[i]]
        if crossings:
            be = crossings[0]
            ax.axvline(be, color=COL_ACC, lw=1.5, linestyle='--', alpha=0.8)
            ax.text(be + 0.5, ax.get_ylim()[0] * 0.98,
                    f'~Month {be}\n({months_to_date(be)})',
                    color=COL_ACC, fontsize=7.5, va='bottom')
            ax.fill_between(X[be:], res['a_nw_mean'][be:], res['b_nw_mean'][be:],
                            where=res['b_nw_mean'][be:] >= res['a_nw_mean'][be:],
                            alpha=0.10, color=COL_B)

        ax.annotate(f"A: ${res['final_a_nw']:,.0f}",
                    xy=(MONTHS, res['a_nw_mean'][-1]), xytext=(-35, -15),
                    textcoords='offset points', color=COL_A, fontsize=8, fontweight='bold')
        ax.annotate(f"B: ${res['final_b_nw']:,.0f}",
                    xy=(MONTHS, res['b_nw_mean'][-1]), xytext=(-35, 8),
                    textcoords='offset points', color=COL_B, fontsize=8, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart1_networth.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 2 — CASH vs EQUITY BREAKDOWN
# =============================================================================

def chart_cash_equity(base):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.stackplot(X,
                 base['b_cash_mean'],
                 base['b_equity_mean'],
                 labels=['Cash (Option B)', 'Home Equity (appreciation + paydown)'],
                 colors=[COL_B, '#8FBC8F'],
                 alpha=0.85)
    ax.plot(X, base['a_nw_mean'], color=COL_A, lw=2.5, linestyle='--',
            label='Option A Net Worth (for reference)')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('$', fontsize=10)
    ax.set_title('Option B Composition: Cash + Equity vs Option A Cash', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart2_cash_equity.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 3 — CUMULATIVE GAS COST
# =============================================================================

def chart_gas():
    a_gas_cum, b_gas_cum = [], []
    tot_a, tot_b = 0, 0
    for m in range(1, MONTHS + 1):
        inf = (1 + MONTHLY_INFLATION) ** (m - 1)
        tot_a += A_GAS_BASE * inf
        tot_b += B_GAS_BASE * inf
        a_gas_cum.append(tot_a)
        b_gas_cum.append(tot_b)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(X, a_gas_cum, color=COL_A, lw=2.5,
            label=f'Option A — ${A_GAS_BASE:.0f}/mo (long commute)')
    ax.plot(X, b_gas_cum, color=COL_B, lw=2.5,
            label=f'Option B — ${B_GAS_BASE:.0f}/mo (shorter commute)')
    ax.fill_between(X, b_gas_cum, a_gas_cum, alpha=0.15, color=COL_WARN,
                    label=f'Gas savings choosing B: ${a_gas_cum[-1]-b_gas_cum[-1]:,.0f} total')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Cumulative Gas Spend ($)', fontsize=10)
    ax.set_title('Cumulative Gas Cost — Two-Car Households', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.text(MONTHS * 0.5, (a_gas_cum[-1] + b_gas_cum[-1]) / 2,
            f'${a_gas_cum[-1]-b_gas_cum[-1]:,.0f}\nsaved\nby B',
            ha='center', va='center', fontsize=11, color=COL_WARN, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart3_gas.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 4 — BREAK-EVEN DISTRIBUTION
# =============================================================================

def chart_breakeven(base, tv):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    tv_label = f'${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo'
    for ax, res, title in zip(axes, [base, tv],
                               ['Without Time Value',
                                f'With Time Value ({tv_label})']):
        valid = [b for b in res['be_months'] if b <= MONTHS]
        never = sum(b > MONTHS for b in res['be_months'])
        if valid:
            ax.hist(valid, bins=range(1, MONTHS + 2, 3), color=COL_B, edgecolor='white',
                    alpha=0.85, density=False)
        ax.axvline(res['be_median'], color=COL_ACC, lw=2, linestyle='--',
                   label=f'Median: Month {int(res["be_median"]) if not np.isnan(res["be_median"]) else "N/A"}')
        ax.set_xlabel('Month B Overtakes A (net worth)', fontsize=10)
        ax.set_ylabel('Number of Simulations', fontsize=10)
        ax.set_title(f'{title}\n{res["be_pct"]:.0f}% of paths: B wins within horizon\n'
                     f'({never} paths: B never overtakes)', fontsize=10, fontweight='bold')
        ax.legend(fontsize=9)
        ax.set_xlim(1, MONTHS)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart4_breakeven.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 5 — SCENARIO COMPARISON (income growth)
# =============================================================================

def chart_scenarios(scenarios):
    fig, ax = plt.subplots(figsize=(12, 6))
    cmap_a = plt.cm.Blues(np.linspace(0.5, 0.9, len(scenarios)))
    cmap_b = plt.cm.Greens(np.linspace(0.5, 0.9, len(scenarios)))

    for i, (label, res) in enumerate(scenarios):
        ax.plot(X, res['a_nw_mean'], color=cmap_a[i], lw=2, linestyle='--',
                label=f'A — {label}')
        ax.plot(X, res['b_nw_mean'], color=cmap_b[i], lw=2,
                label=f'B — {label}')

    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Mean Net Worth', fontsize=10)
    ax.set_title('Net Worth Scenarios — Income Growth Sensitivity\n'
                 '(dashed = Option A, solid = Option B)', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart5_scenarios.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 6 — OPPORTUNITY COST BREAKDOWN
# =============================================================================

def chart_opportunity_cost(base):
    months = np.arange(1, MONTHS + 1)

    gas_savings_cum = []
    gs = 0
    for m in range(1, MONTHS + 1):
        inf = (1 + MONTHLY_INFLATION) ** (m - 1)
        gs += (A_GAS_BASE - B_GAS_BASE) * inf
        gas_savings_cum.append(gs)

    rent_cum   = np.cumsum(base['rental_mean'])
    equity_cum = base['b_equity_mean']
    dp_invested = TOTAL_UPFRONT * ((1 + MONTHLY_INVEST_RETURN) ** months - 1)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(months,
                 gas_savings_cum,
                 rent_cum,
                 labels=['Gas savings (B over A)', 'Cumulative rental income (B)'],
                 colors=[COL_ACC, '#6495ED'],
                 alpha=0.8)
    ax.plot(months, equity_cum, color=COL_B, lw=2.5,
            label=f'Home equity ({ANNUAL_APPRECIATION*100:.0f}%/yr appreciation)')
    ax.plot(months, dp_invested, color=COL_WARN, lw=2, linestyle=':',
            label=f'Down payment if kept invested by A (${TOTAL_UPFRONT:,.0f} @ {ANNUAL_INVEST_RETURN*100:.1f}%)')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Cumulative $ Value', fontsize=10)
    ax.set_title('Opportunity Cost Breakdown — Where Option B Builds Its Advantage',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart6_opportunity_cost.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 7 — MONTHLY EXPENSE COMPOSITION (uses actual config values)
# =============================================================================

def chart_spending():
    # Option A baseline spending (month 1, no inflation)
    a_mortgage   = 0
    a_gas        = A_GAS_BASE
    a_fixed_rest = A_FIXED_INFLATING  # groceries, utilities, insurance, etc.
    a_repairs    = A_REPAIR_MEAN
    a_total_exp  = a_fixed_rest + a_gas + a_repairs
    a_savings    = max(0, MONTHLY_INCOME - a_total_exp)

    # Option B baseline spending (month 1, no inflation)
    b_mortgage   = MONTHLY_PAYMENT
    b_gas        = B_GAS_BASE
    b_fixed_rest = B_FIXED_INFLATING
    b_repairs    = B_REPAIR_MEAN
    b_total_exp  = b_mortgage + b_fixed_rest + b_gas + b_repairs
    b_savings    = max(0, MONTHLY_INCOME - b_total_exp)

    a_items = {
        'Savings':         a_savings,
        'Fixed expenses':  a_fixed_rest,
        'Gas (2 cars)':    a_gas,
        'Repairs (avg)':   a_repairs,
    }
    b_items = {
        'Savings':         b_savings,
        'Fixed expenses':  b_fixed_rest,
        'Mortgage':        b_mortgage,
        'Gas (2 cars)':    b_gas,
        'Repairs (avg)':   b_repairs,
    }

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle('Monthly Spending Breakdown — Baseline Month 1', fontsize=13, fontweight='bold')
    pal = plt.cm.tab20.colors

    for ax, items, title in zip(axes, [a_items, b_items],
                                 ['Option A (Trailer)', f'Option B (${HOME_PRICE:,.0f} House)']):
        labels   = list(items.keys())
        vals     = list(items.values())
        explode  = [0.03] * len(vals)
        wedges, texts, autos = ax.pie(
            vals, labels=None, autopct='%1.0f%%',
            startangle=140, explode=explode, colors=pal[:len(vals)],
            pctdistance=0.75, wedgeprops={'linewidth': 0.5, 'edgecolor': 'white'}
        )
        for t in autos:
            t.set_fontsize(7)
        ax.legend(wedges,
                  [f'{l}: ${v:,.0f}' for l, v in zip(labels, vals)],
                  loc='lower center', fontsize=7,
                  bbox_to_anchor=(0.5, -0.35), ncol=2)
        ax.set_title(f'{title}\nTotal: ${sum(vals):,.0f}/mo', fontsize=10, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart7_spending.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 8 — AMORTIZATION SCHEDULE
# =============================================================================

def chart_amortization():
    balances, principals, interests, equities, home_vals = [], [], [], [], []
    bal = LOAN_AMOUNT
    hv  = HOME_PRICE
    for m in range(1, MONTHS + 1):
        interest, principal, bal = amortize_one_month(bal, MONTHLY_RATE, MONTHLY_PAYMENT)
        hv *= (1 + MONTHLY_APPRECIATION)
        equity = hv - bal
        balances.append(bal)
        principals.append(principal)
        interests.append(interest)
        equities.append(equity)
        home_vals.append(hv)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    ax.bar(X, interests,  color=COL_WARN, label='Interest', alpha=0.8)
    ax.bar(X, principals, bottom=interests, color=COL_B, label='Principal', alpha=0.8)
    ax.yaxis.set_major_formatter(DOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Monthly Payment Breakdown', fontsize=10)
    ax.set_title(f'Mortgage Payment: ${MONTHLY_PAYMENT:.2f}/mo\n'
                 f'Month 1: ${interests[0]:.0f} interest / ${principals[0]:.0f} principal',
                 fontsize=10, fontweight='bold')
    ax.legend(fontsize=9)
    ax.text(MONTHS * 0.6, MONTHLY_PAYMENT * 0.6,
            f'Month {MONTHS}:\n${interests[-1]:.0f} interest\n${principals[-1]:.0f} principal',
            fontsize=8, color='black')

    ax = axes[1]
    ax.fill_between(X, 0, equities, alpha=0.4, color=COL_B, label='Equity')
    ax.fill_between(X, equities, home_vals, alpha=0.3, color=COL_WARN, label='Remaining loan')
    ax.plot(X, home_vals, color=COL_B,    lw=2, label=f'Home value ({ANNUAL_APPRECIATION*100:.0f}%/yr appreciation)')
    ax.plot(X, equities,  color=COL_ACC,  lw=2, label='Your equity')
    ax.plot(X, balances,  color=COL_WARN, lw=1.5, linestyle='--', label='Loan balance')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('$', fontsize=10)
    ax.set_title(f'Equity Accumulation (Month 1\u219260)\n'
                 f'Equity at Month {MONTHS}: ${equities[-1]:,.0f}',
                 fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart8_amortization.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# PDF REPORT GENERATOR
# =============================================================================

def build_pdf(base, tv, scenarios, chart_paths):
    path = os.path.join(OUTPUT_DIR, 'housing_analysis_report.pdf')
    doc  = SimpleDocTemplate(path, pagesize=letter,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles = getSampleStyleSheet()
    S = {
        'title':   ParagraphStyle('t', parent=styles['Title'],
                                  fontSize=20, textColor=colors.HexColor('#1A3A5C'),
                                  spaceAfter=6),
        'h1':      ParagraphStyle('h1', parent=styles['Heading1'],
                                  fontSize=14, textColor=colors.HexColor('#2E5D9A'),
                                  spaceBefore=14, spaceAfter=4),
        'h2':      ParagraphStyle('h2', parent=styles['Heading2'],
                                  fontSize=11, textColor=colors.HexColor('#2E8B57'),
                                  spaceBefore=8, spaceAfter=2),
        'body':    ParagraphStyle('b', parent=styles['Normal'],
                                  fontSize=9.5, leading=14, spaceAfter=6),
        'bullet':  ParagraphStyle('bl', parent=styles['Normal'],
                                  fontSize=9, leading=13, leftIndent=14,
                                  bulletIndent=0, spaceAfter=3),
        'warn':    ParagraphStyle('w', parent=styles['Normal'],
                                  fontSize=9.5, textColor=colors.HexColor('#C0392B'),
                                  leading=13, spaceAfter=4),
        'green':   ParagraphStyle('g', parent=styles['Normal'],
                                  fontSize=9.5, textColor=colors.HexColor('#1E6B3A'),
                                  leading=13, spaceAfter=4),
        'caption': ParagraphStyle('c', parent=styles['Normal'],
                                  fontSize=8, textColor=colors.gray,
                                  leading=11, spaceAfter=8, alignment=1),
    }

    def HR():
        return HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#CCCCCC'),
                          spaceAfter=8, spaceBefore=4)

    def img(p, w=6.5):
        return Image(p, width=w*inch, height=w*inch * 0.48)

    story = []

    story += [
        Paragraph('Housing Decision Analysis', S['title']),
        Paragraph(f'Option A: Trailer on Parents\' Property  vs  '
                  f'Option B: ${HOME_PRICE:,.0f} House Purchase', S['h2']),
        Paragraph(f'Muscle Shoals, AL  |  Monte Carlo Simulation ({MC_RUNS:,} runs)  |  '
                  f'Generated {datetime.now().strftime("%B %d, %Y")}', S['body']),
        HR(),
        Spacer(1, 4),
    ]

    story.append(Paragraph('Simulation Parameters', S['h1']))
    param_data = [
        ['Parameter', 'Value', 'Note'],
        ['Combined take-home', f'${MONTHLY_INCOME:,.0f}/mo', 'Both jobs, after tax'],
        ['Starting savings', f'${STARTING_CASH:,.0f}', 'At wedding, Nov 2026'],
        ['Home price (Option B)', f'${HOME_PRICE:,.0f}', ''],
        ['Down payment', f'${DOWN_PAYMENT:,.0f}', f'{DOWN_PCT*100:.1f}%'],
        ['Closing costs', f'${CLOSING_COSTS:,.0f}', f'{CLOSING_PCT*100:.1f}%'],
        ['Total upfront cost', f'${TOTAL_UPFRONT:,.0f}', ''],
        ['Cash after closing', f'${STARTING_CASH - TOTAL_UPFRONT:,.0f}', 'Remaining cushion'],
        ['Loan amount', f'${LOAN_AMOUNT:,.0f}', f'{MORTGAGE_TERM//12}-yr, {MORTGAGE_APR*100:.1f}% fixed'],
        ['Monthly mortgage', f'${MONTHLY_PAYMENT:.2f}', 'Fixed — does not inflate'],
        ['Option A gas', f'${A_GAS_BASE:.0f}/mo', 'Long commute, 2 cars'],
        ['Option B gas', f'${B_GAS_BASE:.0f}/mo', 'Shorter commute, 2 cars'],
        ['Rental income (B)', f'${RENT_MIN:.0f}–${RENT_MAX:.0f}/mo',
         f'Starts month {RENTAL_START}, {VACANCY_RATE*100:.0f}% vacancy'],
        ['Home appreciation', f'{ANNUAL_APPRECIATION*100:.1f}%/yr', 'Conservative'],
        ['Expense inflation', f'{ANNUAL_INFLATION*100:.1f}%/yr', ''],
        ['Invest return on cash', f'{ANNUAL_INVEST_RETURN*100:.1f}%/yr', 'HYSA / fund'],
        ['Simulation length', f'{MONTHS} months ({MONTHS//12} yrs)', ''],
        ['Monte Carlo runs', f'{MC_RUNS:,}', 'P10/P90 uncertainty bands'],
    ]
    ts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E5D9A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#EEF4FF')]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ])
    story.append(Table(param_data, colWidths=[2.2*inch, 1.8*inch, 3.0*inch], style=ts))
    story.append(Spacer(1, 8))
    story.append(PageBreak())

    story.append(Paragraph('Key Results Summary', S['h1']))
    def fmt(v): return f'${v:,.0f}'

    results_data = [
        ['Metric', 'Option A (Trailer)', 'Option B (House)', 'Winner'],
        ['Mean net worth — final month (no time value)',
         fmt(base['final_a_nw']), fmt(base['final_b_nw']),
         'B' if base['final_b_nw'] > base['final_a_nw'] else 'A'],
        ['Mean net worth — final month (with time value)',
         fmt(tv['final_a_nw']), fmt(tv['final_b_nw']),
         'B' if tv['final_b_nw'] > tv['final_a_nw'] else 'A'],
        ['10th percentile net worth (no time value)',
         fmt(base['final_a_p10']), fmt(base['final_b_p10']),
         'B' if base['final_b_p10'] > base['final_a_p10'] else 'A'],
        ['90th percentile net worth (no time value)',
         fmt(base['final_a_p90']), fmt(base['final_b_p90']),
         'B' if base['final_b_p90'] > base['final_a_p90'] else 'A'],
        ['Break-even month (median, no time value)',
         '—', f'Month {int(base["be_median"]) if not np.isnan(base["be_median"]) else "N/A"}', '—'],
        ['% simulations: B wins within horizon (no TV)',
         '—', f'{base["be_pct"]:.0f}%', '—'],
        ['Break-even month (median, with time value)',
         '—', f'Month {int(tv["be_median"]) if not np.isnan(tv["be_median"]) else "N/A"}', '—'],
        ['% simulations: B wins within horizon (with TV)',
         '—', f'{tv["be_pct"]:.0f}%', '—'],
        ['Cumulative gas cost (A vs B)',
         f'~${A_GAS_BASE*MONTHS:,}', f'~${B_GAS_BASE*MONTHS:,}',
         f'B saves ${(A_GAS_BASE-B_GAS_BASE)*MONTHS:,}'],
        ['Home equity at final month (mean)', '—',
         fmt(base['b_equity_mean'][-1]), 'B'],
        ['Mean rental income earned (lifetime)', '—',
         fmt(float(np.sum(base['rental_mean']))), 'B'],
    ]
    ts2 = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E5D9A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#EEF4FF')]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TEXTCOLOR', (3,1), (3,-1), colors.HexColor('#1E6B3A')),
        ('FONTNAME', (3,1), (3,-1), 'Helvetica-Bold'),
    ])
    story.append(Table(results_data, colWidths=[2.9*inch, 1.5*inch, 1.5*inch, 1.1*inch], style=ts2))
    story.append(Spacer(1, 10))

    captions = [
        f'Chart 1: Net Worth Projection — {MONTHS}-month horizon with Monte Carlo P10–P90 bands. '
        f'Left: no time value. Right: includes ${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo commute opportunity cost.',
        'Chart 2: Option B component breakdown — cash balance plus home equity. '
        'Option A net worth shown dashed for comparison.',
        f'Chart 3: Cumulative gas expenditure. Option A pays ${A_GAS_BASE:.0f}/mo vs '
        f'Option B ${B_GAS_BASE:.0f}/mo — the difference compounds over the full horizon.',
        'Chart 4: Distribution of break-even month across all simulation paths.',
        'Chart 5: Scenario analysis — net worth trajectories under different income growth assumptions.',
        'Chart 6: Opportunity cost decomposition — where Option B\'s long-run advantage originates.',
        'Chart 7: Monthly spending composition using actual config values.',
        f'Chart 8: Mortgage amortization detail for ${HOME_PRICE:,.0f} home at '
        f'{MORTGAGE_APR*100:.1f}% over {MORTGAGE_TERM//12} years.',
    ]
    for cpath, caption in zip(chart_paths, captions):
        story.append(img(cpath, w=6.8))
        story.append(Paragraph(caption, S['caption']))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    story.append(Paragraph('Analyst Verdict', S['h1']))
    winner_base = 'B' if base['final_b_nw'] > base['final_a_nw'] else 'A'
    winner_tv   = 'B' if tv['final_b_nw'] > tv['final_a_nw'] else 'A'
    margin_base = abs(base['final_b_nw'] - base['final_a_nw'])
    margin_tv   = abs(tv['final_b_nw'] - tv['final_a_nw'])
    story += [
        Paragraph(
            f'Base scenario (no time value): Option {winner_base} leads by ${margin_base:,.0f} '
            f'at month {MONTHS}. {base["be_pct"]:.0f}% of simulation paths show B overtaking A '
            f'within the {MONTHS}-month horizon.',
            S['body']),
        Paragraph(
            f'With time value of commute (${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo): '
            f'Option {winner_tv} leads by ${margin_tv:,.0f}. {tv["be_pct"]:.0f}% of paths show B winning.',
            S['body']),
        Paragraph('Key risk factors to monitor:', S['h2']),
        Paragraph(f'• Repair spike in years 1–2 before rental income starts (month {RENTAL_START}). '
                  f'Cash cushion after closing: ${STARTING_CASH - TOTAL_UPFRONT:,.0f}.', S['bullet']),
        Paragraph(f'• Vacancy risk on rental (modeled at {VACANCY_RATE*100:.0f}%). '
                  f'Vetting tenants carefully is critical.', S['bullet']),
        Paragraph('• Income disruption — Option A\'s lower fixed costs provide more short-term flexibility '
                  'in a job-loss scenario.', S['bullet']),
        HR(),
        Paragraph(f'Simulation generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}  |  '
                  f'{MC_RUNS:,} Monte Carlo paths  |  {MONTHS}-month horizon', S['caption']),
    ]

    doc.build(story)
    return path


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print(f"\n[1/6] Running base simulation (no time value)...")
    base = monte_carlo(use_time_value=False, income_growth_annual=0.0, label='Base (no time value)')

    print(f"[2/6] Running time-value simulation (${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo commute cost)...")
    tv = monte_carlo(use_time_value=True, income_growth_annual=0.0, label='With time value')

    print("[3/6] Running income growth scenarios...")
    scenarios = []
    for growth, lbl in [(0.0, 'No raises'), (0.02, '2%/yr raises'), (0.04, '4%/yr raises (CT cert)')]:
        s = monte_carlo(use_time_value=False, income_growth_annual=growth, label=lbl)
        scenarios.append((lbl, s))

    print("[4/6] Generating charts...")
    c1 = chart_networth(base, tv)
    c2 = chart_cash_equity(base)
    c3 = chart_gas()
    c4 = chart_breakeven(base, tv)
    c5 = chart_scenarios(scenarios)
    c6 = chart_opportunity_cost(base)
    c7 = chart_spending()
    c8 = chart_amortization()
    charts = [c1, c2, c3, c4, c5, c6, c7, c8]

    print("[5/6] Building PDF report...")
    pdf_path = build_pdf(base, tv, scenarios, charts)

    print("[6/6] Done.\n")
    print("=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n  BASE SCENARIO (no time value of commute):")
    print(f"    Option A final net worth (mean): ${base['final_a_nw']:>10,.0f}")
    print(f"    Option B final net worth (mean): ${base['final_b_nw']:>10,.0f}")
    print(f"    Advantage:                       ${base['final_b_nw'] - base['final_a_nw']:>10,.0f}  ({'B' if base['final_b_nw'] > base['final_a_nw'] else 'A'})")
    print(f"    B overtakes A by month (median): {int(base['be_median']) if not np.isnan(base['be_median']) else 'N/A'}")
    print(f"    Paths where B wins:              {base['be_pct']:.0f}%")

    print(f"\n  WITH TIME VALUE OF COMMUTE (${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS_MONTH:.0f}/mo):")
    print(f"    Option A final net worth (mean): ${tv['final_a_nw']:>10,.0f}")
    print(f"    Option B final net worth (mean): ${tv['final_b_nw']:>10,.0f}")
    print(f"    Advantage:                       ${tv['final_b_nw'] - tv['final_a_nw']:>10,.0f}  ({'B' if tv['final_b_nw'] > tv['final_a_nw'] else 'A'})")
    print(f"    B overtakes A by month (median): {int(tv['be_median']) if not np.isnan(tv['be_median']) else 'N/A'}")
    print(f"    Paths where B wins:              {tv['be_pct']:.0f}%")

    print(f"\n  KEY NUMBERS:")
    print(f"    Monthly mortgage payment:        ${MONTHLY_PAYMENT:.2f}")
    print(f"    Cash remaining after closing:    ${STARTING_CASH - TOTAL_UPFRONT:,.0f}")
    print(f"    Mean equity at final month:      ${base['b_equity_mean'][-1]:,.0f}")
    print(f"    Total rental income (mean):      ${float(np.sum(base['rental_mean'])):,.0f}")
    print(f"\n  OUTPUT FILES:")
    print(f"    PDF report:  {pdf_path}")
    for c in charts:
        print(f"    Chart:       {c}")
    print()
