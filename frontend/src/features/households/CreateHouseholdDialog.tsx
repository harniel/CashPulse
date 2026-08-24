import { useState } from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";

import { extractApiErrors } from "../../lib/apiErrors";
import { useCreateHousehold } from "./hooks";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CreateHouseholdDialog({ open, onClose }: Props) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createHousehold = useCreateHousehold();

  const handleClose = () => {
    setName("");
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    setError(null);
    try {
      await createHousehold.mutateAsync(name);
      handleClose();
    } catch (submitError) {
      const { fieldErrors, message } = extractApiErrors(submitError);
      setError(fieldErrors.name ?? message ?? "Couldn't create the household.");
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
      <DialogTitle>New household</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          autoFocus
          fullWidth
          label="Household name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. The Smiths"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!name.trim() || createHousehold.isPending}
        >
          Create
        </Button>
      </DialogActions>
    </Dialog>
  );
}
