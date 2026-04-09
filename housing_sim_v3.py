#!/usr/bin/env python3
"""
Housing Decision Simulator v3.0
Two-phase long-term model — Muscle Shoals, AL — Nov 2026

OPTION A: Trailer (phase 1) → Buy permanent home (phase 2)
OPTION B: Buy House 1 now (phase 1) → Rent it out + Buy House 2 (phase 2)
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
MONTHS  = int(cfg['simulation']['months'])
MC_RUNS = int(cfg['simulation']['mc_runs'])

# Finances
MONTHLY_INCOME = float(cfg['finances']['monthly_income'])
STARTING_CASH  = float(cfg['finances']['starting_cash'])

# Option A — Trailer
TRAILER_FIXUP        = float(cfg['option_a']['trailer']['fixup_cost'])
TRAILER_FIXED        = float(cfg['option_a']['trailer']['monthly_fixed'])
TRAILER_GAS          = float(cfg['option_a']['trailer']['gas'])
TRAILER_REP_MEAN     = float(cfg['option_a']['trailer']['repair_mean'])
TRAILER_REP_STD      = float(cfg['option_a']['trailer']['repair_std'])
A_MOVEOUT            = int(cfg['option_a']['moveout_month'])

# Option A — Permanent home
A_PRICE     = float(cfg['option_a']['permanent_home']['price'])
A_DOWN_PCT  = float(cfg['option_a']['permanent_home']['down_pct']) / 100
A_CLOSE_PCT = float(cfg['option_a']['permanent_home']['closing_pct']) / 100
A_APR       = float(cfg['option_a']['permanent_home']['apr']) / 100
A_TERM      = int(cfg['option_a']['permanent_home']['term_months'])
A_FIXED     = float(cfg['option_a']['permanent_home']['monthly_fixed'])
A_GAS       = float(cfg['option_a']['permanent_home']['gas'])
A_REP_MEAN  = float(cfg['option_a']['permanent_home']['repair_mean'])
A_REP_STD   = float(cfg['option_a']['permanent_home']['repair_std'])
A_REP_CAP   = float(cfg['option_a']['permanent_home']['repair_cap'])

A_DOWN      = A_PRICE * A_DOWN_PCT
A_CLOSING   = A_PRICE * A_CLOSE_PCT
A_UPFRONT   = A_DOWN + A_CLOSING
A_LOAN      = A_PRICE - A_DOWN
A_MRATE     = A_APR / 12
A_MPAYMENT  = (A_LOAN * A_MRATE / (1 - (1 + A_MRATE) ** -A_TERM))

# Option B — House 1
B1_PRICE     = float(cfg['option_b']['house1']['price'])
B1_DOWN_PCT  = float(cfg['option_b']['house1']['down_pct']) / 100
B1_CLOSE_PCT = float(cfg['option_b']['house1']['closing_pct']) / 100
B1_APR       = float(cfg['option_b']['house1']['apr']) / 100
B1_TERM      = int(cfg['option_b']['house1']['term_months'])
B1_FIXED     = float(cfg['option_b']['house1']['monthly_fixed'])
B1_GAS       = float(cfg['option_b']['house1']['gas'])
B1_REP_MEAN  = float(cfg['option_b']['house1']['repair_mean'])
B1_REP_STD   = float(cfg['option_b']['house1']['repair_std'])
B1_REP_CAP   = float(cfg['option_b']['house1']['repair_cap'])

B1_DOWN      = B1_PRICE * B1_DOWN_PCT
B1_CLOSING   = B1_PRICE * B1_CLOSE_PCT
B1_UPFRONT   = B1_DOWN + B1_CLOSING
B1_LOAN      = B1_PRICE - B1_DOWN
B1_MRATE     = B1_APR / 12
B1_MPAYMENT  = (B1_LOAN * B1_MRATE / (1 - (1 + B1_MRATE) ** -B1_TERM))

B_MOVEOUT    = int(cfg['option_b']['moveout_month'])

# Option B — Rental
RENT_MIN     = float(cfg['option_b']['rental']['rent_min'])
RENT_MAX     = float(cfg['option_b']['rental']['rent_max'])
VACANCY      = float(cfg['option_b']['rental']['vacancy_rate_pct']) / 100

# Option B — House 2
B2_PRICE     = float(cfg['option_b']['house2']['price'])
B2_DOWN_PCT  = float(cfg['option_b']['house2']['down_pct']) / 100
B2_CLOSE_PCT = float(cfg['option_b']['house2']['closing_pct']) / 100
B2_APR       = float(cfg['option_b']['house2']['apr']) / 100
B2_TERM      = int(cfg['option_b']['house2']['term_months'])
B2_FIXED     = float(cfg['option_b']['house2']['monthly_fixed'])
B2_GAS       = float(cfg['option_b']['house2']['gas'])
B2_REP_MEAN  = float(cfg['option_b']['house2']['repair_mean'])
B2_REP_STD   = float(cfg['option_b']['house2']['repair_std'])
B2_REP_CAP   = float(cfg['option_b']['house2']['repair_cap'])

B2_DOWN      = B2_PRICE * B2_DOWN_PCT
B2_CLOSING   = B2_PRICE * B2_CLOSE_PCT
B2_UPFRONT   = B2_DOWN + B2_CLOSING
B2_LOAN      = B2_PRICE - B2_DOWN
B2_MRATE     = B2_APR / 12
B2_MPAYMENT  = (B2_LOAN * B2_MRATE / (1 - (1 + B2_MRATE) ** -B2_TERM))

# Goals & commute
PASSIVE_GOAL        = float(cfg['goals']['passive_income_goal'])
HOURLY_TIME_VALUE   = float(cfg['commute']['hourly_time_value'])
EXTRA_COMMUTE_HRS   = float(cfg['commute']['extra_hours_per_month'])

# Rates
ANNUAL_APPR   = float(cfg['rates']['annual_appreciation_pct']) / 100
ANNUAL_INF    = float(cfg['rates']['annual_inflation_pct']) / 100
ANNUAL_INVEST = float(cfg['rates']['annual_invest_return_pct']) / 100
GAS_VOL       = float(cfg['rates']['gas_volatility_pct']) / 100

MONTHLY_APPR   = (1 + ANNUAL_APPR)   ** (1/12) - 1
MONTHLY_INF    = (1 + ANNUAL_INF)    ** (1/12) - 1
MONTHLY_INVEST = (1 + ANNUAL_INVEST) ** (1/12) - 1

# Print summary
print("\n" + "=" * 65)
print("  HOUSING DECISION SIMULATOR v3.0")
print("=" * 65)
print(f"  Months: {MONTHS} ({MONTHS//12} yrs)  |  MC runs: {MC_RUNS:,}")
print(f"\n  OPTION A: Trailer ({A_MOVEOUT} months) → ${A_PRICE:,.0f} permanent home")
print(f"    Trailer fixup:   ${TRAILER_FIXUP:,.0f}")
print(f"    A upfront costs: ${A_UPFRONT:,.0f}  |  A mortgage: ${A_MPAYMENT:.2f}/mo")
print(f"\n  OPTION B: ${B1_PRICE:,.0f} House 1 → Rent it (mo {B_MOVEOUT}+) → ${B2_PRICE:,.0f} House 2")
print(f"    B1 upfront:      ${B1_UPFRONT:,.0f}  |  B1 mortgage: ${B1_MPAYMENT:.2f}/mo")
print(f"    B2 upfront:      ${B2_UPFRONT:,.0f}  |  B2 mortgage: ${B2_MPAYMENT:.2f}/mo")
print(f"    Rent range:      ${RENT_MIN:.0f}–${RENT_MAX:.0f}/mo  |  Vacancy: {VACANCY*100:.0f}%")
print(f"    Passive income goal: ${PASSIVE_GOAL:.0f}/mo")

# =============================================================================
# AFFORDABILITY CHECK (deterministic — no randomness, straight-line projection)
# =============================================================================

def affordability_check():
    """
    Projects cash forward using average expenses (no random events).
    Checks if each purchase is affordable at the scheduled month.
    If not, finds the earliest month it becomes affordable.
    Returns a dict of results for printing and PDF inclusion.
    """
    results = {}

    # ---- Option B: House 1 at Month 1 ----
    cash_b1 = STARTING_CASH - B1_UPFRONT
    results['b1_starting_cash']   = STARTING_CASH
    results['b1_upfront']         = B1_UPFRONT
    results['b1_cash_after']      = cash_b1
    results['b1_affordable']      = cash_b1 >= 0
    results['b1_cushion']         = cash_b1  # how much left over

    # ---- Option B: Project cash to B_MOVEOUT, check House 2 ----
    cash = cash_b1
    for m in range(1, B_MOVEOUT + 1):
        inf  = (1 + MONTHLY_INF) ** (m - 1)
        exp  = B1_MPAYMENT + B1_FIXED * inf + B1_GAS * inf + B1_REP_MEAN * inf
        cash += MONTHLY_INCOME - exp
        cash *= (1 + MONTHLY_INVEST)

    results['b2_cash_at_moveout']  = cash
    results['b2_upfront']          = B2_UPFRONT
    results['b2_cash_after']       = cash - B2_UPFRONT
    results['b2_affordable']       = cash >= B2_UPFRONT
    results['b2_scheduled_month']  = B_MOVEOUT

    # If not affordable at scheduled month, find earliest month
    if not results['b2_affordable']:
        cash2 = cash_b1
        earliest = None
        for m in range(1, MONTHS + 1):
            inf = (1 + MONTHLY_INF) ** (m - 1)
            if m <= B_MOVEOUT:
                exp = B1_MPAYMENT + B1_FIXED * inf + B1_GAS * inf + B1_REP_MEAN * inf
                flow = MONTHLY_INCOME - exp
            else:
                rent = (RENT_MIN + RENT_MAX) / 2 * (1 + MONTHLY_INF) ** (m - B_MOVEOUT)
                exp  = B1_MPAYMENT + B2_FIXED * inf + B2_GAS * inf + B2_REP_MEAN * inf
                flow = MONTHLY_INCOME - exp + rent
            cash2 += flow
            cash2 *= (1 + MONTHLY_INVEST)
            if cash2 >= B2_UPFRONT and earliest is None:
                earliest = m
        results['b2_earliest_month'] = earliest
    else:
        results['b2_earliest_month'] = B_MOVEOUT

    # ---- Option A: Trailer fixup at Month 1 ----
    results['a_trailer_starting_cash'] = STARTING_CASH
    results['a_trailer_fixup']         = TRAILER_FIXUP
    results['a_cash_after_fixup']      = STARTING_CASH - TRAILER_FIXUP
    results['a_trailer_affordable']    = STARTING_CASH >= TRAILER_FIXUP

    # ---- Option A: Project cash to A_MOVEOUT, check permanent home ----
    cash_a = STARTING_CASH - TRAILER_FIXUP
    for m in range(1, A_MOVEOUT + 1):
        inf   = (1 + MONTHLY_INF) ** (m - 1)
        exp   = TRAILER_FIXED * inf + TRAILER_GAS * inf + TRAILER_REP_MEAN * inf
        cash_a += MONTHLY_INCOME - exp
        cash_a *= (1 + MONTHLY_INVEST)

    results['a_cash_at_moveout']   = cash_a
    results['a_upfront']           = A_UPFRONT
    results['a_cash_after_home']   = cash_a - A_UPFRONT
    results['a_affordable']        = cash_a >= A_UPFRONT
    results['a_scheduled_month']   = A_MOVEOUT

    if not results['a_affordable']:
        cash3 = STARTING_CASH - TRAILER_FIXUP
        earliest_a = None
        for m in range(1, MONTHS + 1):
            inf   = (1 + MONTHLY_INF) ** (m - 1)
            exp   = TRAILER_FIXED * inf + TRAILER_GAS * inf + TRAILER_REP_MEAN * inf
            cash3 += MONTHLY_INCOME - exp
            cash3 *= (1 + MONTHLY_INVEST)
            if cash3 >= A_UPFRONT and earliest_a is None:
                earliest_a = m
        results['a_earliest_month'] = earliest_a
    else:
        results['a_earliest_month'] = A_MOVEOUT

    # ---- Monthly cashflow sanity ----
    results['a_trailer_monthly_exp']     = TRAILER_FIXED + TRAILER_GAS + TRAILER_REP_MEAN
    results['a_trailer_monthly_savings'] = MONTHLY_INCOME - results['a_trailer_monthly_exp']
    results['b1_monthly_exp']            = B1_MPAYMENT + B1_FIXED + B1_GAS + B1_REP_MEAN
    results['b1_monthly_savings']        = MONTHLY_INCOME - results['b1_monthly_exp']

    # ---- Print summary ----
    ok = lambda x: '✓ AFFORDABLE' if x else '✗ NOT AFFORDABLE'
    print('\n' + '=' * 65)
    print('  AFFORDABILITY CHECK')
    print('=' * 65)

    print(f'\n  OPTION A — Trailer fixup (Month 1):')
    print(f'    Starting cash:            ${STARTING_CASH:>10,.0f}')
    print(f'    Trailer fixup cost:      -${TRAILER_FIXUP:>10,.0f}')
    print(f'    Cash remaining:           ${results["a_cash_after_fixup"]:>10,.0f}  {ok(results["a_trailer_affordable"])}')
    print(f'    Monthly savings (trailer): ${results["a_trailer_monthly_savings"]:>9,.0f}/mo')

    print(f'\n  OPTION A — Buy permanent home (scheduled Month {A_MOVEOUT}):')
    print(f'    Projected cash at Mo {A_MOVEOUT}:  ${results["a_cash_at_moveout"]:>10,.0f}')
    print(f'    Down + closing needed:   -${results["a_upfront"]:>10,.0f}')
    print(f'    Cash remaining after:     ${results["a_cash_after_home"]:>10,.0f}  {ok(results["a_affordable"])}')
    if not results['a_affordable']:
        print(f'    Earliest affordable month: Month {results["a_earliest_month"]}')
    else:
        delay = results['a_earliest_month'] - A_MOVEOUT
        print(f'    Could buy {abs(delay)} months earlier if needed')

    print(f'\n  OPTION B — Buy House 1 (Month 1):')
    print(f'    Starting cash:            ${STARTING_CASH:>10,.0f}')
    print(f'    Down + closing needed:   -${B1_UPFRONT:>10,.0f}')
    print(f'    Cash remaining:           ${results["b1_cash_after"]:>10,.0f}  {ok(results["b1_affordable"])}')
    print(f'    Monthly savings (house1):  ${results["b1_monthly_savings"]:>9,.0f}/mo')

    print(f'\n  OPTION B — Buy House 2 (scheduled Month {B_MOVEOUT}):')
    print(f'    Projected cash at Mo {B_MOVEOUT}:  ${results["b2_cash_at_moveout"]:>10,.0f}')
    print(f'    Down + closing needed:   -${B2_UPFRONT:>10,.0f}')
    print(f'    Cash remaining after:     ${results["b2_cash_after"]:>10,.0f}  {ok(results["b2_affordable"])}')
    if not results['b2_affordable']:
        print(f'    Earliest affordable month: Month {results["b2_earliest_month"]}')
        print(f'    *** WARNING: Simulation will delay House 2 purchase until affordable ***')
    else:
        months_early = B_MOVEOUT - results['b2_earliest_month'] if results['b2_earliest_month'] < B_MOVEOUT else 0
        if months_early > 0:
            print(f'    Could afford House 2 {months_early} months earlier than scheduled')

    print('=' * 65)
    return results


# =============================================================================
# OUTPUT DIRS
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
COL_PUR  = '#8E44AD'
DOLLAR   = FuncFormatter(lambda x, _: f'${x:,.0f}')
KDOLLAR  = FuncFormatter(lambda x, _: f'${x/1000:.0f}k')


# =============================================================================
# HELPERS
# =============================================================================

def amortize(balance, monthly_rate, payment):
    interest  = balance * monthly_rate
    principal = min(payment - interest, balance)
    new_bal   = max(0.0, balance - principal)
    return interest, principal, new_bal

def months_to_date(m):
    year  = 2026 + (m - 1) // 12
    month = ((10 + m - 1) % 12) + 1
    names = ['Jan','Feb','Mar','Apr','May','Jun',
             'Jul','Aug','Sep','Oct','Nov','Dec']
    return f"{names[month-1]} {year}"

X = np.arange(1, MONTHS + 1)


# =============================================================================
# SINGLE PATH SIMULATION
# =============================================================================

def run_one_path(use_time_value=False, income_growth_annual=0.0):
    inc_growth  = (1 + income_growth_annual) ** (1/12) - 1
    monthly_inc = MONTHLY_INCOME

    # ---- Option A state ----
    a_cash        = STARTING_CASH - TRAILER_FIXUP
    a_in_trailer  = True
    a_loan_bal    = 0.0
    a_home_val    = 0.0

    # ---- Option B state ----
    b_cash        = STARTING_CASH - B1_UPFRONT
    b_in_house1   = True
    b1_loan_bal   = B1_LOAN
    b1_home_val   = B1_PRICE
    b2_loan_bal   = 0.0
    b2_home_val   = 0.0
    b_has_house2  = False

    out = {k: [] for k in [
        'a_cash', 'a_equity', 'a_nw',
        'b_cash', 'b_equity1', 'b_equity2', 'b_nw',
        'passive_income', 'rental_gross',
        'a_expenses', 'b_expenses',
    ]}
    a_actual_purchase_month  = None
    b2_actual_purchase_month = None

    for month in range(1, MONTHS + 1):
        if month > 1:
            monthly_inc *= (1 + inc_growth)

        inf   = (1 + MONTHLY_INF) ** (month - 1)
        shock = 1 + np.random.uniform(-GAS_VOL, GAS_VOL)

        # ============================================================
        # OPTION A
        # ============================================================

        # Phase transition: move out of trailer, buy permanent home
        # Only buy when scheduled AND cash is actually sufficient
        if a_in_trailer and month > A_MOVEOUT and a_cash >= A_UPFRONT:
            a_in_trailer = False
            a_cash      -= A_UPFRONT
            a_loan_bal   = A_LOAN
            a_home_val   = A_PRICE
            a_actual_purchase_month = month

        if a_in_trailer:
            # Trailer expenses
            a_rep   = max(0, np.random.normal(TRAILER_REP_MEAN * inf, TRAILER_REP_STD * inf))
            a_gas   = TRAILER_GAS * inf * shock
            a_exp   = TRAILER_FIXED * inf + a_gas + a_rep
            if use_time_value:
                a_exp += HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS
            a_equity = 0.0
        else:
            # Permanent home expenses
            a_rep   = min(max(0, np.random.normal(A_REP_MEAN * inf, A_REP_STD * inf)), A_REP_CAP)
            a_gas   = A_GAS * inf * shock
            a_exp   = A_MPAYMENT + A_FIXED * inf + a_gas + a_rep
            if use_time_value:
                a_exp += HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS
            _, _, a_loan_bal = amortize(a_loan_bal, A_MRATE, A_MPAYMENT)
            a_home_val *= (1 + MONTHLY_APPR)
            a_equity = a_home_val - a_loan_bal

        a_flow  = monthly_inc - a_exp
        a_cash += a_flow
        a_cash *= (1 + MONTHLY_INVEST)
        a_nw    = a_cash + a_equity

        # ============================================================
        # OPTION B
        # ============================================================

        # Phase transition: move out of House 1, buy House 2
        # Only buy when scheduled AND cash is actually sufficient
        if b_in_house1 and month > B_MOVEOUT and b_cash >= B2_UPFRONT:
            b_in_house1  = False
            b_has_house2 = True
            b_cash      -= B2_UPFRONT
            b2_loan_bal  = B2_LOAN
            b2_home_val  = B2_PRICE
            b2_actual_purchase_month = month

        # House 1 always appreciates and amortizes (it's always owned)
        _, _, b1_loan_bal = amortize(b1_loan_bal, B1_MRATE, B1_MPAYMENT)
        b1_home_val *= (1 + MONTHLY_APPR)
        b1_equity    = b1_home_val - b1_loan_bal

        if b_in_house1:
            # Living in House 1
            b1_rep  = min(max(0, np.random.normal(B1_REP_MEAN * inf, B1_REP_STD * inf)), B1_REP_CAP)
            b1_gas  = B1_GAS * inf * shock
            b_exp   = B1_MPAYMENT + B1_FIXED * inf + b1_gas + b1_rep
            rental  = 0.0
            passive = 0.0
            b2_equity = 0.0
        else:
            # House 1 is a rental, living in House 2
            b1_rep_land = min(max(0, np.random.normal(B1_REP_MEAN * 0.5 * inf,
                                                       B1_REP_STD * 0.5 * inf)), B1_REP_CAP * 0.5)
            if np.random.rand() > VACANCY:
                rent_base = np.random.uniform(RENT_MIN, RENT_MAX)
                rental    = rent_base * (1 + MONTHLY_INF) ** (month - B_MOVEOUT)
            else:
                rental = 0.0

            passive = rental - B1_MPAYMENT - b1_rep_land

            b2_rep  = min(max(0, np.random.normal(B2_REP_MEAN * inf, B2_REP_STD * inf)), B2_REP_CAP)
            b2_gas  = B2_GAS * inf * shock
            b_exp   = B2_MPAYMENT + B2_FIXED * inf + b2_gas + b2_rep

            _, _, b2_loan_bal = amortize(b2_loan_bal, B2_MRATE, B2_MPAYMENT)
            b2_home_val *= (1 + MONTHLY_APPR)
            b2_equity    = b2_home_val - b2_loan_bal

        b_flow  = monthly_inc - b_exp + rental
        b_cash += b_flow
        b_cash *= (1 + MONTHLY_INVEST)
        b_nw    = b_cash + b1_equity + (b2_equity if b_has_house2 else 0)

        # Record
        out['a_cash'].append(a_cash)
        out['a_equity'].append(a_equity)
        out['a_nw'].append(a_nw)
        out['b_cash'].append(b_cash)
        out['b_equity1'].append(b1_equity)
        out['b_equity2'].append(b2_equity if b_has_house2 else 0.0)
        out['b_nw'].append(b_nw)
        out['passive_income'].append(passive)
        out['rental_gross'].append(rental)
        out['a_expenses'].append(a_exp)
        out['b_expenses'].append(b_exp)

    out['a_actual_purchase_month']  = a_actual_purchase_month
    out['b2_actual_purchase_month'] = b2_actual_purchase_month
    return out


# =============================================================================
# MONTE CARLO ENGINE
# =============================================================================

def monte_carlo(use_time_value=False, income_growth_annual=0.0, label=""):
    all_a_nw      = np.zeros((MC_RUNS, MONTHS))
    all_b_nw      = np.zeros((MC_RUNS, MONTHS))
    all_a_eq      = np.zeros((MC_RUNS, MONTHS))
    all_b_eq1     = np.zeros((MC_RUNS, MONTHS))
    all_b_eq2     = np.zeros((MC_RUNS, MONTHS))
    all_a_cash    = np.zeros((MC_RUNS, MONTHS))
    all_b_cash    = np.zeros((MC_RUNS, MONTHS))
    all_passive   = np.zeros((MC_RUNS, MONTHS))
    all_rental    = np.zeros((MC_RUNS, MONTHS))
    be_months              = []
    goal_months            = []
    a_purchase_months      = []
    b2_purchase_months     = []

    for i in range(MC_RUNS):
        p = run_one_path(use_time_value, income_growth_annual)
        all_a_nw[i]    = p['a_nw']
        all_b_nw[i]    = p['b_nw']
        all_a_eq[i]    = p['a_equity']
        all_b_eq1[i]   = p['b_equity1']
        all_b_eq2[i]   = p['b_equity2']
        all_a_cash[i]  = p['a_cash']
        all_b_cash[i]  = p['b_cash']
        all_passive[i] = p['passive_income']
        all_rental[i]  = p['rental_gross']

        a_purchase_months.append(p['a_actual_purchase_month']  if p['a_actual_purchase_month']  else MONTHS + 1)
        b2_purchase_months.append(p['b2_actual_purchase_month'] if p['b2_actual_purchase_month'] else MONTHS + 1)

        # Break-even: 3 consecutive months B > A
        diff = np.array(p['b_nw']) - np.array(p['a_nw'])
        be   = None
        for j in range(len(diff) - 2):
            if diff[j] > 0 and diff[j+1] > 0 and diff[j+2] > 0:
                be = j + 1
                break
        be_months.append(be if be is not None else MONTHS + 1)

        # Goal: 3 consecutive months passive income >= goal
        pi   = np.array(p['passive_income'])
        goal = None
        for j in range(len(pi) - 2):
            if pi[j] >= PASSIVE_GOAL and pi[j+1] >= PASSIVE_GOAL and pi[j+2] >= PASSIVE_GOAL:
                goal = j + 1
                break
        goal_months.append(goal if goal is not None else MONTHS + 1)

    within_be   = [b for b in be_months   if b <= MONTHS]
    within_goal = [g for g in goal_months if g <= MONTHS]
    be_pct      = len(within_be)   / MC_RUNS * 100
    goal_pct    = len(within_goal) / MC_RUNS * 100
    be_med      = float(np.median(within_be))   if within_be   else float('nan')
    goal_med    = float(np.median(within_goal)) if within_goal else float('nan')

    return {
        'label':          label,
        'a_nw_mean':      np.mean(all_a_nw,    axis=0),
        'a_nw_p10':       np.percentile(all_a_nw, 10, axis=0),
        'a_nw_p90':       np.percentile(all_a_nw, 90, axis=0),
        'b_nw_mean':      np.mean(all_b_nw,    axis=0),
        'b_nw_p10':       np.percentile(all_b_nw, 10, axis=0),
        'b_nw_p90':       np.percentile(all_b_nw, 90, axis=0),
        'a_equity_mean':  np.mean(all_a_eq,    axis=0),
        'b_equity1_mean': np.mean(all_b_eq1,   axis=0),
        'b_equity2_mean': np.mean(all_b_eq2,   axis=0),
        'a_cash_mean':    np.mean(all_a_cash,  axis=0),
        'b_cash_mean':    np.mean(all_b_cash,  axis=0),
        'passive_mean':   np.mean(all_passive, axis=0),
        'passive_p10':    np.percentile(all_passive, 10, axis=0),
        'passive_p90':    np.percentile(all_passive, 90, axis=0),
        'rental_mean':    np.mean(all_rental,  axis=0),
        'be_months':      be_months,
        'be_median':      be_med,
        'be_pct':         be_pct,
        'goal_months':    goal_months,
        'goal_median':    goal_med,
        'goal_pct':          goal_pct,
        'a_purchase_months':  a_purchase_months,
        'b2_purchase_months': b2_purchase_months,
        'a_purchase_delayed_pct':  sum(m > A_MOVEOUT + 1 for m in a_purchase_months)  / MC_RUNS * 100,
        'b2_purchase_delayed_pct': sum(m > B_MOVEOUT + 1 for m in b2_purchase_months) / MC_RUNS * 100,
        'a_purchase_med':   float(np.median([m for m in a_purchase_months  if m <= MONTHS])) if any(m <= MONTHS for m in a_purchase_months)  else float('nan'),
        'b2_purchase_med':  float(np.median([m for m in b2_purchase_months if m <= MONTHS])) if any(m <= MONTHS for m in b2_purchase_months) else float('nan'),
        'final_a_nw':     float(np.mean(all_a_nw[:, -1])),
        'final_b_nw':     float(np.mean(all_b_nw[:, -1])),
        'final_a_p10':    float(np.percentile(all_a_nw[:, -1], 10)),
        'final_b_p10':    float(np.percentile(all_b_nw[:, -1], 10)),
        'final_a_p90':    float(np.percentile(all_a_nw[:, -1], 90)),
        'final_b_p90':    float(np.percentile(all_b_nw[:, -1], 90)),
    }


# =============================================================================
# CHART 1 — NET WORTH PROJECTION
# =============================================================================

def chart_networth(base, tv):
    tv_mo = f"${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS:.0f}/mo"
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    fig.suptitle(f'Net Worth — Option A (Trailer→Home) vs Option B (House→Rental→House2)\n'
                 f'{MONTHS//12}-Year Horizon | {MC_RUNS:,} Monte Carlo Paths',
                 fontsize=13, fontweight='bold')

    for ax, res, title in zip(axes, [base, tv],
                               ['Without Time Value of Commute',
                                f'With Time Value ({tv_mo})']):
        ax.fill_between(X, res['a_nw_p10'], res['a_nw_p90'], alpha=0.15, color=COL_A)
        ax.fill_between(X, res['b_nw_p10'], res['b_nw_p90'], alpha=0.15, color=COL_B)
        ax.plot(X, res['a_nw_mean'], color=COL_A, lw=2.5, label='Option A (Trailer→Home)')
        ax.plot(X, res['b_nw_mean'], color=COL_B, lw=2.5, label='Option B (House→Rental→House2)')

        # Phase markers
        ax.axvline(A_MOVEOUT, color=COL_A, lw=1, linestyle=':', alpha=0.7)
        ax.axvline(B_MOVEOUT, color=COL_B, lw=1, linestyle=':', alpha=0.7)
        ax.text(A_MOVEOUT + 1, ax.get_ylim()[0], 'A buys home', color=COL_A,
                fontsize=7, rotation=90, va='bottom', alpha=0.8)
        ax.text(B_MOVEOUT + 1, ax.get_ylim()[0], 'B starts rental', color=COL_B,
                fontsize=7, rotation=90, va='bottom', alpha=0.8)

        ax.yaxis.set_major_formatter(KDOLLAR)
        ax.set_xlabel(f'Month from Nov 2026', fontsize=10)
        ax.set_ylabel('Net Worth', fontsize=10)
        ax.set_title(title, fontsize=11)
        ax.legend(fontsize=9)

        ax.annotate(f"A: ${res['final_a_nw']:,.0f}",
                    xy=(MONTHS, res['a_nw_mean'][-1]), xytext=(-40, -18),
                    textcoords='offset points', color=COL_A, fontsize=8, fontweight='bold')
        ax.annotate(f"B: ${res['final_b_nw']:,.0f}",
                    xy=(MONTHS, res['b_nw_mean'][-1]), xytext=(-40, 6),
                    textcoords='offset points', color=COL_B, fontsize=8, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart01_networth.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 2 — NET WORTH GAP (B minus A)
# =============================================================================

def chart_nw_gap(base, tv):
    fig, ax = plt.subplots(figsize=(12, 5))
    gap_base = base['b_nw_mean'] - base['a_nw_mean']
    gap_tv   = tv['b_nw_mean']   - tv['a_nw_mean']

    ax.plot(X, gap_base, color=COL_B, lw=2.5, label='No time value')
    ax.plot(X, gap_tv,   color=COL_ACC, lw=2.5, linestyle='--',
            label=f'With time value (${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS:.0f}/mo)')
    ax.axhline(0, color='black', lw=1, linestyle='-', alpha=0.4)
    ax.fill_between(X, 0, gap_base, where=gap_base >= 0, alpha=0.15, color=COL_B)
    ax.fill_between(X, 0, gap_base, where=gap_base <  0, alpha=0.15, color=COL_WARN)

    ax.axvline(A_MOVEOUT, color=COL_A, lw=1, linestyle=':', alpha=0.6,
               label=f'A buys home (Mo {A_MOVEOUT})')
    ax.axvline(B_MOVEOUT, color=COL_B, lw=1, linestyle=':', alpha=0.6,
               label=f'B starts rental (Mo {B_MOVEOUT})')

    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('B Net Worth minus A Net Worth', fontsize=10)
    ax.set_title('Net Worth Gap Over Time\n'
                 'Above zero = Option B is ahead | Below zero = Option A is ahead',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart02_nw_gap.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 3 — PASSIVE INCOME GROWTH
# =============================================================================

def chart_passive(base):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(X, base['passive_p10'], base['passive_p90'],
                    alpha=0.2, color=COL_B, label='P10–P90 range')
    ax.plot(X, base['passive_mean'], color=COL_B, lw=2.5, label='Mean passive income')
    ax.axhline(PASSIVE_GOAL, color=COL_ACC, lw=2, linestyle='--',
               label=f'Goal: ${PASSIVE_GOAL:.0f}/mo')
    ax.axhline(0, color='black', lw=0.8, alpha=0.4)
    ax.axvline(B_MOVEOUT, color=COL_B, lw=1, linestyle=':', alpha=0.7,
               label=f'House 1 becomes rental (Mo {B_MOVEOUT})')

    if not np.isnan(base['goal_median']) and base['goal_median'] <= MONTHS:
        gm = int(base['goal_median'])
        ax.axvline(gm, color=COL_WARN, lw=1.5, linestyle='--', alpha=0.8)
        ax.text(gm + 1, PASSIVE_GOAL * 1.05, f'Goal hit\nMo {gm}\n({months_to_date(gm)})',
                color=COL_WARN, fontsize=8)

    ax.yaxis.set_major_formatter(DOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Monthly Passive Income ($)', fontsize=10)
    ax.set_title(f'Option B — Monthly Passive Income Growth\n'
                 f'{base["goal_pct"]:.0f}% of paths hit ${PASSIVE_GOAL:.0f}/mo goal within {MONTHS//12} years',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart03_passive_income.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 4 — EQUITY COMPARISON
# =============================================================================

def chart_equity(base):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Option A equity
    ax = axes[0]
    ax.fill_between(X, 0, base['a_equity_mean'], alpha=0.6, color=COL_A,
                    label=f'Option A equity (${A_PRICE:,.0f} home)')
    ax.axvline(A_MOVEOUT, color=COL_A, lw=1.5, linestyle='--', alpha=0.7,
               label=f'Buys home (Mo {A_MOVEOUT})')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Equity ($)', fontsize=10)
    ax.set_title('Option A — 1 Property\nEquity builds after home purchase',
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)

    # Right: Option B equity (stacked)
    ax = axes[1]
    ax.stackplot(X,
                 base['b_equity1_mean'],
                 base['b_equity2_mean'],
                 labels=[f'House 1 equity (${B1_PRICE:,.0f})',
                         f'House 2 equity (${B2_PRICE:,.0f})'],
                 colors=[COL_B, '#8FBC8F'],
                 alpha=0.75)
    ax.axvline(B_MOVEOUT, color=COL_B, lw=1.5, linestyle='--', alpha=0.7,
               label=f'House 2 bought (Mo {B_MOVEOUT})')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Combined Equity ($)', fontsize=10)
    ax.set_title('Option B — 2 Properties\nStacked equity across both homes',
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)

    fig.suptitle('Equity Comparison — 1 Property vs 2 Properties',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart04_equity.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 5 — BREAK-EVEN DISTRIBUTION
# =============================================================================

def chart_breakeven(base, tv):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    tv_mo = f"${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS:.0f}/mo"

    for ax, res, title in zip(axes, [base, tv],
                               ['Without Time Value',
                                f'With Time Value ({tv_mo})']):
        valid = [b for b in res['be_months'] if b <= MONTHS]
        never = sum(b > MONTHS for b in res['be_months'])
        if valid:
            ax.hist(valid, bins=range(1, MONTHS + 2, 6), color=COL_B,
                    edgecolor='white', alpha=0.85)
        if not np.isnan(res['be_median']):
            ax.axvline(res['be_median'], color=COL_ACC, lw=2, linestyle='--',
                       label=f'Median: Month {int(res["be_median"])} ({months_to_date(int(res["be_median"]))})')
        ax.set_xlabel('Month B overtakes A in net worth', fontsize=10)
        ax.set_ylabel('Number of simulations', fontsize=10)
        ax.set_title(f'{title}\n{res["be_pct"]:.0f}% of paths: B wins within {MONTHS//12} years\n'
                     f'({never} paths: B never overtakes)', fontsize=10, fontweight='bold')
        ax.legend(fontsize=9)
        ax.set_xlim(1, MONTHS)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart05_breakeven.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 6 — PASSIVE INCOME GOAL ACHIEVEMENT
# =============================================================================

def chart_goal(base):
    valid = [g for g in base['goal_months'] if g <= MONTHS]
    never = sum(g > MONTHS for g in base['goal_months'])

    fig, ax = plt.subplots(figsize=(10, 5))
    if valid:
        ax.hist(valid, bins=range(1, MONTHS + 2, 6), color=COL_PUR,
                edgecolor='white', alpha=0.85)
    if not np.isnan(base['goal_median']):
        ax.axvline(base['goal_median'], color=COL_ACC, lw=2, linestyle='--',
                   label=f'Median: Month {int(base["goal_median"])} ({months_to_date(int(base["goal_median"]))})')

    ax.set_xlabel('Month passive income first hits goal for 3+ consecutive months', fontsize=10)
    ax.set_ylabel('Number of simulations', fontsize=10)
    ax.set_title(f'When Does Option B Hit ${PASSIVE_GOAL:.0f}/mo Passive Income?\n'
                 f'{base["goal_pct"]:.0f}% of paths achieve this within {MONTHS//12} years '
                 f'| {never} paths never reach it',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.set_xlim(1, MONTHS)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart06_goal.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 7 — CUMULATIVE GAS
# =============================================================================

def chart_gas():
    a_cum, b_cum = [], []
    ta, tb = 0, 0
    for m in range(1, MONTHS + 1):
        inf = (1 + MONTHLY_INF) ** (m - 1)
        # Option A: trailer gas until moveout, then permanent home gas
        ta += (TRAILER_GAS if m <= A_MOVEOUT else A_GAS) * inf
        # Option B: house1 gas until moveout, then house2 gas
        tb += (B1_GAS if m <= B_MOVEOUT else B2_GAS) * inf
        a_cum.append(ta)
        b_cum.append(tb)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(X, a_cum, color=COL_A, lw=2.5, label=f'Option A — trailer ${TRAILER_GAS:.0f}/mo → home ${A_GAS:.0f}/mo')
    ax.plot(X, b_cum, color=COL_B, lw=2.5, label=f'Option B — house ${B1_GAS:.0f}/mo → house2 ${B2_GAS:.0f}/mo')
    ax.fill_between(X, b_cum, a_cum, where=[a >= b for a, b in zip(a_cum, b_cum)],
                    alpha=0.15, color=COL_WARN,
                    label=f'Total A saves: ${a_cum[-1]-b_cum[-1]:,.0f} less spent by B')
    ax.axvline(A_MOVEOUT, color=COL_A, lw=1, linestyle=':', alpha=0.6)
    ax.axvline(B_MOVEOUT, color=COL_B, lw=1, linestyle=':', alpha=0.6)
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Cumulative Gas Spend', fontsize=10)
    ax.set_title('Cumulative Gas Cost — Both Options Over Full Horizon', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart07_gas.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 8 — MONTHLY SPENDING BREAKDOWN
# =============================================================================

def chart_spending():
    # Month 1 baseline for each option
    a_exp_m1 = TRAILER_FIXED + TRAILER_GAS + TRAILER_REP_MEAN
    b_exp_m1 = B1_MPAYMENT  + B1_FIXED    + B1_GAS + B1_REP_MEAN

    a_items = {
        'Savings':        max(0, MONTHLY_INCOME - a_exp_m1),
        'Fixed expenses': TRAILER_FIXED,
        'Gas':            TRAILER_GAS,
        'Repairs':        TRAILER_REP_MEAN,
    }
    b_items = {
        'Savings':        max(0, MONTHLY_INCOME - b_exp_m1),
        'Fixed expenses': B1_FIXED,
        'Mortgage':       B1_MPAYMENT,
        'Gas':            B1_GAS,
        'Repairs':        B1_REP_MEAN,
    }

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle('Monthly Spending Breakdown — Month 1 Baseline', fontsize=13, fontweight='bold')
    pal = plt.cm.tab20.colors

    for ax, items, title in zip(axes, [a_items, b_items],
                                 ['Option A (Trailer Phase)',
                                  f'Option B (House 1, ${B1_PRICE:,.0f})']):
        labels  = list(items.keys())
        vals    = list(items.values())
        explode = [0.03] * len(vals)
        wedges, _, autos = ax.pie(
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
    path = os.path.join(CHART_DIR, 'chart08_spending.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 9 — INCOME GROWTH SCENARIOS
# =============================================================================

def chart_scenarios(scenarios):
    fig, ax = plt.subplots(figsize=(13, 6))
    cmap_a = plt.cm.Blues(np.linspace(0.45, 0.9, len(scenarios)))
    cmap_b = plt.cm.Greens(np.linspace(0.45, 0.9, len(scenarios)))

    for i, (label, res) in enumerate(scenarios):
        ax.plot(X, res['a_nw_mean'], color=cmap_a[i], lw=2, linestyle='--',
                label=f'A — {label}')
        ax.plot(X, res['b_nw_mean'], color=cmap_b[i], lw=2,
                label=f'B — {label}')

    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_ylabel('Mean Net Worth', fontsize=10)
    ax.set_title('Income Growth Sensitivity\n(dashed = Option A, solid = Option B)',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart09_scenarios.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 10 — AMORTIZATION (House 1)
# =============================================================================

def chart_amortization():
    balances, principals, interests, equities, home_vals = [], [], [], [], []
    bal = B1_LOAN
    hv  = B1_PRICE
    for m in range(1, MONTHS + 1):
        interest, principal, bal = amortize(bal, B1_MRATE, B1_MPAYMENT)
        hv *= (1 + MONTHLY_APPR)
        equities.append(hv - bal)
        home_vals.append(hv)
        balances.append(bal)
        principals.append(principal)
        interests.append(interest)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    ax.bar(X, interests,  color=COL_WARN, label='Interest', alpha=0.8)
    ax.bar(X, principals, bottom=interests, color=COL_B, label='Principal', alpha=0.8)
    ax.yaxis.set_major_formatter(DOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_title(f'House 1 Mortgage — ${B1_MPAYMENT:.2f}/mo\n'
                 f'Month 1: ${interests[0]:.0f} interest / ${principals[0]:.0f} principal',
                 fontsize=10, fontweight='bold')
    ax.legend(fontsize=9)

    ax = axes[1]
    ax.fill_between(X, 0, equities, alpha=0.4, color=COL_B, label='Your equity')
    ax.fill_between(X, equities, home_vals, alpha=0.25, color=COL_WARN, label='Remaining loan')
    ax.plot(X, home_vals, color=COL_B,   lw=2, label=f'Home value ({ANNUAL_APPR*100:.0f}%/yr)')
    ax.plot(X, equities,  color=COL_ACC, lw=2, label='Equity')
    ax.plot(X, balances,  color=COL_WARN, lw=1.5, linestyle='--', label='Loan balance')
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_xlabel('Month', fontsize=10)
    ax.set_title(f'House 1 Equity Buildup\nEquity at Mo {MONTHS}: ${equities[-1]:,.0f}',
                 fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)

    fig.suptitle(f'House 1 Mortgage Amortization — ${B1_PRICE:,.0f} at {B1_APR*100:.1f}%',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart10_amortization.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# CHART 11 — UPFRONT COSTS COMPARISON
# =============================================================================

def chart_upfront():
    fig, ax = plt.subplots(figsize=(10, 6))

    a_labels = [f'Trailer fixup\n${TRAILER_FIXUP:,.0f}',
                f'Home down\n${A_DOWN:,.0f}',
                f'Home closing\n${A_CLOSING:,.0f}']
    a_vals   = [TRAILER_FIXUP, A_DOWN, A_CLOSING]
    a_colors = ['#B0C4DE', '#3B5FA0', '#1A3A6C']

    b_labels = [f'House 1 down\n${B1_DOWN:,.0f}',
                f'House 1 closing\n${B1_CLOSING:,.0f}',
                f'House 2 down\n${B2_DOWN:,.0f}',
                f'House 2 closing\n${B2_CLOSING:,.0f}']
    b_vals   = [B1_DOWN, B1_CLOSING, B2_DOWN, B2_CLOSING]
    b_colors = ['#90EE90', '#2E8B57', '#006400', '#004d00']

    x      = np.array([0, 1])
    width  = 0.4

    # Stacked bars
    a_bottom, b_bottom = 0, 0
    for lbl, val, col in zip(a_labels, a_vals, a_colors):
        ax.bar(0, val, width, bottom=a_bottom, color=col, edgecolor='white', linewidth=0.5)
        if val > 500:
            ax.text(0, a_bottom + val / 2, f'${val:,.0f}', ha='center', va='center',
                    fontsize=8, color='white', fontweight='bold')
        a_bottom += val

    for lbl, val, col in zip(b_labels, b_vals, b_colors):
        ax.bar(1, val, width, bottom=b_bottom, color=col, edgecolor='white', linewidth=0.5)
        if val > 500:
            ax.text(1, b_bottom + val / 2, f'${val:,.0f}', ha='center', va='center',
                    fontsize=8, color='white', fontweight='bold')
        b_bottom += val

    ax.text(0, a_bottom + 500, f'Total: ${a_bottom:,.0f}', ha='center',
            fontsize=10, fontweight='bold', color=COL_A)
    ax.text(1, b_bottom + 500, f'Total: ${b_bottom:,.0f}', ha='center',
            fontsize=10, fontweight='bold', color=COL_B)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Option A\n(Trailer + Home)', 'Option B\n(House 1 + House 2)'], fontsize=11)
    ax.yaxis.set_major_formatter(KDOLLAR)
    ax.set_ylabel('Total Upfront Costs ($)', fontsize=10)
    ax.set_title('Total Upfront Cash Required — Full Lifecycle\n'
                 '(Option A pays twice: trailer fixup + home purchase)\n'
                 '(Option B pays twice: House 1 + House 2)',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'chart11_upfront.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


# =============================================================================
# PDF REPORT
# =============================================================================

def build_pdf(base, tv, scenarios, charts, afford):
    path = os.path.join(OUTPUT_DIR, 'housing_analysis_report.pdf')
    doc  = SimpleDocTemplate(path, pagesize=letter,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles = getSampleStyleSheet()
    S = {
        'title':   ParagraphStyle('t',  parent=styles['Title'],
                                  fontSize=20, textColor=colors.HexColor('#1A3A5C'), spaceAfter=6),
        'h1':      ParagraphStyle('h1', parent=styles['Heading1'],
                                  fontSize=14, textColor=colors.HexColor('#2E5D9A'),
                                  spaceBefore=14, spaceAfter=4),
        'h2':      ParagraphStyle('h2', parent=styles['Heading2'],
                                  fontSize=11, textColor=colors.HexColor('#2E8B57'),
                                  spaceBefore=8, spaceAfter=2),
        'body':    ParagraphStyle('b',  parent=styles['Normal'],
                                  fontSize=9.5, leading=14, spaceAfter=6),
        'bullet':  ParagraphStyle('bl', parent=styles['Normal'],
                                  fontSize=9, leading=13, leftIndent=14, spaceAfter=3),
        'green':   ParagraphStyle('g',  parent=styles['Normal'],
                                  fontSize=9.5, textColor=colors.HexColor('#1E6B3A'),
                                  leading=13, spaceAfter=4),
        'warn':    ParagraphStyle('w',  parent=styles['Normal'],
                                  fontSize=9.5, textColor=colors.HexColor('#C0392B'),
                                  leading=13, spaceAfter=4),
        'caption': ParagraphStyle('c',  parent=styles['Normal'],
                                  fontSize=8, textColor=colors.gray,
                                  leading=11, spaceAfter=8, alignment=1),
    }

    def HR():
        return HRFlowable(width='100%', thickness=0.5,
                          color=colors.HexColor('#CCCCCC'), spaceAfter=8, spaceBefore=4)

    def img(p, w=6.5):
        return Image(p, width=w*inch, height=w*inch * 0.46)

    def table(data, col_widths, header_color='#2E5D9A'):
        ts = TableStyle([
            ('BACKGROUND',   (0,0), (-1,0), colors.HexColor(header_color)),
            ('TEXTCOLOR',    (0,0), (-1,0), colors.white),
            ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',     (0,0), (-1,-1), 8.5),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#EEF4FF')]),
            ('GRID',         (0,0), (-1,-1), 0.3, colors.HexColor('#CCCCCC')),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',   (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ])
        return Table(data, colWidths=col_widths, style=ts)

    story = []
    fmt = lambda v: f'${v:,.0f}'

    # Cover
    story += [
        Paragraph('Housing Decision Analysis', S['title']),
        Paragraph('Option A: Trailer → Permanent Home  vs  Option B: Buy Now → Rent → Buy Again',
                  S['h2']),
        Paragraph(f'Muscle Shoals, AL  |  {MONTHS//12}-Year Horizon  |  '
                  f'{MC_RUNS:,} Monte Carlo Paths  |  '
                  f'Generated {datetime.now().strftime("%B %d, %Y")}', S['body']),
        HR(),
    ]

    # Parameters table — side by side A vs B
    story.append(Paragraph('Simulation Parameters', S['h1']))
    param_data = [
        ['Parameter', 'Option A', 'Option B'],
        ['Simulation length', f'{MONTHS} months ({MONTHS//12} yrs)', '← same'],
        ['Monte Carlo runs', f'{MC_RUNS:,}', '← same'],
        ['Monthly income', fmt(MONTHLY_INCOME), '← same'],
        ['Starting cash', fmt(STARTING_CASH), '← same'],
        ['Phase 1 upfront cost', fmt(TRAILER_FIXUP) + ' (fixup)', fmt(B1_UPFRONT) + ' (buy house)'],
        ['Phase 1 monthly gas', f'${TRAILER_GAS:.0f}/mo', f'${B1_GAS:.0f}/mo'],
        ['Phase 1 ends', f'Month {A_MOVEOUT}', f'Month {B_MOVEOUT}'],
        ['Phase 2 home price', fmt(A_PRICE), fmt(B2_PRICE)],
        ['Phase 2 mortgage', f'${A_MPAYMENT:.2f}/mo', f'${B2_MPAYMENT:.2f}/mo'],
        ['Phase 2 upfront', fmt(A_UPFRONT), fmt(B2_UPFRONT)],
        ['Rental income (B only)', 'None', f'${RENT_MIN:.0f}–${RENT_MAX:.0f}/mo from Mo {B_MOVEOUT}'],
        ['Vacancy rate (B only)', 'N/A', f'{VACANCY*100:.0f}%'],
        ['Passive income goal', 'N/A', f'${PASSIVE_GOAL:.0f}/mo'],
        ['Home appreciation', f'{ANNUAL_APPR*100:.1f}%/yr', '← same'],
        ['Expense inflation', f'{ANNUAL_INF*100:.1f}%/yr', '← same'],
        ['HYSA return', f'{ANNUAL_INVEST*100:.1f}%/yr', '← same'],
        ['Time value of commute', f'${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS:.0f}/mo', '← same'],
    ]
    story.append(table(param_data, [2.5*inch, 2.0*inch, 2.5*inch]))
    story.append(Spacer(1, 8))

    # Affordability section
    story.append(Paragraph('Affordability Check', S['h1']))
    story.append(Paragraph(
        'The following table shows whether each scheduled purchase is actually affordable '
        'based on projected cash at the time of purchase. If a purchase is not affordable '
        'at the scheduled month, the simulation automatically delays it until cash is sufficient.',
        S['body']))

    ok = lambda x: '✓ Affordable' if x else '✗ Not affordable at scheduled month'
    afford_data = [
        ['Purchase', 'Scheduled Month', 'Cash Available', 'Cost Required', 'Left Over', 'Status'],
        ['Option A — Trailer fixup', 'Month 1',
         f'${afford["a_trailer_starting_cash"]:,.0f}',
         f'${afford["a_trailer_fixup"]:,.0f}',
         f'${afford["a_cash_after_fixup"]:,.0f}',
         ok(afford['a_trailer_affordable'])],
        ['Option A — Permanent home', f'Month {A_MOVEOUT}',
         f'${afford["a_cash_at_moveout"]:,.0f}',
         f'${afford["a_upfront"]:,.0f}',
         f'${afford["a_cash_after_home"]:,.0f}',
         ok(afford['a_affordable'])],
        ['Option B — Buy House 1', 'Month 1',
         f'${afford["b1_starting_cash"]:,.0f}',
         f'${afford["b1_upfront"]:,.0f}',
         f'${afford["b1_cash_after"]:,.0f}',
         ok(afford['b1_affordable'])],
        ['Option B — Buy House 2', f'Month {B_MOVEOUT}',
         f'${afford["b2_cash_at_moveout"]:,.0f}',
         f'${afford["b2_upfront"]:,.0f}',
         f'${afford["b2_cash_after"]:,.0f}',
         ok(afford['b2_affordable'])],
    ]
    afford_ts = TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0), colors.HexColor('#2E5D9A')),
        ('TEXTCOLOR',     (0,0),  (-1,0), colors.white),
        ('FONTNAME',      (0,0),  (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),  (-1,-1), 8),
        ('ROWBACKGROUNDS',(0,1),  (-1,-1), [colors.white, colors.HexColor('#EEF4FF')]),
        ('GRID',          (0,0),  (-1,-1), 0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN',        (0,0),  (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),  (-1,-1), 4),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 4),
        ('TEXTCOLOR',     (5,1),  (5,-1),  colors.HexColor('#1E6B3A')),
        ('FONTNAME',      (5,1),  (5,-1),  'Helvetica-Bold'),
    ])
    story.append(Table(afford_data,
                       colWidths=[1.7*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.0*inch, 1.5*inch],
                       style=afford_ts))

    # Monte Carlo delay stats
    story.append(Spacer(1, 6))
    delay_data = [
        ['', 'Scheduled Month', 'Median Actual Month', '% of Paths Delayed'],
        ['Option A home purchase',
         f'Month {A_MOVEOUT}',
         f'Month {int(base["a_purchase_med"]) if not np.isnan(base["a_purchase_med"]) else "Never"}',
         f'{base["a_purchase_delayed_pct"]:.0f}%'],
        ['Option B House 2 purchase',
         f'Month {B_MOVEOUT}',
         f'Month {int(base["b2_purchase_med"]) if not np.isnan(base["b2_purchase_med"]) else "Never"}',
         f'{base["b2_purchase_delayed_pct"]:.0f}%'],
    ]
    story.append(Paragraph('Purchase Delay Statistics (across all 1,000 Monte Carlo paths):', S['h2']))
    story.append(table(delay_data, [2.2*inch, 1.3*inch, 1.6*inch, 1.6*inch]))
    story.append(Spacer(1, 4))
    story.append(PageBreak())

    # Key results
    story.append(Paragraph('Key Results Summary', S['h1']))
    winner_base = 'B' if base['final_b_nw'] > base['final_a_nw'] else 'A'
    winner_tv   = 'B' if tv['final_b_nw']   > tv['final_a_nw']   else 'A'

    results_data = [
        ['Metric', 'Option A', 'Option B', 'Winner'],
        [f'Mean net worth — Month {MONTHS} (no time value)',
         fmt(base['final_a_nw']), fmt(base['final_b_nw']), winner_base],
        [f'Mean net worth — Month {MONTHS} (with time value)',
         fmt(tv['final_a_nw']), fmt(tv['final_b_nw']), winner_tv],
        ['10th pct net worth (no TV)',
         fmt(base['final_a_p10']), fmt(base['final_b_p10']),
         'B' if base['final_b_p10'] > base['final_a_p10'] else 'A'],
        ['90th pct net worth (no TV)',
         fmt(base['final_a_p90']), fmt(base['final_b_p90']),
         'B' if base['final_b_p90'] > base['final_a_p90'] else 'A'],
        ['Break-even month (median, no TV)',
         '—', f'Month {int(base["be_median"]) if not np.isnan(base["be_median"]) else "Never"}', '—'],
        ['% paths B wins (no TV)', '—', f'{base["be_pct"]:.0f}%', '—'],
        ['Break-even month (median, with TV)',
         '—', f'Month {int(tv["be_median"]) if not np.isnan(tv["be_median"]) else "Never"}', '—'],
        ['% paths B wins (with TV)', '—', f'{tv["be_pct"]:.0f}%', '—'],
        [f'% paths hit ${PASSIVE_GOAL:.0f}/mo passive income',
         'N/A', f'{base["goal_pct"]:.0f}%', '—'],
        [f'Median month goal achieved',
         'N/A',
         f'Month {int(base["goal_median"]) if not np.isnan(base["goal_median"]) else "Never"}',
         '—'],
        ['House 1 equity at final month (B)', '—', fmt(base['b_equity1_mean'][-1]), 'B'],
        ['House 2 equity at final month (B)', '—', fmt(base['b_equity2_mean'][-1]), 'B'],
        ['Total rental income earned (mean)', '—', fmt(float(np.sum(base['rental_mean']))), 'B'],
        ['Total upfront costs (lifecycle)', fmt(TRAILER_FIXUP + A_UPFRONT),
         fmt(B1_UPFRONT + B2_UPFRONT), '—'],
    ]
    ts2 = TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0), colors.HexColor('#2E5D9A')),
        ('TEXTCOLOR',     (0,0),  (-1,0), colors.white),
        ('FONTNAME',      (0,0),  (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),  (-1,-1), 8.5),
        ('ROWBACKGROUNDS',(0,1),  (-1,-1), [colors.white, colors.HexColor('#EEF4FF')]),
        ('GRID',          (0,0),  (-1,-1), 0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN',        (0,0),  (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),  (-1,-1), 3),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 3),
        ('TEXTCOLOR',     (3,1),  (3,-1),  colors.HexColor('#1E6B3A')),
        ('FONTNAME',      (3,1),  (3,-1),  'Helvetica-Bold'),
    ])
    story.append(Table(results_data,
                       colWidths=[2.9*inch, 1.4*inch, 1.5*inch, 0.9*inch],
                       style=ts2))

    # Milestone snapshots
    story.append(Spacer(1, 10))
    story.append(Paragraph('Milestone Snapshots', S['h1']))
    milestones = []
    for yr in [5, 10, 15]:
        mo = yr * 12
        if mo <= MONTHS:
            milestones.append([
                f'Year {yr} (Mo {mo})',
                fmt(base['a_nw_mean'][mo-1]),
                fmt(base['b_nw_mean'][mo-1]),
                fmt(base['b_equity1_mean'][mo-1] + base['b_equity2_mean'][mo-1]),
                f'${base["passive_mean"][mo-1]:,.0f}/mo',
            ])
    ms_data = [['Milestone', 'A Net Worth', 'B Net Worth', 'B Total Equity', 'B Passive Income']] + milestones
    story.append(table(ms_data, [1.3*inch, 1.4*inch, 1.4*inch, 1.4*inch, 1.4*inch]))
    story.append(PageBreak())

    # Charts
    captions = [
        f'Chart 1: Net Worth — {MONTHS//12}-year horizon. Option A (trailer→home) vs Option B (buy→rent→buy). '
        'Shaded bands show P10–P90 Monte Carlo uncertainty. Phase transition lines shown.',
        'Chart 2: Net Worth Gap (B minus A). Above zero = Option B is ahead. '
        'Shows when and by how much each option leads.',
        f'Chart 3: Option B monthly passive income growth. Goal line at ${PASSIVE_GOAL:.0f}/mo. '
        f'{base["goal_pct"]:.0f}% of simulation paths achieve this within {MONTHS//12} years.',
        'Chart 4: Equity comparison. Option A builds equity in one home; '
        'Option B builds stacked equity across two properties.',
        'Chart 5: Break-even distribution — month B net worth first exceeds A for 3+ months.',
        f'Chart 6: Goal achievement distribution — month Option B first sustains ${PASSIVE_GOAL:.0f}/mo passive income.',
        'Chart 7: Cumulative gas costs. Both options transition gas rates at their respective move-out months.',
        'Chart 8: Monthly spending breakdown at Month 1 baseline using actual config values.',
        'Chart 9: Income growth sensitivity — net worth across three raise scenarios.',
        f'Chart 10: House 1 mortgage amortization. '
        f'${B1_PRICE:,.0f} at {B1_APR*100:.1f}% — interest/principal split and equity growth.',
        'Chart 11: Total lifecycle upfront costs. Both options pay twice — Option A pays for '
        'trailer fixup then permanent home; Option B pays for House 1 then House 2.',
    ]
    for cpath, caption in zip(charts, captions):
        story.append(img(cpath, w=6.8))
        story.append(Paragraph(caption, S['caption']))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # Verdict
    story.append(Paragraph('Analyst Verdict', S['h1']))
    margin_base = base['final_b_nw'] - base['final_a_nw']
    margin_tv   = tv['final_b_nw']   - tv['final_a_nw']
    story += [
        Paragraph(
            f'At {MONTHS//12} years, Option {"B" if margin_base > 0 else "A"} leads by '
            f'${abs(margin_base):,.0f} in the base scenario (no time value). '
            f'With ${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS:.0f}/mo commute time value included, '
            f'Option {"B" if margin_tv > 0 else "A"} leads by ${abs(margin_tv):,.0f}.',
            S['body']),
        Paragraph(
            f'Option B achieves the ${PASSIVE_GOAL:.0f}/mo passive income goal in '
            f'{base["goal_pct"]:.0f}% of simulation paths, '
            f'with a median achievement month of '
            f'{int(base["goal_median"]) if not np.isnan(base["goal_median"]) else "N/A"} '
            f'({months_to_date(int(base["goal_median"])) if not np.isnan(base["goal_median"]) else "N/A"}).',
            S['body']),
        Paragraph('Key risks to monitor:', S['h2']),
        Paragraph(f'• Option B cash after House 1 closing: ${STARTING_CASH - B1_UPFRONT:,.0f}. '
                  f'Repair spikes in year 1–2 are the primary short-term risk.', S['bullet']),
        Paragraph(f'• Option A makes two separate purchases totaling ${TRAILER_FIXUP + A_UPFRONT:,.0f} '
                  f'in upfront costs. Option B also pays twice but the second payment '
                  f'(House 2) is partially funded by rental income.', S['bullet']),
        Paragraph(f'• Vacancy risk on House 1 rental modeled at {VACANCY*100:.0f}%. '
                  f'Good tenant screening is worth the time.', S['bullet']),
        Paragraph(f'• If income drops significantly, Option A\'s lower early fixed costs '
                  f'(trailer phase) provide more breathing room.', S['bullet']),
        HR(),
        Paragraph(f'Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}  |  '
                  f'{MC_RUNS:,} Monte Carlo paths  |  {MONTHS}-month horizon', S['caption']),
    ]

    doc.build(story)
    return path


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    afford = affordability_check()

    print(f'\n[1/6] Running base simulation (no time value)...')
    base = monte_carlo(use_time_value=False, income_growth_annual=0.0, label='Base')

    print(f'[2/6] Running time-value simulation...')
    tv = monte_carlo(use_time_value=True, income_growth_annual=0.0, label='With time value')

    print('[3/6] Running income growth scenarios...')
    scenarios = []
    for growth, lbl in [(0.0, 'No raises'), (0.02, '2%/yr raises'), (0.04, '4%/yr raises')]:
        s = monte_carlo(use_time_value=False, income_growth_annual=growth, label=lbl)
        scenarios.append((lbl, s))

    print('[4/6] Generating charts...')
    charts = [
        chart_networth(base, tv),
        chart_nw_gap(base, tv),
        chart_passive(base),
        chart_equity(base),
        chart_breakeven(base, tv),
        chart_goal(base),
        chart_gas(),
        chart_spending(),
        chart_scenarios(scenarios),
        chart_amortization(),
        chart_upfront(),
    ]

    print('[5/6] Building PDF report...')
    pdf_path = build_pdf(base, tv, scenarios, charts, afford)

    print('[6/6] Done.\n')
    print('=' * 65)
    print('  RESULTS SUMMARY')
    print('=' * 65)
    print(f'\n  BASE SCENARIO (no time value):')
    print(f'    Option A final net worth: ${base["final_a_nw"]:>12,.0f}')
    print(f'    Option B final net worth: ${base["final_b_nw"]:>12,.0f}')
    print(f'    Advantage:                ${base["final_b_nw"]-base["final_a_nw"]:>12,.0f}  ({"B" if base["final_b_nw"] > base["final_a_nw"] else "A"})')
    print(f'    B overtakes A (median):   Month {int(base["be_median"]) if not np.isnan(base["be_median"]) else "Never"}')
    print(f'    Paths where B wins:       {base["be_pct"]:.0f}%')
    print(f'\n  WITH TIME VALUE (${HOURLY_TIME_VALUE * EXTRA_COMMUTE_HRS:.0f}/mo):')
    print(f'    Option A final net worth: ${tv["final_a_nw"]:>12,.0f}')
    print(f'    Option B final net worth: ${tv["final_b_nw"]:>12,.0f}')
    print(f'    Advantage:                ${tv["final_b_nw"]-tv["final_a_nw"]:>12,.0f}  ({"B" if tv["final_b_nw"] > tv["final_a_nw"] else "A"})')
    print(f'    Paths where B wins:       {tv["be_pct"]:.0f}%')
    print(f'\n  PASSIVE INCOME GOAL (${PASSIVE_GOAL:.0f}/mo):')
    print(f'    Paths achieving goal:     {base["goal_pct"]:.0f}%')
    print(f'    Median month achieved:    {int(base["goal_median"]) if not np.isnan(base["goal_median"]) else "Never"}')
    print(f'\n  OUTPUT FILES:')
    print(f'    PDF: {pdf_path}')
    for c in charts:
        print(f'    Chart: {c}')
    print()
