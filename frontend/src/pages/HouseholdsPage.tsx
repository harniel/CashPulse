import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

import { CreateHouseholdDialog } from "../features/households/CreateHouseholdDialog";
import { useHouseholds } from "../features/households/hooks";
import { useActiveHousehold } from "../hooks/useActiveHousehold";

export default function HouseholdsPage() {
  const { data: households, isLoading } = useHouseholds();
  const { activeHouseholdId, setActiveHouseholdId } = useActiveHousehold();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4" component="h1">
          Households
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
          New household
        </Button>
      </Stack>

      {isLoading && <CircularProgress />}

      {!isLoading && households?.length === 0 && (
        <Typography color="text.secondary">
          You're not in any households yet. Create one to start sharing expenses.
        </Typography>
      )}

      <Stack spacing={2}>
        {households?.map((household) => (
          <Card key={household.id} variant="outlined">
            <CardActionArea onClick={() => setActiveHouseholdId(household.id)}>
              <CardContent>
                <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
                  <Box>
                    <Typography variant="h6">{household.name}</Typography>
                    <Chip
                      size="small"
                      label={household.my_role}
                      sx={{ textTransform: "capitalize", mt: 0.5 }}
                    />
                  </Box>
                  {activeHouseholdId === household.id && (
                    <Chip color="primary" label="Active" size="small" />
                  )}
                </Stack>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Stack>

      <CreateHouseholdDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </Box>
  );
}
