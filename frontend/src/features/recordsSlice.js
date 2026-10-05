import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import api from "../services/api";


export const fetchRecords = createAsyncThunk(
  "records/fetchRecords",
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get("/records");
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch records."
      );
    }
  }
);


export const createRecord = createAsyncThunk(
  "records/createRecord",
  async (recordData, { rejectWithValue }) => {
    try {
      const response = await api.post("/records", recordData);
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to create record."
      );
    }
  }
);


export const updateRecordAsync = createAsyncThunk(
  "records/updateRecord",
  async ({ id, recordData }, { rejectWithValue }) => {
    try {
      const response = await api.put(`/records/${id}`, recordData);
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to update record."
      );
    }
  }
);


export const deleteRecordAsync = createAsyncThunk(
  "records/deleteRecord",
  async (id, { rejectWithValue }) => {
    try {
      await api.delete(`/records/${id}`);
      return id;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to delete record."
      );
    }
  }
);


const recordsSlice = createSlice({
  name: "records",
  initialState: {
    items: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      // Fetch
      .addCase(fetchRecords.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecords.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchRecords.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // Create
      .addCase(createRecord.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createRecord.fulfilled, (state, action) => {
        state.loading = false;
        state.items.push(action.payload);
      })
      .addCase(createRecord.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // Update
      .addCase(updateRecordAsync.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateRecordAsync.fulfilled, (state, action) => {
        state.loading = false;

        const index = state.items.findIndex(
          (record) => record.id === action.payload.id
        );

        if (index !== -1) {
          state.items[index] = action.payload;
        } else {
          state.items.push(action.payload);
        }
      })
      .addCase(updateRecordAsync.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // Delete
      .addCase(deleteRecordAsync.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteRecordAsync.fulfilled, (state, action) => {
        state.loading = false;
        state.items = state.items.filter(
          (record) => record.id !== action.payload
        );
      })
      .addCase(deleteRecordAsync.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export default recordsSlice.reducer;