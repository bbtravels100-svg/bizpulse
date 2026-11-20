import csv
import os
from datetime import date, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 1. Products definition
PRODUCTS = [
    {
        "product_id": "PROD_001",
        "product_name": "Ultra Ergonomic Desk Chair",
        "unit_price": 350.00,
        "unit_cost": 175.00,  # 50.0% margin
    },
    {
        "product_id": "PROD_002",
        "product_name": "Noise-Cancelling Headphones",
        "unit_price": 180.00,
        "unit_cost": 90.00,  # 50.0% margin
    },
    {
        "product_id": "PROD_003",
        "product_name": "Smart Fitness Watch",
        "unit_price": 120.00,
        "unit_cost": 72.00,  # 40.0% margin
    },
    {
        "product_id": "PROD_004",
        "product_name": "Compact Mechanical Keyboard",
        "unit_price": 95.00,
        "unit_cost": 52.25,  # 45.0% margin
    },
    {
        "product_id": "PROD_005",
        "product_name": "Heavy Duty Gaming Monitor Stand",
        "unit_price": 45.00,
        "unit_cost": 43.20,  # 4.0% margin (UNUSUALLY LOW MARGIN!)
    },
]

def generate_costs_csv():
    costs_path = os.path.join(DATA_DIR, "costs.csv")
    with open(costs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_id", "product_name", "unit_cost"])
        for p in PRODUCTS:
            writer.writerow([p["product_id"], p["product_name"], f"{p['unit_cost']:.2f}"])
    print(f"Generated: {costs_path}")

def generate_sales_csv():
    sales_path = os.path.join(DATA_DIR, "sales.csv")
    prices = [p["unit_price"] for p in PRODUCTS]
    start_date = date(2026, 11, 1)

    # Week 1 Units (Day 1 - Day 7): Target total revenue = 85,000.00
    # Day sums: [12130, 11840, 12610, 12150, 12065, 12605, 11600] = 85,000
    w1_units = [
        [16, 18, 12, 10, 20],  # 5600 + 3240 + 1440 + 950 + 900 = 12,130
        [15, 17, 13, 11, 21],  # 5250 + 3060 + 1560 + 1045 + 945 = 11,860 -> wait let's calculate exact
        [17, 19, 11, 10, 20],  # 5950 + 3420 + 1320 + 950 + 900 = 12,540
        [16, 18, 12, 10, 21],  # 5600 + 3240 + 1440 + 950 + 945 = 12,175
        [15, 18, 13, 11, 20],  # 5250 + 3240 + 1560 + 1045 + 900 = 11,995
        [17, 19, 12, 10, 21],  # 5950 + 3420 + 1440 + 950 + 945 = 12,705
        [15, 17, 12, 10, 21],  # 5250 + 3060 + 1440 + 950 + 945 = 11,645
    ]
    # Let's verify sum:
    # 12130 + 11860 + 12540 + 12175 + 11995 + 12705 + 11645 = 85,050
    # To reduce by 50: in day 7, 10 units of PROD_004 ($95) -> 9 units ($95) and 21 of PROD_005 ($45) -> 22 ($45) => diff is -95 + 45 = -50!
    w1_units[6] = [15, 17, 12, 9, 22] # 5250 + 3060 + 1440 + 855 + 990 = 11,595
    # Sum: 12130 + 11860 + 12540 + 12175 + 11995 + 12705 + 11595 = 85,000!

    # Week 2 Units (Day 8 - Day 14): Target total revenue = 69,700.00
    # Day sums: ~ 9,957 per day
    w2_units = [
        [13, 15, 10, 8, 17],  # 4550 + 2700 + 1200 + 760 + 765 = 9,975
        [12, 14, 11, 9, 16],  # 4200 + 2520 + 1320 + 855 + 720 = 9,615
        [14, 16, 9, 8, 18],   # 4900 + 2880 + 1080 + 760 + 810 = 10,430
        [13, 15, 10, 8, 16],  # 4550 + 2700 + 1200 + 760 + 720 = 9,930
        [12, 15, 11, 9, 17],  # 4200 + 2700 + 1320 + 855 + 765 = 9,840
        [14, 15, 10, 8, 18],  # 4900 + 2700 + 1200 + 760 + 810 = 10,370
        [12, 14, 10, 8, 17],  # 4200 + 2520 + 1200 + 760 + 765 = 9,445
    ]
    # Sum w2:
    # 9975 + 9615 + 10430 + 9930 + 9840 + 10370 + 9445 = 69,605
    # Diff to 69,700 is +95. Exactly +1 unit of PROD_004 ($95)!
    # Add 1 unit of PROD_004 to Day 14: [12, 14, 10, 9, 17] => 9445 + 95 = 9,540.
    w2_units[6] = [12, 14, 10, 9, 17]
    # Sum w2: 9975 + 9615 + 10430 + 9930 + 9840 + 10370 + 9540 = 69,700!

    all_units = w1_units + w2_units
    w1_total = sum(sum(u * p for u, p in zip(day, prices)) for day in w1_units)
    w2_total = sum(sum(u * p for u, p in zip(day, prices)) for day in w2_units)
    decline_pct = (w2_total - w1_total) / w1_total

    assert w1_total == 85000.0, f"Expected 85000, got {w1_total}"
    assert w2_total == 69700.0, f"Expected 69700, got {w2_total}"
    assert abs(decline_pct - (-0.18)) < 1e-6, f"Expected -0.18, got {decline_pct}"

    with open(sales_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "product_id", "product_name", "units_sold", "revenue"])
        for day_idx, day_counts in enumerate(all_units):
            current_date = (start_date + timedelta(days=day_idx)).isoformat()
            for prod, units in zip(PRODUCTS, day_counts):
                revenue = round(units * prod["unit_price"], 2)
                writer.writerow([
                    current_date,
                    prod["product_id"],
                    prod["product_name"],
                    units,
                    f"{revenue:.2f}",
                ])
    print(f"Generated: {sales_path} (W1=${w1_total:.2f}, W2=${w2_total:.2f}, Decline={decline_pct*100:.2f}%)")

