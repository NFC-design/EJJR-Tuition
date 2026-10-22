import csv
import io
from datetime import date
import streamlit as st
from calculator import generate_schedule, dollars

st.set_page_config(page_title='EJJR Tuition Planner', page_icon='🎓', layout='wide')
st.title('🎓 EJJR Tuition & Payment Planner')
st.caption('Planning prototype for the 2027–2028 school year • Sample rates until approved by EJJR')
st.info('This is a planning tool, not an official EJJR invoice or TEFA award confirmation. Tuition rates, eligibility, deposit policy, and TEFA release timing must be verified.')

# The school can edit these amounts in this demo. In a real parent-facing app,
# these must be moved to administrator-only configuration.
DEFAULT_RATES = {
    'Pre-K 3': 0, 'Pre-K 4': 0, 'Kindergarten': 0,
    'First Grade': 15500, 'Second Grade': 0, 'Third Grade': 0,
    'Fourth Grade': 0, 'Fifth Grade': 0, 'Sixth Grade': 0,
    'Seventh Grade': 0, 'Eighth Grade': 0,
}

with st.expander('⚙️ School setup — edit sample tuition and funding assumptions', expanded=False):
    st.warning('Prototype only: these settings are not password-protected and changes are not permanently saved. Do not publish a real parent version with editable school rates.')
    school_year = st.number_input('Starting calendar year (July)', min_value=2026, max_value=2040, value=2027, step=1)
    deposit_pct = st.number_input('February deposit (% of base tuition)', min_value=0, max_value=100, value=10, step=1)
    st.write('**Grade-level base tuition ($)** — 0 means rate not yet provided.')
    rate_values = {}
    cols = st.columns(3)
    for i, (name, default) in enumerate(DEFAULT_RATES.items()):
        with cols[i % 3]:
            rate_values[name] = st.number_input(name, min_value=0, max_value=100000, value=default, step=100, key=f'rate_{name}')
    st.write('**Fees and TEFA schedule**')
    pre_k_fee = st.number_input('Pre-K athletic fee ($)', min_value=0, value=300, step=25)
    older_fee = st.number_input('Other grades athletic fee ($)', min_value=0, value=800, step=25)
    default_award = st.number_input('Sample TEFA award ($)', min_value=0, value=10474, step=100)
    st.caption('Illustrative 25% July / 25% October / 50% February release pattern. Update when 2027–2028 terms are confirmed.')
    a, b, c = st.columns(3)
    with a: share_july = st.number_input('July funding %', 0, 100, 25)
    with b: share_oct = st.number_input('October funding %', 0, 100, 25)
    with c: share_feb = st.number_input('February funding %', 0, 100, 50)
    athletics_eligible = st.checkbox('Assume athletic fee is TEFA-eligible', value=False,
                                     help='Only enable once eligibility is confirmed for the particular charge.')
    aftercare_eligible = st.checkbox('Assume after-school care is TEFA-eligible', value=False,
                                    help='Default is no; after-school supervision should not be assumed TEFA-eligible.')

st.subheader('Build a family payment schedule')
left, right = st.columns(2)
with left:
    grade = st.selectbox('Grade entering', list(DEFAULT_RATES.keys()), index=3)
    aftercare = st.checkbox('Include optional after-school care', value=False)
    care_amount = st.number_input('Annual after-school care charge ($)', min_value=0, value=0, step=100, disabled=not aftercare)
with right:
    tefa_status = st.selectbox('TEFA status', ['No award', 'Award pending (estimate)', 'Award approved'])
    award = st.number_input('TEFA award amount ($)', min_value=0, value=int(default_award), step=100,
                            disabled=(tefa_status == 'No award'))
    st.caption('Pending awards are projections only. Approved awards still require eligible charges and actual disbursement.')

tuition = rate_values[grade]
athletic_fee = pre_k_fee if grade.startswith('Pre-K') else older_fee
applied_award = 0 if tefa_status == 'No award' else award

if tuition == 0:
    st.warning(f'The base tuition for {grade} has not been entered. Open School setup to enter the approved rate before generating a schedule.')
elif share_july + share_oct + share_feb != 100:
    st.error('The July, October, and February TEFA percentages must total 100%.')
else:
    try:
        result = generate_schedule(tuition, athletic_fee, care_amount if aftercare else 0,
                                   applied_award, athletics_eligible, aftercare_eligible,
                                   school_year, deposit_pct, (share_july, share_oct, share_feb))
    except ValueError as exc:
        st.error(str(exc))
    else:
        a,b,c = st.columns(3)
        a.metric('Total charges', dollars(result['charges']))
        b.metric('Projected TEFA applied', dollars(result['tefa']))
        c.metric('Parent total', dollars(result['parent_total']))
        st.write(f'**Breakdown:** tuition {dollars(tuition*100)} + athletics {dollars(athletic_fee*100)} + after-school care {dollars((care_amount if aftercare else 0)*100)}')
        if tefa_status == 'Award pending (estimate)':
            st.warning('TEFA is still pending. The parent amounts below depend on approval and should not be presented as guaranteed.')
        st.subheader('Payment timeline')
        output = []
        for r in result['rows']:
            output.append({'Due date':r['date'].isoformat(), 'Event':r['event'],
                           'Parent payment':dollars(r['parent']), 'TEFA projected':dollars(r['tefa']),
                           'Remaining balance':dollars(r['balance'])})
        st.dataframe(output, use_container_width=True, hide_index=True)
        st.success('Projected final balance: $0.00 — assuming all scheduled parent payments and TEFA credits are received and applied.')
        st.caption('Positive interim balances represent EJJR funds not yet collected; they are NOT additional parent bills. The model spreads the remaining parent obligation evenly after the deposit, with rounding reconciled in March. Actual TEFA invoices, eligibility, and receipt dates may differ.')
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(output[0].keys()))
        writer.writeheader()
        writer.writerows(output)
        st.download_button('⬇️ Download schedule (CSV / Excel-compatible)', out.getvalue(),
                           file_name=f'ejjr_{grade.lower().replace(" ", "_")}_{school_year}_schedule.csv',
                           mime='text/csv')

st.divider()
st.caption('No student names, account numbers, or other personal identifiers are collected or stored in this prototype. Always verify TEFA requirements and EJJR policies before issuing official schedules.')
