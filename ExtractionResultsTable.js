import React, { useState } from "react";
import { DataGrid } from "@mui/x-data-grid";
// eslint-disable-next-line
import { Chip, Box, Button, Modal, Typography, TextField } from '@mui/material';

// eslint-disable-next-line
const style = {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 400,
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};


export default function ExtractionResultsTable({ rows, onDelete }) {
  const [statuses, setStatuses] = useState({});
  // eslint-disable-next-line
  const [open, setOpen] = useState(false);
  // eslint-disable-next-line
  const [modalData, setModalData] = useState(null);
  // eslint-disable-next-line
  const [skillFilter, setSkillFilter] = useState("");

  // Modal logic for work experience
  // eslint-disable-next-line
  const handleOpenModal = (row) => {
    setModalData(row.work_experience);
    setOpen(true);
  };
  // eslint-disable-next-line
  const handleClose = () => setOpen(false);

  // Delete resume logic (calls backend and triggers parent refresh)
  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this resume?")) {
      try {
        await fetch(`http://localhost:8000/resume/${id}`, { method: 'DELETE' });
        if (onDelete) onDelete();
      } catch (err) {
        alert('Failed to delete resume.');
      }
    }
  };

  // Show all skills as tags
  const columns = [
    { field: "name", headerName: "Name", width: 180 },
    { field: "email", headerName: "Email", width: 200 },
    { field: "phone", headerName: "Phone", width: 140 },
    {
      field: "skills",
      headerName: "Skills",
      width: 300,
      valueGetter: (params) => {
        if (Array.isArray(params.row.skills)) return params.row.skills;
        if (typeof params.row.skills === "string") return params.row.skills.split(",").map(s => s.trim()).filter(Boolean);
        return [];
      },
      renderCell: (params) => (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {params.value.map(skill => (
            <Chip key={skill} label={skill} size="small" sx={{ mb: 0.5, bgcolor: '#e3f2fd', color: '#1565c0', fontWeight: 500, border: '1px solid #90caf9' }} />
          ))}
        </Box>
      ),
    },

    {
      field: "review_status",
      headerName: "Status",
      width: 140,
      renderCell: (params) => {
        const value = statuses[params.row.id] || "Review";
        let chipColor = 'default';
        if (value === "Accept") chipColor = 'success';
        else if (value === "Reject") chipColor = 'error';
        return (
          <Box>
            <Chip
              label={value}
              color={chipColor}
              sx={{ fontWeight: 'bold', minWidth: 80, cursor: 'pointer' }}
              onClick={e => {
                // Show dropdown on click
                const next = value === "Review" ? "Accept" : value === "Accept" ? "Reject" : "Review";
                setStatuses({ ...statuses, [params.row.id]: next });
              }}
            />
          </Box>
        );
      },
    },
    {
      field: "total_experience",
      headerName: "Work Experience (Years)",
      width: 180,
      renderCell: (params) => (
        <Typography variant="h5" sx={{ fontWeight: 700, color: '#1976d2', textAlign: 'center', width: '100%' }}>
          {typeof params.row.total_experience === 'number' ? params.row.total_experience : 0}
        </Typography>
      ),
    },
    {
      field: "delete",
      headerName: "Delete",
      width: 100,
      renderCell: (params) => (
        <Button variant="contained" color="error" size="small" onClick={() => handleDelete(params.row.id)}>
          Delete
        </Button>
      ),
    },
  ];


  // Skill filter logic
  // Filtering logic for all columns
  const [filters, setFilters] = useState({});
  const filteredRows = rows.filter(row => {
    // Skills filter (from the input above the table)
    if (filters.skills) {
      const skills = Array.isArray(row.skills) ? row.skills : (row.skills || '').split(',');
      if (!skills.some(s => s.toLowerCase().includes(filters.skills.toLowerCase()))) return false;
    }
    // Status filter (dropdown above table)
    const effectiveStatus = statuses[row.id] || row.review_status || 'Review';
    if (filters.review_status && filters.review_status !== 'All' && effectiveStatus !== filters.review_status) return false;

    return true;
  });

  return (
    <>

      {/* Filter by Skill and Status above the table */}
    <Box mb={2} display="flex" alignItems="center" gap={2}>
      <input
        type="text"
        placeholder="Filter by Skill"
        value={filters.skills || ''}
        onChange={e => setFilters(f => ({ ...f, skills: e.target.value }))}
        style={{ width: 200, padding: 6, borderRadius: 6, border: '1.5px solid #1976d2', fontSize: 16 }}
      />
      {/* Status dropdown filter */}
      <select
        value={filters.review_status || 'All'}
        onChange={e => setFilters(f => ({ ...f, review_status: e.target.value }))}
        style={{ width: 160, padding: 6, borderRadius: 6, border: '1.5px solid #1976d2', fontSize: 16 }}
      >
        <option value="All">All Statuses</option>
        <option value="Review">Review</option>
        <option value="Accept">Accept</option>
        <option value="Reject">Reject</option>
      </select>
    </Box>
    <div style={{ height: 500, width: "100%", background: '#f7fafc', borderRadius: 12, boxShadow: '0 2px 12px #e0e0e0' }}>
      <DataGrid
        rows={filteredRows}
        columns={columns.map(col => ({
          ...col,
          renderHeader: (params) => (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', pb: 1, width: '100%' }}>
              <div style={{ fontWeight: 'bold', fontSize: 18, letterSpacing: 0.5, marginBottom: 2, color: '#1976d2' }}>{col.headerName}</div>

            </Box>
          )
        }))}
        pageSize={10}
        getRowHeight={() => 70}
        sx={{
          '& .MuiDataGrid-row': { alignItems: 'flex-start', minHeight: 60 },
          '& .MuiDataGrid-cell': {
            background: '#ffffff',
            py: 1,
            whiteSpace: 'normal',
            wordBreak: 'break-word',
            fontWeight: 500,
          },
          '& .MuiDataGrid-columnHeaders': { background: '#e3f2fd' },
          '& .MuiDataGrid-columnHeaderTitle': { fontWeight: 'bold', color: '#1976d2' },
          '& .MuiDataGrid-footerContainer': { background: '#e3f2fd' },
        }}
      />
    </div>

    </>
  );
}
