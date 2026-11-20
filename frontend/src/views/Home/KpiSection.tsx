import { MetricCard } from '../../components/common/MetricCard';
import { Button } from '../../components/common/Button';
import { useApiData } from '../../hooks/useApiData';
import { formatCurrency, formatInteger, formatPercent } from '../../utils/format';
import type { OverviewResponse, ProfitabilityResponse } from '../../types';

export function KpiSection() {
  const overview = useApiData<OverviewResponse>('/api/overview');
  const profit = useApiData<ProfitabilityResponse>('/api/products/profitability');

  // Derived strictly from backend-calculated per-product figures.
  const products = profit.data?.products ?? [];
  const totalProfit = products.reduce((s, p) => s + p.gross_profit, 0);
  const profitBasisRevenue = products.reduce((s, p) => s + p.total_revenue, 0);
  const margin = profitBasisRevenue > 0 ? (totalProfit / profitBasisRevenue) * 100 : null;

  // Percentage change only when the backend comparison has a valid Week 1 base.
  const wow = overview.data?.week_over_week;
  const revenueDelta = wow && wow.period1.revenue > 0 ? wow.percentage_change : undefined;

  const profitEmpty = !profit.loading && !profit.error && products.length === 0;
  const anyError = overview.error ?? profit.error;

  return (
    <section aria-label="Business performance overview">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '0.75rem',
          gap: '0.5rem',
        }}
      >
        <h3 style={{ fontSize: '1rem' }}>Business Performance</h3>
        {anyError && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              overview.reload();
              profit.reload();
            }}
          >
            Retry
          </Button>
        )}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '1rem',
        }}
      >
        <MetricCard
          label="Total Revenue"
          icon="💰"
          loading={overview.loading}
          error={overview.error ?? undefined}
          value={overview.data ? formatCurrency(overview.data.total_revenue) : '—'}
          delta={revenueDelta}
          deltaLabel="Week 2 vs Week 1"
        />
        <MetricCard
          label="Total Profit"
          icon="📈"
          loading={profit.loading}
          error={profit.error ?? undefined}
          value={profitEmpty ? 'No data' : formatCurrency(totalProfit)}
          note="Gross profit across all products"
        />
        <MetricCard
          label="Units Sold"
          icon="🛒"
          loading={overview.loading}
          error={overview.error ?? undefined}
          value={overview.data ? formatInteger(overview.data.total_units_sold) : '—'}
          note="Order counts aren't in the data source; showing units sold"
        />
        <MetricCard
          label="Profit Margin"
          icon="🎯"
          loading={profit.loading}
          error={profit.error ?? undefined}
          value={margin === null ? 'No data' : formatPercent(margin)}
          note="Gross profit ÷ revenue"
        />
      </div>
    </section>
  );
}
