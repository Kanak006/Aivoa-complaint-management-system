import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { extractFromText, extractFromFile, saveComplaint, askAssistant } from "../api/api";

const emptyFields = {
  complaint_source: "",
  customer_name: "",
  product_name: "",
  product_strength: "",
  batch_lot_number: "",
  manufacturing_date: "",
  expiry_date: "",
  quantity_affected: "",
  complaint_type: "",
  complaint_date: "",
  description: "",
  initial_severity: "",
  priority: "",
};

const initialState = {
  fields: emptyFields,
  status: "Pending Triage",
  completenessScore: null,
  missingFields: [],
  riskClassification: null,
  riskJustification: null,
  capaRecommendation: null,
  duplicateMatches: [],
  isPotentialDuplicate: false,
  rawSourceText: "",
  extractionState: "idle", // idle | loading | done | error
  extractionError: null,
  saveState: "idle",
  chatMessages: [],
  chatState: "idle",
  savedComplaintId: null,
};

export const runExtraction = createAsyncThunk(
  "complaint/runExtraction",
  async ({ mode, text, file }) => {
    if (mode === "file") return extractFromFile(file);
    return extractFromText(text);
  }
);

export const persistComplaint = createAsyncThunk(
  "complaint/persistComplaint",
  async (_, { getState }) => {
    const s = getState().complaint;
    const payload = {
      ...s.fields,
      completeness_score: s.completenessScore,
      missing_fields: s.missingFields,
      risk_classification: s.riskClassification,
      risk_justification: s.riskJustification,
      capa_recommendation: s.capaRecommendation,
      raw_source_text: s.rawSourceText,
      status: s.status,
      duplicate_matches: s.duplicateMatches,
      is_potential_duplicate: s.isPotentialDuplicate,
    };
    // backend expects nulls, not empty strings, for date fields
    ["manufacturing_date", "expiry_date", "complaint_date"].forEach((k) => {
      if (!payload[k]) payload[k] = null;
    });
    return saveComplaint(payload);
  }
);

export const sendChatMessage = createAsyncThunk(
  "complaint/sendChatMessage",
  async (question, { getState }) => {
    const s = getState().complaint;
    const contextText =
      s.rawSourceText ||
      `Product: ${s.fields.product_name}, Description: ${s.fields.description}`;
    const res = await askAssistant({ question, contextText });
    return { question, answer: res.answer };
  }
);

const complaintSlice = createSlice({
  name: "complaint",
  initialState,
  reducers: {
    updateField(state, action) {
      const { name, value } = action.payload;
      state.fields[name] = value;
    },
    resetForm() {
      return initialState;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(runExtraction.pending, (state) => {
        state.extractionState = "loading";
        state.extractionError = null;
      })
      .addCase(runExtraction.fulfilled, (state, action) => {
        const data = action.payload;
        state.extractionState = "done";
        state.fields = { ...emptyFields, ...data.extracted };
        state.completenessScore = data.completeness_score;
        state.missingFields = data.missing_fields || [];
        state.riskClassification = data.risk_classification;
        state.riskJustification = data.risk_justification;
        state.capaRecommendation = data.capa_recommendation;
        state.duplicateMatches = data.duplicate_matches || [];
        state.isPotentialDuplicate = data.is_potential_duplicate || false;
        state.rawSourceText = data.raw_source_text;
        state.status =
          data.completeness_score < 0.4 ? "Manual Review Required" : "Pending Triage";
      })
      .addCase(runExtraction.rejected, (state, action) => {
        state.extractionState = "error";
        state.extractionError = action.error.message;
      })
      .addCase(persistComplaint.pending, (state) => {
        state.saveState = "loading";
      })
      .addCase(persistComplaint.fulfilled, (state, action) => {
        state.saveState = "done";
        state.savedComplaintId = action.payload.id;
      })
      .addCase(persistComplaint.rejected, (state) => {
        state.saveState = "error";
      })
      .addCase(sendChatMessage.pending, (state, action) => {
        state.chatState = "loading";
        state.chatMessages.push({ role: "user", text: action.meta.arg });
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatState = "idle";
        state.chatMessages.push({ role: "assistant", text: action.payload.answer });
      })
      .addCase(sendChatMessage.rejected, (state) => {
        state.chatState = "idle";
        state.chatMessages.push({
          role: "assistant",
          text: "Sorry, I couldn't reach the assistant. Please try again.",
        });
      });
  },
});

export const { updateField, resetForm } = complaintSlice.actions;
export default complaintSlice.reducer;
