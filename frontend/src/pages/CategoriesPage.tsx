import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";

import { CreateCategoryDialog } from "../features/categories/CreateCategoryDialog";
import { useCategories, useDeleteCategory } from "../features/categories/hooks";
import type { Category, CategoryKind } from "../features/categories/types";
import { extractApiErrors } from "../lib/apiErrors";

function CategoryTable({
  kind,
  label,
  categories,
  onAdd,
  onDelete,
}: {
  kind: CategoryKind;
  label: string;
  categories: Category[];
  onAdd: (kind: CategoryKind) => void;
  onDelete: (category: Category) => void;
}) {
  const topLevel = categories.filter((c) => c.kind === kind && c.parent === null);
  const childrenByParent = categories.reduce<Record<string, Category[]>>((acc, c) => {
    if (c.kind === kind && c.parent) {
      (acc[c.parent] ??= []).push(c);
    }
    return acc;
  }, {});

  return (
    <Box sx={{ mb: 4 }}>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h6">{label}</Typography>
        <Button size="small" startIcon={<AddIcon />} onClick={() => onAdd(kind)}>
          Add
        </Button>
      </Stack>

      {topLevel.length === 0 ? (
        <Typography color="text.secondary">No {label.toLowerCase()} categories yet.</Typography>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600, width: "30%" }}>Category</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Subcategories</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, width: 64 }} />
              </TableRow>
            </TableHead>
            <TableBody>
              {topLevel.map((category) => {
                const children = childrenByParent[category.id] ?? [];
                return (
                  <TableRow key={category.id} hover>
                    <TableCell>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {category.name}
                        </Typography>
                        {category.is_system && <Chip size="small" label="System" variant="outlined" />}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      {children.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">
                          —
                        </Typography>
                      ) : (
                        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                          {children.map((child) => (
                            <Chip
                              key={child.id}
                              size="small"
                              label={child.name}
                              variant={child.is_system ? "outlined" : "filled"}
                              onDelete={child.is_system ? undefined : () => onDelete(child)}
                            />
                          ))}
                        </Stack>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {!category.is_system && (
                        <IconButton size="small" onClick={() => onDelete(category)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}

export default function CategoriesPage() {
  const { data: categories, isLoading } = useCategories();
  const deleteCategory = useDeleteCategory();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultKind, setDefaultKind] = useState<CategoryKind>("expense");
  const [error, setError] = useState<string | null>(null);

  const handleAdd = (kind: CategoryKind) => {
    setDefaultKind(kind);
    setDialogOpen(true);
  };

  const handleDelete = async (category: Category) => {
    try {
      await deleteCategory.mutateAsync(category.id);
    } catch (submitError) {
      const { message } = extractApiErrors(submitError);
      setError(message ?? "This category has transactions and can't be deleted.");
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Categories
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading && <CircularProgress />}

      {!isLoading && (
        <>
          <CategoryTable
            kind="expense"
            label="Expense"
            categories={categories ?? []}
            onAdd={handleAdd}
            onDelete={handleDelete}
          />
          <CategoryTable
            kind="income"
            label="Income"
            categories={categories ?? []}
            onAdd={handleAdd}
            onDelete={handleDelete}
          />
        </>
      )}

      <CreateCategoryDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        defaultKind={defaultKind}
      />
    </Box>
  );
}
