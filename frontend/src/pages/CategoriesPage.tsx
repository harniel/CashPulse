import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";

import { CreateCategoryDialog } from "../features/categories/CreateCategoryDialog";
import { useCategories, useDeleteCategory } from "../features/categories/hooks";
import type { Category, CategoryKind } from "../features/categories/types";
import { extractApiErrors } from "../lib/apiErrors";

function CategorySection({
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
      <List dense>
        {topLevel.map((category) => (
          <Box key={category.id}>
            <ListItem
              secondaryAction={
                !category.is_system && (
                  <IconButton size="small" onClick={() => onDelete(category)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                )
              }
            >
              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <span>{category.name}</span>
                    {category.is_system && <Chip size="small" label="System" />}
                  </Stack>
                }
              />
            </ListItem>
            {(childrenByParent[category.id] ?? []).map((child) => (
              <ListItem
                key={child.id}
                sx={{ pl: 4 }}
                secondaryAction={
                  !child.is_system && (
                    <IconButton size="small" onClick={() => onDelete(child)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  )
                }
              >
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <span>{child.name}</span>
                      {child.is_system && <Chip size="small" label="System" />}
                    </Stack>
                  }
                />
              </ListItem>
            ))}
          </Box>
        ))}
      </List>
    </Box>
  );
}

export default function CategoriesPage() {
  const { data: categories, isLoading } = useCategories();
  const deleteCategory = useDeleteCategory();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultKind, setDefaultKind] = useState<CategoryKind>("expense");
  const [error, setError] = useState<string | null>(null);

  const sorted = useMemo(() => categories ?? [], [categories]);

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
          <CategorySection
            kind="expense"
            label="Expense"
            categories={sorted}
            onAdd={handleAdd}
            onDelete={handleDelete}
          />
          <CategorySection
            kind="income"
            label="Income"
            categories={sorted}
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
