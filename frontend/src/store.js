import { configureStore } from "@reduxjs/toolkit";
import recordsReducer from "./features/recordsSlice";

export const store = configureStore({
  reducer: {
    records: recordsReducer,
  },
});