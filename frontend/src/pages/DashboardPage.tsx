import { Box, Typography } from "@mui/material";

import { useCurrentUser } from "../hooks/useCurrentUser";

export default function DashboardPage() {
  const user = useCurrentUser();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome{user ? `, ${user.first_name || user.email}` : ""}
      </Typography>
      <Typography color="text.secondary">
        The dashboard summary (net cash flow, savings rate, net worth, charts, and insights) isn't
        built yet — this page is a placeholder while Accounts, Categories, and Transactions get
        their own screens first.
      </Typography>
    </Box>
  );
}
