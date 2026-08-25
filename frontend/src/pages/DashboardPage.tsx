import { Alert, Box, Card, CardContent, Grid, LinearProgress, Stack, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { LineChart } from "@mui/x-charts/LineChart";
import { PieChart } from "@mui/x-charts/PieChart";

import { useDashboardSummary } from "../features/dashboard/hooks";
import type { InsightType } from "../features/dashboard/types";
import { useActiveHousehold } from "../hooks/useActiveHousehold";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { formatMoney } from "../lib/money";

const INSIGHT_SEVERITY: Record<InsightType, "error" | "warning"> = {
  budget_exceeded: "error",
  budget_approaching: "warning",
  negative_cash_flow: "warning",
};

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Card variant="outlined" sx={{ flex: 1 }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" sx={{ color }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const user = useCurrentUser();
  const { activeHouseholdId } = useActiveHousehold();
  const { data, isLoading, error } = useDashboardSummary(activeHouseholdId);

  if (isLoading) {
    return <LinearProgress />;
  }

  if (error || !data) {
    return <Alert severity="error">Couldn't load the dashboard. Try again in a moment.</Alert>;
  }

  const monthLabels = data.charts.cash_flow_by_month.map((row) =>
    new Date(`${row.month}T00:00:00`).toLocaleDateString(undefined, { month: "short" }),
  );

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome{user ? `, ${user.first_name || user.email}` : ""}
      </Typography>

      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <StatCard
          label="Net cash flow (this month)"
          value={formatMoney(data.net_cash_flow)}
          color={Number(data.net_cash_flow) < 0 ? "error.main" : "success.main"}
        />
        <StatCard
          label="Savings rate"
          value={data.savings_rate_pct !== null ? `${data.savings_rate_pct}%` : "—"}
        />
        <StatCard label="Net worth" value={formatMoney(data.net_worth)} />
      </Stack>

      {data.insights.length > 0 && (
        <Stack spacing={1} sx={{ mb: 3 }}>
          {data.insights.map((insight, index) => (
            <Alert key={index} severity={INSIGHT_SEVERITY[insight.type]}>
              {insight.message}
            </Alert>
          ))}
        </Stack>
      )}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Cash flow (last 6 months)
              </Typography>
              <BarChart
                height={260}
                series={[
                  {
                    data: data.charts.cash_flow_by_month.map((row) => Number(row.income)),
                    label: "Income",
                    color: "#2e7d32",
                  },
                  {
                    data: data.charts.cash_flow_by_month.map((row) => Number(row.expense)),
                    label: "Expense",
                    color: "#c62828",
                  },
                ]}
                xAxis={[{ scaleType: "band", data: monthLabels }]}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Net worth (last 6 months)
              </Typography>
              <LineChart
                height={260}
                series={[
                  {
                    data: data.charts.net_worth_by_month.map((row) => Number(row.net_worth)),
                    label: "Net worth",
                    color: "#1e5f4f",
                  },
                ]}
                xAxis={[{ scaleType: "point", data: monthLabels }]}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Spending by category (this month)
              </Typography>
              {data.charts.spending_by_category.length === 0 ? (
                <Typography color="text.secondary">No expenses recorded this month yet.</Typography>
              ) : (
                <PieChart
                  height={260}
                  series={[
                    {
                      data: data.charts.spending_by_category.map((row) => ({
                        id: row.category_id,
                        value: Number(row.amount),
                        label: row.category,
                      })),
                    },
                  ]}
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Budget utilization (this month)
              </Typography>
              {data.charts.budget_utilization.length === 0 ? (
                <Typography color="text.secondary">No budgets set for this month yet.</Typography>
              ) : (
                <Stack spacing={2}>
                  {data.charts.budget_utilization.map((budget) => {
                    const pct = budget.utilization_pct ? Number(budget.utilization_pct) : 0;
                    return (
                      <Box key={budget.budget_id}>
                        <Stack direction="row" sx={{ justifyContent: "space-between" }}>
                          <Typography variant="body2">{budget.category}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {formatMoney(budget.spent)} / {formatMoney(budget.amount)}
                          </Typography>
                        </Stack>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(pct, 100)}
                          color={pct >= 100 ? "error" : pct >= 80 ? "warning" : "primary"}
                          sx={{ height: 8, borderRadius: 4, mt: 0.5 }}
                        />
                      </Box>
                    );
                  })}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
