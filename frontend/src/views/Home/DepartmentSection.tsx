import { Card } from '../../components/common/Card';
import { EmptyState } from '../../components/common/EmptyState';

/**
 * The backend has no department-level data (no department field in sales,
 * costs, funnel or events datasets), so no department metrics or health
 * scores are shown. Do not add invented values here.
 */
export function DepartmentSection() {
  return (
    <Card header="🏢 Department Overview" padding="1.25rem">
      <EmptyState
        icon="🔌"
        title="Department data not connected yet"
        description="BizPulse currently analyses sales, product costs, website funnel and operational events. None of these sources is broken down by department, so department performance isn't shown until one is connected."
      />
    </Card>
  );
}
