import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  IconButton,
  LinearProgress,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import UploadFileIcon from "@mui/icons-material/UploadFile";

import { BudgetImportDialog } from "../features/budgetImports/BudgetImportDialog";
import { BudgetFormDialog } from "../features/budgets/BudgetFormDialog";
import { useBudgets, useDeleteBudget } from "../features/budgets/hooks";
import type { Budget } from "../features/budgets/types";
import { useCategories } from "../features/categories/hooks";
import { useActiveHousehold } from "../hooks/useActiveHousehold";
import { extractApiErrors } from "../lib/apiErrors";
import { formatMoney } from "../lib/money";

function currentMonth() {
  return new Date().toISOString().slice(0, 7);
}

export default function BudgetsPage() {
  const { activeHouseholdId } = useActiveHousehold();
  const { data: categories = [] } = useCategories();
  const [month, setMonth] = useState(currentMonth());
  const { data: budgets, isLoading } = useBudgets(month, activeHouseholdId);
  const deleteBudget = useDeleteBudget();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | undefined>(undefined);
  const [menuBudget, setMenuBudget] = useState<Budget | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [error, setError] = useState<string | null>(null);

  const categoryName = (id: string) => categories.find((c) => c.id === id)?.name ?? "—";

  const openCreate = () => {
    setEditingBudget(undefined);
    setDialogOpen(true);
  };

  const openEdit = (budget: Budget) => {
    setEditingBudget(budget);
    setDialogOpen(true);
    setMenuAnchor(null);
  };

  const handleDelete = async (budget: Budget) => {
    setMenuAnchor(null);
    try {
      await deleteBudget.mutateAsync(budget.id);
    } catch (submitError) {
      const { message } = extractApiErrors(submitError);
      setError(message ?? "Couldn't delete this budget.");
    }
  };

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h4" component="h1">
          Budgets
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<UploadFileIcon />} onClick={() => setImportDialogOpen(true)}>
            Import
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
            New budget
          </Button>
        </Stack>
      </Stack>

      <TextField
        label="Month"
        type="month"
        size="small"
        value={month}
        onChange={(e) => setMonth(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
        sx={{ mb: 3 }}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading && <CircularProgress />}

      {!isLoading && budgets?.length === 0 && (
        <Typography color="text.secondary">No budgets set for this month yet.</Typography>
      )}

      <Stack spacing={2}>
        {budgets?.map((budget) => {
          const utilization = budget.utilization_pct ? Number(budget.utilization_pct) : 0;
          const overBudget = utilization >= 100;
          return (
            <Card key={budget.id} variant="outlined">
              <CardContent>
                <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                  <Box sx={{ flexGrow: 1, mr: 2 }}>
                    <Typography variant="h6">{categoryName(budget.category)}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatMoney(budget.spent)} of {formatMoney(budget.amount)} spent
                      {budget.daily_recommended_spend !== null &&
                        ` · ${formatMoney(budget.daily_recommended_spend)}/day left`}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(utilization, 100)}
                      color={overBudget ? "error" : utilization >= 80 ? "warning" : "primary"}
                      sx={{ mt: 1, height: 8, borderRadius: 4 }}
                    />
                  </Box>
                  <IconButton
                    onClick={(event) => {
                      setMenuBudget(budget);
                      setMenuAnchor(event.currentTarget);
                    }}
                  >
                    <MoreVertIcon />
                  </IconButton>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      <Menu anchorEl={menuAnchor} open={!!menuAnchor} onClose={() => setMenuAnchor(null)}>
        <MenuItem onClick={() => menuBudget && openEdit(menuBudget)}>Edit</MenuItem>
        <MenuItem onClick={() => menuBudget && handleDelete(menuBudget)}>Delete</MenuItem>
      </Menu>

      <BudgetFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        budget={editingBudget}
        defaultMonth={month}
        defaultHouseholdId={activeHouseholdId}
      />

      <BudgetImportDialog open={importDialogOpen} onClose={() => setImportDialogOpen(false)} />
    </Box>
  );
}
