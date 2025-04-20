import React, { useEffect, useState } from "react";
import { Container, Typography, Button, Box, Snackbar, Alert } from "@mui/material";
import ExtractionResultsTable from "./components/ExtractionResultsTable";
import axios from "axios";

function App() {
  const [resumes, setResumes] = useState([]);
  const [snackbar, setSnackbar] = useState({ open: false, message: "", severity: "success" });

  useEffect(() => {
    fetchResumes();
  }, []);

  const fetchResumes = async () => {
    const res = await axios.get("http://localhost:8000/resumes");
    setResumes(res.data.map(r => ({ ...r, id: r.id })));
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      await axios.post("http://localhost:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSnackbar({ open: true, message: "Resume uploaded!", severity: "success" });
      fetchResumes();
    } catch (err) {
      setSnackbar({ open: true, message: "Upload failed", severity: "error" });
    }
  };

  return (
    <Container>
      <Typography variant="h3" gutterBottom>Resume Skill Extractor</Typography>
      <Box mb={2}>
        <Button variant="contained" component="label">Upload Resume (PDF)
          <input type="file" hidden accept=".pdf" onChange={handleUpload} />
        </Button>
      </Box>
      <ExtractionResultsTable rows={resumes} onDelete={fetchResumes} />
      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Container>
  );
}

export default App;
