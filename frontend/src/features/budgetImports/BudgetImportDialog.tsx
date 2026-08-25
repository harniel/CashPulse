import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import UploadFileIcon from "@mui/icons-material/UploadFile";

import { extractApiErrors } from "../../lib/apiErrors";
import { downloadBudgetImportTemplate } from "./api";
import { useBudgetImportPreview, useConfirmBudgetImport, useUploadBudgetImport } from "./hooks";
import type { BudgetImportRow } from "./types";

interface Props {
  open: boolean;
  onClose: () => void;
}

function initialSelection(rows: BudgetImportRow[]): Set<string> {
  return new Set(rows.filter((row) => row.status === "pending").map((row) => row.id));
}

export function BudgetImportDialog({ open, onClose }: Props) {
  const [batchId, setBatchId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [importedCount, setImportedCount] = useState<number | null>(null);

  const upload = useUploadBudgetImport();
  const preview = useBudgetImportPreview(batchId);
  const confirm = useConfirmBudgetImport();

  const rows = preview.data ?? [];

  const reset = () => {
    setBatchId(null);
    setSelected(new Set());
    setUploadError(null);
    setImportedCount(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploadError(null);
    try {
      const batch = await upload.mutateAsync(file);
      setBatchId(batch.id);
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      setUploadError(fieldErrors.file ?? message ?? "Couldn't upload this file.");
    }
  };

  // Preview just loaded for this batch — default every pending row to selected.
  useEffect(() => {
    if (preview.data) {
      setSelected(initialSelection(preview.data));
    }
  }, [batchId, preview.data]);

  const toggleRow = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleConfirm = async () => {
    if (!batchId) return;
    const result = await confirm.mutateAsync({ batchId, rowIds: Array.from(selected) });
    setImportedCount(result.imported_count);
  };

  const pendingCount = rows.filter((r) => r.status === "pending").length;
  const failedCount = rows.filter((r) => r.status === "failed").length;

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>Import budgets from Excel</DialogTitle>
      <DialogContent>
        {importedCount !== null ? (
          <Alert severity="success" sx={{ mt: 1 }}>
            Imported {importedCount} budget{importedCount === 1 ? "" : "s"}.
          </Alert>
        ) : !batchId ? (
          <Stack spacing={3} sx={{ mt: 1 }}>
            <Stack direction="row" spacing={2} sx={{ alignItems: "flex-start" }}>
              <Chip label="1" size="small" color="primary" sx={{ mt: 0.25 }} />
              <Box>
                <Typography sx={{ fontWeight: 500 }}>Download the template</Typography>
                <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                  An .xlsx with the columns we expect — <strong>Category</strong>,{" "}
                  <strong>Month</strong>, <strong>Amount</strong>, and optionally{" "}
                  <strong>Household</strong> — already filled in as a header row.
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<DownloadIcon />}
                  onClick={() => downloadBudgetImportTemplate()}
                >
                  Download template
                </Button>
              </Box>
            </Stack>

            <Stack direction="row" spacing={2} sx={{ alignItems: "flex-start" }}>
              <Chip label="2" size="small" color="primary" sx={{ mt: 0.25 }} />
              <Box sx={{ flexGrow: 1 }}>
                <Typography sx={{ fontWeight: 500 }}>Fill it in and upload it</Typography>
                <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                  One row per budget. Re-importing the same category and month updates that
                  budget instead of creating a duplicate.
                </Typography>
                {uploadError && (
                  <Alert severity="error" sx={{ mb: 1 }}>
                    {uploadError}
                  </Alert>
                )}
                <Button
                  component="label"
                  variant="contained"
                  startIcon={upload.isPending ? <CircularProgress size={16} /> : <UploadFileIcon />}
                  disabled={upload.isPending}
                >
                  Choose file
                  <input type="file" accept=".xlsx" hidden onChange={handleFileChange} />
                </Button>
              </Box>
            </Stack>
          </Stack>
        ) : preview.isLoading ? (
          <CircularProgress sx={{ mt: 2 }} />
        ) : (
          <Box sx={{ mt: 1 }}>
            <Typography color="text.secondary" sx={{ mb: 1 }}>
              {pendingCount} row{pendingCount === 1 ? "" : "s"} ready to import
              {failedCount > 0 && `, ${failedCount} row${failedCount === 1 ? "" : "s"} with errors`}.
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" />
                  <TableCell>Category</TableCell>
                  <TableCell>Month</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Household</TableCell>
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell padding="checkbox">
                      <Checkbox
                        size="small"
                        checked={selected.has(row.id)}
                        disabled={row.status !== "pending"}
                        onChange={() => toggleRow(row.id)}
                      />
                    </TableCell>
                    <TableCell>{row.raw_data.category}</TableCell>
                    <TableCell>{row.raw_data.month}</TableCell>
                    <TableCell>{row.raw_data.amount}</TableCell>
                    <TableCell>{row.raw_data.household || "—"}</TableCell>
                    <TableCell>
                      {row.status === "failed" ? (
                        <Chip size="small" color="error" label={row.error} />
                      ) : (
                        <Chip
                          size="small"
                          variant="outlined"
                          color={row.action === "update" ? "warning" : "success"}
                          label={row.action === "update" ? "Update" : "Create"}
                        />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>{importedCount !== null ? "Close" : "Cancel"}</Button>
        {batchId && importedCount === null && (
          <Button
            variant="contained"
            onClick={handleConfirm}
            disabled={selected.size === 0 || confirm.isPending}
          >
            {confirm.isPending ? "Importing…" : `Import ${selected.size} row${selected.size === 1 ? "" : "s"}`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
