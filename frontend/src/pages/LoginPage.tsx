import { Box, Container, Paper } from "@mui/material";

import { LoginForm } from "../features/auth/LoginForm";

export default function LoginPage() {
  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 10 }}>
        <Paper sx={{ p: 4 }} variant="outlined">
          <LoginForm />
        </Paper>
      </Box>
    </Container>
  );
}
