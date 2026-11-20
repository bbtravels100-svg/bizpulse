import pandas as pd
import numpy as np

def run_verification():
    # 1. Load raw CSVs directly
    sales = pd.read_csv('D:/Bizpulse/backend/data/sales.csv')
    costs = pd.read_csv('D:/Bizpulse/backend/data/costs.csv')
    funnel = pd.read_csv('D:/Bizpulse/backend/data/website_funnel.csv')
    events = pd.read_csv('D:/Bizpulse/backend/data/events.csv')

    print("==================================================")
    print("BIZPULSE BUSINESS DATA ENGINE INDEPENDENT AUDIT")
    print("==================================================")
    print(f"Sales records:   {len(sales)} rows")
    print(f"Costs records:   {len(costs)} rows")
    print(f"Funnel records:  {len(funnel)} rows")
    print(f"Events records:  {len(events)} rows")

    # Problem 1: Revenue decline
    w1 = sales[(sales['date'] >= '2026-11-01') & (sales['date'] <= '2026-11-07')]
    w2 = sales[(sales['date'] >= '2026-11-08') & (sales['date'] <= '2026-11-14')]
    w1_rev = float(w1['revenue'].sum())
    w2_rev = float(w2['revenue'].sum())
    diff = w2_rev - w1_rev
    pct = (diff / w1_rev) * 100

    print("\n--- PROBLEM 1: REVENUE DECLINE ---")
    print(f"Week 1 Total Revenue: ${w1_rev:,.2f}")
    print(f"Week 2 Total Revenue: ${w2_rev:,.2f}")
    print(f"Absolute Difference:  ${diff:,.2f}")
    print(f"Percentage Change:    {pct:.2f}% (Expected: ~ -18.00%)")

    # Problem 2: Product Margins
    agg = sales.groupby('product_id', as_index=False).agg(
        units=('units_sold', 'sum'),
        rev=('revenue', 'sum')
    )
    m = pd.merge(agg, costs, on='product_id')
    m['cost_total'] = m['units'] * m['unit_cost']
    m['profit'] = m['rev'] - m['cost_total']
    m['margin_pct'] = (m['profit'] / m['rev']) * 100

    print("\n--- PROBLEM 2: PRODUCT MARGINS & ANOMALY ---")
    for _, r in m.sort_values('margin_pct').iterrows():
        print(f"Product {r['product_id']} | {r['product_name']:<32} | Units: {r['units']:3d} | Rev: ${r['rev']:>9,.2f} | Cost: ${r['cost_total']:>9,.2f} | Profit: ${r['profit']:>8,.2f} | Margin: {r['margin_pct']:>5.2f}%")

    low_margin = m[m['margin_pct'] < 15.0]
    print(f"\nDetected Low-Margin Products (< 15%): {len(low_margin)}")
    for _, r in low_margin.iterrows():
        print(f"-> {r['product_name']} ({r['product_id']}): {r['margin_pct']:.2f}% margin (Unit Price: ${r['rev']/r['units']:.2f}, Unit Cost: ${r['unit_cost']:.2f})")

    # Problem 3: Funnel & Device Deterioration
    f_w1_d = funnel[(funnel['date'] >= '2026-11-01') & (funnel['date'] <= '2026-11-07') & (funnel['device'] == 'desktop')]
    f_w2_d = funnel[(funnel['date'] >= '2026-11-08') & (funnel['date'] <= '2026-11-14') & (funnel['device'] == 'desktop')]
    f_w1_m = funnel[(funnel['date'] >= '2026-11-01') & (funnel['date'] <= '2026-11-07') & (funnel['device'] == 'mobile')]
    f_w2_m = funnel[(funnel['date'] >= '2026-11-08') & (funnel['date'] <= '2026-11-14') & (funnel['device'] == 'mobile')]

    d_w1_pay_rate = f_w1_d['purchased'].sum() / f_w1_d['reached_payment'].sum() * 100
    d_w2_pay_rate = f_w2_d['purchased'].sum() / f_w2_d['reached_payment'].sum() * 100
    m_w1_pay_rate = f_w1_m['purchased'].sum() / f_w1_m['reached_payment'].sum() * 100
    m_w2_pay_rate = f_w2_m['purchased'].sum() / f_w2_m['reached_payment'].sum() * 100

    d_w1_overall = f_w1_d['purchased'].sum() / f_w1_d['visitors'].sum() * 100
    d_w2_overall = f_w2_d['purchased'].sum() / f_w2_d['visitors'].sum() * 100
    m_w1_overall = f_w1_m['purchased'].sum() / f_w1_m['visitors'].sum() * 100
    m_w2_overall = f_w2_m['purchased'].sum() / f_w2_m['visitors'].sum() * 100

    print("\n--- PROBLEM 3: FUNNEL & DEVICE COMPARISONS ---")
    print(f"Desktop W1: Payment Completion = {d_w1_pay_rate:.2f}%, Overall Conversion = {d_w1_overall:.2f}%")
    print(f"Desktop W2: Payment Completion = {d_w2_pay_rate:.2f}%, Overall Conversion = {d_w2_overall:.2f}% (Change: {((d_w2_pay_rate - d_w1_pay_rate)/d_w1_pay_rate*100):+.2f}%)")
    print(f"Mobile  W1: Payment Completion = {m_w1_pay_rate:.2f}%, Overall Conversion = {m_w1_overall:.2f}%")
    print(f"Mobile  W2: Payment Completion = {m_w2_pay_rate:.2f}%, Overall Conversion = {m_w2_overall:.2f}% (Change: {((m_w2_pay_rate - m_w1_pay_rate)/m_w1_pay_rate*100):+.2f}%)")

    print("\n--- EVENTS TIMELINE AROUND PROBLEM 3 ---")
    for _, e in events.iterrows():
        print(f"[{e['timestamp']}] ({e['event_type']}) on {e['affected_system']}: {e['description']}")

if __name__ == '__main__':
    run_verification()