def generate_website_funnel_csv():
    funnel_path = os.path.join(DATA_DIR, "website_funnel.csv")
    start_date = date(2026, 11, 1)

    # 14 days of data:
    # Week 1 (Days 0-6): Normal desktop and normal mobile
    # Week 2 (Days 7-13): Normal desktop, SEVERELY DETERIORATED mobile payment
    with open(funnel_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "device", "visitors", "reached_cart", "reached_payment", "purchased"])
        
        for day_idx in range(14):
            cur_date = (start_date + timedelta(days=day_idx)).isoformat()
            
            # Desktop metrics (steady across all 14 days)
            # Slight natural weekday/weekend variation
            d_vis = 5000 + (day_idx % 3) * 120 - (day_idx % 2) * 80
            d_cart = int(d_vis * 0.20)
            d_pay = int(d_cart * 0.60)
            d_purch = int(d_pay * 0.75) # 75% payment completion
            writer.writerow([cur_date, "desktop", d_vis, d_cart, d_pay, d_purch])
            
            # Mobile metrics
            m_vis = 8200 + (day_idx % 4) * 150 - (day_idx % 3) * 100
            m_cart = int(m_vis * 0.20)
            m_pay = int(m_cart * 0.60)
            
            if day_idx < 7:
                # Week 1: Healthy payment completion ~75%
                m_purch = int(m_pay * 0.75)
            else:
                # Week 2: Mobile payment checkout bug! Payment completion drops to ~22%
                m_purch = int(m_pay * 0.22)
            
            # Verify funnel constraint: visitors >= reached_cart >= reached_payment >= purchased >= 0
            assert d_vis >= d_cart >= d_pay >= d_purch >= 0
            assert m_vis >= m_cart >= m_pay >= m_purch >= 0
            
            writer.writerow([cur_date, "mobile", m_vis, m_cart, m_pay, m_purch])

    print(f"Generated: {funnel_path}")

def generate_events_csv():
    events_path = os.path.join(DATA_DIR, "events.csv")
    events = [
        {
            "timestamp": "2026-11-03T09:00:00Z",
            "event_type": "marketing_campaign",
            "description": "Launched Early November Digital Ads campaign across social channels",
            "affected_system": "marketing",
        },
        {
            "timestamp": "2026-11-05T14:30:00Z",
            "event_type": "infrastructure",
            "description": "Scheduled database read-replica routine maintenance and optimization",
            "affected_system": "database",
        },
        {
            "timestamp": "2026-11-08T02:15:00Z",
            "event_type": "website_update",
            "description": "Deployed checkout frontend v2.4.0 with revised mobile payment sheet integration",
            "affected_system": "checkout_frontend",
        },
        {
            "timestamp": "2026-11-08T06:45:00Z",
            "event_type": "error_alert",
            "description": "Spike in client-side Javascript exceptions and mobile payment gateway timeouts (HTTP 504)",
            "affected_system": "payment_gateway",
        },
        {
            "timestamp": "2026-11-09T10:30:00Z",
            "event_type": "support_alert",
            "description": "Customer support received surge of 90+ tickets reporting frozen payment on iOS/Android devices",
            "affected_system": "customer_support",
        },
        {
            "timestamp": "2026-11-11T11:00:00Z",
            "event_type": "inventory_audit",
            "description": "Supplier cost revision logged for warehouse peripheral components",
            "affected_system": "inventory",
        },
        {
            "timestamp": "2026-11-13T16:20:00Z",
            "event_type": "incident_investigation",
            "description": "Engineering team began investigating mobile checkout form validation incompatibilities",
            "affected_system": "engineering",
        },
    ]

    with open(events_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "event_type", "description", "affected_system"])
        for ev in events:
            writer.writerow([ev["timestamp"], ev["event_type"], ev["description"], ev["affected_system"]])
    print(f"Generated: {events_path}")

if __name__ == "__main__":
    generate_costs_csv()
    generate_sales_csv()
    generate_website_funnel_csv()
    generate_events_csv()
