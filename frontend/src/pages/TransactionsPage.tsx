import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  MenuItem,
  Pagination,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/EditOutlined";

import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
import { TransactionFormDialog } from "../features/transactions/TransactionFormDialog";
import { useDeleteTransaction, useTransactions } from "../features/transactions/hooks";
import type { Transaction, TransactionType } from "../features/transactions/types";
import { useActiveHousehold } from "../hooks/useActiveHousehold";
import { extractApiErrors } from "../lib/apiErrors";
import { formatMoney } from "../lib/money";

const PAGE_SIZE = 25;

export default function TransactionsPage() {
  const { activeHouseholdId } = useActiveHousehold();
  const { data: accounts = [] } = useAccounts();
  const { data: categories = [] } = useCategories();
  const deleteTransaction = useDeleteTransaction();

  const [typeFilter, setTypeFilter] = useState<TransactionType | "">("");
  const [accountFilter, setAccountFilter] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const scopeFilter = useMemo(
    () => (activeHouseholdId ? { household: activeHouseholdId } : { is_shared: false as const }),
    [activeHouseholdId],
  );

  const filters = useMemo(
    () => ({
      ...scopeFilter,
      ...(typeFilter ? { type: typeFilter } : {}),
      ...(accountFilter ? { account: accountFilter } : {}),
    }),
    [scopeFilter, typeFilter, accountFilter],
  );

  const { data, isLoading } = useTransactions(filters, page);

  const accountName = (id: string) => accounts.find((a) => a.id === id)?.name ?? "—";
  const categoryName = (id: string | null) => {
    if (!id) return "—";
    const category = categories.find((c) => c.id === id);
    if (!category) return "—";
    const parent = category.parent ? categories.find((p) => p.id === category.parent) : null;
    return parent ? `${parent.name} > ${category.name}` : category.name;
  };

  const openCreate = () => {
    setEditingTransaction(undefined);
    setDialogOpen(true);
  };

  const openEdit = (transaction: Transaction) => {
    setEditingTransaction(transaction);
    setDialogOpen(true);
  };

  const handleDelete = async (transaction: Transaction) => {
    try {
      await deleteTransaction.mutateAsync(transaction.id);
    } catch (submitError) {
      const { message } = extractApiErrors(submitError);
      setError(message ?? "Couldn't delete this transaction.");
    }
  };

  const amountDisplay = (transaction: Transaction) => {
    if (transaction.type === "income") {
      return { text: `+${formatMoney(transaction.amount, transaction.currency)}`, color: "success.main" };
    }
    if (transaction.type === "expense") {
      return { text: `-${formatMoney(transaction.amount, transaction.currency)}`, color: "error.main" };
    }
    return { text: formatMoney(transaction.amount, transaction.currency), color: "text.primary" };
  };

  const pageCount = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h4" component="h1">
          Transactions
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          New transaction
        </Button>
      </Stack>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          select
          label="Type"
          size="small"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value as TransactionType | "");
            setPage(1);
          }}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="">All types</MenuItem>
          <MenuItem value="income">Income</MenuItem>
          <MenuItem value="expense">Expense</MenuItem>
          <MenuItem value="transfer">Transfer</MenuItem>
        </TextField>
        <TextField
          select
          label="Account"
          size="small"
          value={accountFilter}
          onChange={(e) => {
            setAccountFilter(e.target.value);
            setPage(1);
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All accounts</MenuItem>
          {accounts.map((a) => (
            <MenuItem key={a.id} value={a.id}>
              {a.name}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading && <CircularProgress />}

      {!isLoading && data?.results.length === 0 && (
        <Typography color="text.secondary">No transactions yet.</Typography>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Category / To</TableCell>
                <TableCell>Account</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Amount</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {data.results.map((transaction) => {
                const amount = amountDisplay(transaction);
                return (
                  <TableRow key={transaction.id} hover>
                    <TableCell>{transaction.date}</TableCell>
                    <TableCell>{transaction.description || "—"}</TableCell>
                    <TableCell>
                      {transaction.type === "transfer"
                        ? `→ ${accountName(transaction.to_account ?? "")}`
                        : categoryName(transaction.category)}
                    </TableCell>
                    <TableCell>{accountName(transaction.account)}</TableCell>
                    <TableCell>
                      <Chip size="small" label={transaction.type_display} />
                    </TableCell>
                    <TableCell align="right" sx={{ color: amount.color, fontWeight: 500 }}>
                      {amount.text}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => openEdit(transaction)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleDelete(transaction)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {pageCount > 1 && (
        <Stack direction="row" sx={{ justifyContent: "center", mt: 2 }}>
          <Pagination count={pageCount} page={page} onChange={(_, value) => setPage(value)} />
        </Stack>
      )}

      <TransactionFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        transaction={editingTransaction}
        defaultHouseholdId={activeHouseholdId}
      />
    </Box>
  );
}
