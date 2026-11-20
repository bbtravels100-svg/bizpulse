// ============================================================
// Analytics response types — verified against backend/app/main.py
// and backend/app/analytics/*.py. Keep 1:1 with the real API.
// ============================================================

// ─── /api/overview ───────────────────────────────────────────
export interface RevenuePeriod {
  start_date: string;
  end_date: string;
  revenue: number;
}

export interface RevenueComparison {
  period1: RevenuePeriod;
  period2: RevenuePeriod;
  absolute_change: number;
  percentage_change: number;
  trend: 'declined' | 'increased' | 'flat';
}

export interface FunnelSummary {
  visitors: number;
  reached_cart: number;
  reached_payment: number;
  purchased: number;
  cart_conversion_pct: number;
  payment_step_pct: number;
  payment_completion_pct: number;
  overall_conversion_pct: number;
}

export interface OverviewResponse {
  total_revenue: number;
  total_units_sold: number;
  week_over_week: RevenueComparison;
  overall_funnel: FunnelSummary;
  anomalies_detected_count: number;
  critical_anomalies_count: number;
}

// ─── /api/products/profitability ─────────────────────────────
export interface ProductProfitability {
  product_id: string;
  product_name: string;
  units_sold: number;
  unit_cost: number;
  total_revenue: number;
  total_cost: number;
  gross_profit: number;
  gross_profit_margin_pct: number;
  is_low_margin: boolean;
}

export interface ProfitabilityResponse {
  threshold_used_pct: number;
  total_products: number;
  low_margin_products_count: number;
  products: ProductProfitability[];
}

// ─── /api/funnel ─────────────────────────────────────────────
export interface DeviceFunnelSide {
  period1: FunnelSummary;
  period2: FunnelSummary;
  payment_completion_relative_change_pct: number;
}

export interface MobileFunnelSide extends DeviceFunnelSide {
  deterioration_detected: boolean;
}

export interface FunnelResponse {
  overall_funnel: FunnelSummary;
  device_comparison: {
    period1_dates: { start: string; end: string };
    period2_dates: { start: string; end: string };
    desktop: DeviceFunnelSide;
    mobile: MobileFunnelSide;
  };
}

// ─── /api/anomalies ──────────────────────────────────────────
export interface Anomaly {
  anomaly_id: string;
  title: string;
  category: string;
  severity: string; // backend currently emits "critical" | "warning"
  description: string;
  metric_impact: Record<string, unknown>;
  supporting_evidence: Record<string, unknown>[];
  recommended_actions: string[];
}

export interface AnomaliesResponse {
  count: number;
  anomalies: Anomaly[];
}

// ─── /api/events ─────────────────────────────────────────────
export interface BusinessEvent {
  timestamp: string;
  event_type: string;
  description: string;
  affected_system: string;
}

export interface EventsResponse {
  count: number;
  events: BusinessEvent[];
}
