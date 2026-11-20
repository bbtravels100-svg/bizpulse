from typing import Optional
from .models import (
    BaselineMetric,
    VerificationComparison,
    VerificationOutcome,
    MetricComparisonDirection,
)


def evaluate_metric_comparison(
    baseline: BaselineMetric,
    current_value: Optional[float],
) -> VerificationComparison:
    """
    Deterministic Python calculation of business metrics comparison.
    Strictly performs numerical calculations without any LLM involvement:
      - absolute_change = current_value - baseline_value
      - percentage_change = (absolute_change / baseline_value) * 100
      - outcome determination: Improved, Not Improved, Deteriorated, Inconclusive, Insufficient Data
    """
    # 1. Check for Insufficient Data
    if current_value is None:
        return VerificationComparison(
            metric_name=baseline.metric_name,
            baseline_value=baseline.baseline_value,
            current_value=0.0,
            absolute_change=0.0,
            percentage_change=0.0,
            target_value=baseline.target_value,
            comparison_direction=baseline.comparison_direction,
            target_met=False,
            outcome=VerificationOutcome.INSUFFICIENT_DATA,
            calculation_summary="No current measurement data was supplied. Outcome classified as Insufficient Data.",
        )

    # 2. Guard against invalid or NaN/Infinity numbers
    try:
        curr = float(current_value)
        base = float(baseline.baseline_value)
        target = float(baseline.target_value)
    except (ValueError, TypeError):
        return VerificationComparison(
            metric_name=baseline.metric_name,
            baseline_value=baseline.baseline_value,
            current_value=0.0,
            absolute_change=0.0,
            percentage_change=0.0,
            target_value=baseline.target_value,
            comparison_direction=baseline.comparison_direction,
            target_met=False,
            outcome=VerificationOutcome.INCONCLUSIVE,
            calculation_summary="Supplied metric value could not be parsed numerically.",
        )

    # 3. Deterministic Python Arithmetic
    abs_change = round(curr - base, 4)
    if base != 0:
        pct_change = round((abs_change / abs(base)) * 100, 2)
    else:
        pct_change = 0.0 if abs_change == 0 else 100.0

    # 4. Check whether target threshold was achieved
    direction = baseline.comparison_direction
    if direction == MetricComparisonDirection.INCREASE:
        target_met = curr >= target
    else:
        target_met = curr <= target

    # 5. Classify outcome
    EPSILON = 0.0001
    if direction == MetricComparisonDirection.INCREASE:
        if abs_change > EPSILON:
            outcome = VerificationOutcome.IMPROVED
        elif abs_change < -EPSILON:
            outcome = VerificationOutcome.DETERIORATED
        else:
            outcome = VerificationOutcome.NOT_IMPROVED
    else:  # DECREASE
        if abs_change < -EPSILON:
            outcome = VerificationOutcome.IMPROVED
        elif abs_change > EPSILON:
            outcome = VerificationOutcome.DETERIORATED
        else:
            outcome = VerificationOutcome.NOT_IMPROVED

    # Build summary
    sign = "+" if abs_change > 0 else ""
    summary = (
        f"Baseline: {base} -> Current: {curr} "
        f"(Absolute Change: {sign}{abs_change}, Relative Change: {sign}{pct_change}%). "
        f"Target ({target}): {'Met' if target_met else 'Not Met'}. "
        f"Outcome: {outcome.value}."
    )

    return VerificationComparison(
        metric_name=baseline.metric_name,
        baseline_value=base,
        current_value=curr,
        absolute_change=abs_change,
        percentage_change=pct_change,
        target_value=target,
        comparison_direction=direction,
        target_met=target_met,
        outcome=outcome,
        calculation_summary=summary,
    )
