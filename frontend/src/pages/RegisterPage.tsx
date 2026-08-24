import { Box, Container, Paper } from "@mui/material";

import { RegisterForm } from "../features/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 10 }}>
        <Paper sx={{ p: 4 }} variant="outlined">
          <RegisterForm />
        </Paper>
      </Box>
    </Container>
  );
}
