import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import MoreVertIcon from "@mui/icons-material/MoreVert";

import { AccountFormDialog } from "../features/accounts/AccountFormDialog";
import { useAccounts, useDeleteAccount, useUpdateAccount } from "../features/accounts/hooks";
import type { Account } from "../features/accounts/types";
import { extractApiErrors } from "../lib/apiErrors";
import { formatMoney } from "../lib/money";

export default function AccountsPage() {
  const { data: accounts, isLoading } = useAccounts();
  const updateAccount = useUpdateAccount();
  const deleteAccount = useDeleteAccount();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | undefined>(undefined);
  const [menuAccount, setMenuAccount] = useState<Account | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [error, setError] = useState<string | null>(null);

  const openCreate = () => {
    setEditingAccount(undefined);
    setDialogOpen(true);
  };

  const openEdit = (account: Account) => {
    setEditingAccount(account);
    setDialogOpen(true);
    setMenuAnchor(null);
  };

  const toggleActive = async (account: Account) => {
    setMenuAnchor(null);
    try {
      await updateAccount.mutateAsync({ id: account.id, payload: { is_active: !account.is_active } });
    } catch (submitError) {
      const { message } = extractApiErrors(submitError);
      setError(message ?? "Couldn't update the account.");
    }
  };

  const handleDelete = async (account: Account) => {
    setMenuAnchor(null);
    try {
      await deleteAccount.mutateAsync(account.id);
    } catch (submitError) {
      const { message } = extractApiErrors(submitError);
      setError(message ?? "This account has transactions and can't be deleted.");
    }
  };

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4" component="h1">
          Accounts
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          New account
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading && <CircularProgress />}

      {!isLoading && accounts?.length === 0 && (
        <Typography color="text.secondary">
          No accounts yet — add one to start tracking transactions.
        </Typography>
      )}

      <Stack spacing={2}>
        {accounts?.map((account) => (
          <Card key={account.id} variant="outlined" sx={{ opacity: account.is_active ? 1 : 0.6 }}>
            <CardContent>
              <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <Box>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <Typography variant="h6">{account.name}</Typography>
                    {!account.is_active && <Chip size="small" label="Inactive" />}
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {account.account_type_display}
                    {account.institution ? ` · ${account.institution}` : ""}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                  <Typography variant="h6">{formatMoney(account.balance, account.currency)}</Typography>
                  <IconButton
                    onClick={(event) => {
                      setMenuAccount(account);
                      setMenuAnchor(event.currentTarget);
                    }}
                  >
                    <MoreVertIcon />
                  </IconButton>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Menu anchorEl={menuAnchor} open={!!menuAnchor} onClose={() => setMenuAnchor(null)}>
        <MenuItem onClick={() => menuAccount && openEdit(menuAccount)}>Edit</MenuItem>
        <MenuItem onClick={() => menuAccount && toggleActive(menuAccount)}>
          {menuAccount?.is_active ? "Deactivate" : "Activate"}
        </MenuItem>
        <MenuItem onClick={() => menuAccount && handleDelete(menuAccount)}>Delete</MenuItem>
      </Menu>

      <AccountFormDialog open={dialogOpen} onClose={() => setDialogOpen(false)} account={editingAccount} />
    </Box>
  );
}
