import { ViewContainer } from '../../components/layout/ViewContainer';
import { formatLongDate, getGreeting } from '../../utils/format';
import { KpiSection } from './KpiSection';
import { AlertsSection } from './AlertsSection';
import { DepartmentSection } from './DepartmentSection';
import { AssistantSection } from './AssistantSection';

export function HomeView() {
  const now = new Date();

  return (
    <ViewContainer>
      {/* A. Welcome header */}
      <header>
        <div
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            color: 'var(--bp-purple)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          {formatLongDate(now)}
        </div>
        <h2 style={{ fontSize: '1.75rem', letterSpacing: '-0.02em', marginTop: '0.2rem' }}>
          {getGreeting(now)}
        </h2>
        <p style={{ color: 'var(--bp-text-muted)', fontSize: '0.95rem', marginTop: '0.25rem' }}>
          Here&apos;s your business overview — performance, alerts and AI-assisted insights.
        </p>
      </header>

      {/* B. KPIs */}
      <KpiSection />

      {/* E. AI assistant (prominent) */}
      <AssistantSection />

      {/* C + D */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))',
          gap: '1.5rem',
          alignItems: 'start',
        }}
      >
        <AlertsSection />
        <DepartmentSection />
      </div>
    </ViewContainer>
  );
}
