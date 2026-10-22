"""Pure calculations for EJJR demonstration. All monetary values are integer cents."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def dollars(value):
    return f'${value / 100:,.2f}'


def divide_cents(total, count):
    """Spread cents with remainder in last installment."""
    base, rem = divmod(total, count)
    return [base] * (count - 1) + [base + rem]


def generate_schedule(tuition, athletic_fee, aftercare, tefa_award, eligible_athletic,
                      eligible_aftercare, school_year_start, deposit_pct=10,
                      tefa_shares=(25, 25, 50)):
    tuition_c = cents(tuition)
    athletics_c = cents(athletic_fee)
    care_c = cents(aftercare)
    award_c = cents(tefa_award)
    charges = tuition_c + athletics_c + care_c
    eligible = tuition_c + (athletics_c if eligible_athletic else 0) + (care_c if eligible_aftercare else 0)
    tefa = min(award_c, eligible)
    deposit_due = cents(Decimal(tuition_c) / 100 * Decimal(str(deposit_pct)) / 100)
    parent_due = charges - tefa
    if deposit_due > parent_due:
        raise ValueError('The required February deposit exceeds the total parent obligation after TEFA. EJJR must revise its deposit policy or funding allocation to avoid an overpayment.')
    if sum(tefa_shares) != 100:
        raise ValueError('TEFA release percentages must total 100%.')
    parent_monthly = divide_cents(parent_due - deposit_due, 9)
    tefa_tranches = [tefa * tefa_shares[0] // 100, tefa * tefa_shares[1] // 100]
    tefa_tranches.append(tefa - sum(tefa_tranches))
    year = int(school_year_start)
    # Deposit in February before the upcoming school year. Nine installments: July to March.
    entries = [{'date': date(year, 2, 1), 'event':'February deposit (prior school year)', 'parent':deposit_due, 'tefa':0}]
    months = [(year,m) for m in range(7,13)] + [(year+1,m) for m in range(1,4)]
    for i,(y,m) in enumerate(months):
        tranches = {0:tefa_tranches[0], 3:tefa_tranches[1], 7:tefa_tranches[2]}
        entries.append({'date':date(y,m,1), 'event':'Monthly installment', 'parent':parent_monthly[i], 'tefa':tranches.get(i,0)})
    remaining = charges
    for e in entries:
        remaining -= e['parent'] + e['tefa']
        e['balance'] = remaining
    assert remaining == 0
    assert sum(e['parent'] for e in entries) == parent_due
    assert sum(e['tefa'] for e in entries) == tefa
    return {'charges':charges, 'eligible':eligible, 'tefa':tefa, 'deposit':deposit_due,
            'parent_total':parent_due, 'rows':entries}
