import { useState, useRef } from "react";
import { useSelector, useDispatch } from "react-redux";
import { runExtraction } from "../store/complaintSlice";
import ChatBox from "./ChatBox";

const SAMPLES = [
  { label: "Sterility complaint (email)", value: "sterility" },
  { label: "Labeling defect", value: "labeling" },
  { label: "Vague / incomplete", value: "incomplete" },
];

// Inline copies of the sample_data/*.txt files so the demo works without a file-picker dance.
// (Full versions also live in backend/sample_data/ for the file-upload path.)
const SAMPLE_TEXT = {
  sterility: `Subject: URGENT - Particulate matter found in injectable batch
From: procurement@meridianhealth-hospitals.com

Our pharmacy staff at Meridian Health Hospital identified visible particulate matter (small
white flecks) floating in 4 out of 12 vials from Batch/Lot Number APX-2291-B while performing
a routine visual inspection before administration. The product is "Cefotaxime Sodium for
Injection, 1g/vial", manufacturing date 2026-02-14, expiry date 2028-01-31.

Discovered on 2026-07-20. Vials quarantined, not administered to patients. Given this is a
sterile injectable, we are treating this as a potential critical quality issue.

Complaint submitted by: David Okafor, Senior Pharmacist, Meridian Health Hospitals`,
  labeling: `Complaint Source: Retail Pharmacy
Customer Name: GreenLeaf Pharmacy Chain, Order Desk

Metformin Hydrochloride Extended-Release Tablets, 500mg, Batch/Lot Number MET-500-0847,
manufacturing date 2025-11-03, expiry date 2027-10-31.

2 of 50 cartons received had a smudged outer carton batch number, still legible. Blister
strips inside correctly labeled and undamaged. Quantity affected: 2 cartons (200 tablets).
Minor printing/labeling defect, no safety concern identified.

Complaint date: 2026-07-18. Submitted by Priya Nair, Inventory Manager.`,
  incomplete: `Hi, I bought one of your pain relief tablets last month and after taking it I felt a bit
nauseous. Not sure if it's related to the medicine or something else. Just wanted to flag it.

Thanks, Anonymous customer via web contact form`,
};

export default function AIAssistantPanel() {
  const dispatch = useDispatch();
  const extractionState = useSelector((s) => s.complaint.extractionState);
  const extractionError = useSelector((s) => s.complaint.extractionError);
  const riskClassification = useSelector((s) => s.complaint.riskClassification);
  const riskJustification = useSelector((s) => s.complaint.riskJustification);
  const capaRecommendation = useSelector((s) => s.complaint.capaRecommendation);
  const missingFields = useSelector((s) => s.complaint.missingFields);
  const completenessScore = useSelector((s) => s.complaint.completenessScore);
  const duplicateMatches = useSelector((s) => s.complaint.duplicateMatches);
  const isPotentialDuplicate = useSelector((s) => s.complaint.isPotentialDuplicate);

  const [pastedText, setPastedText] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const progressPct =
    extractionState === "loading" ? 65 : extractionState === "done" ? 100 : 0;

  const handleFile = (file) => {
    if (!file) return;
    dispatch(runExtraction({ mode: "file", file }));
  };

  const handlePasteSubmit = () => {
    if (!pastedText.trim()) return;
    dispatch(runExtraction({ mode: "text", text: pastedText }));
  };

  const loadSample = (key) => {
    setPastedText(SAMPLE_TEXT[key]);
    dispatch(runExtraction({ mode: "text", text: SAMPLE_TEXT[key] }));
  };

  return (
    <section className="panel">
      <div className="panel-header ai-panel-header">
        <div>
          <h2>✨ AI Complaint Intake Assistant</h2>
          <div className="eyebrow">LangGraph pipeline · Groq gemma2-9b-it</div>
        </div>
        <span className="badge-beta">BETA</span>
      </div>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
      >
        <div className="icon">📄</div>
        <div className="primary">Drag &amp; drop complaint document here</div>
        <div className="secondary">or click to browse</div>
        <input
          ref={fileInputRef}
          type="file"
          hidden
          accept=".pdf,.txt,.eml"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      <div className="divider-or">OR</div>

      <div className="paste-box">
        <textarea
          placeholder="Paste complaint text or email here..."
          value={pastedText}
          onChange={(e) => setPastedText(e.target.value)}
        />
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
          <button className="btn btn-primary" onClick={handlePasteSubmit}>
            Extract from Text
          </button>
        </div>
      </div>

      <div className="file-support-note">
        Supported formats: PDF, TXT, EML · Max file size: 10MB
      </div>

      <div className="sample-links">
        {SAMPLES.map((s) => (
          <button key={s.value} className="sample-chip" onClick={() => loadSample(s.value)}>
            Try sample: {s.label}
          </button>
        ))}
      </div>

      {extractionState === "loading" && (
        <div className="extraction-progress">
          <div className="track"><div className="fill" style={{ width: `${progressPct}%` }} /></div>
          <div className="label">Analyzing document content and extracting key details. Please wait...</div>
        </div>
      )}

      {extractionState === "error" && (
        <div className="ai-assistant-msg" style={{ background: "var(--risk-high-tint)" }}>
          Something went wrong during extraction: {extractionError}. Check that your Groq API
          key is set in backend/.env and try again.
        </div>
      )}

      {extractionState === "idle" && (
        <div className="ai-assistant-msg">
          Upload a complaint document, paste text, or try a sample above. I'll automatically
          extract the details and populate the form for you.
        </div>
      )}

      {extractionState === "done" && (
        <>
          <div className="ai-assistant-msg">
            Extraction complete — completeness score {Math.round((completenessScore || 0) * 100)}%.
            {missingFields.length > 0
              ? ` Missing: ${missingFields.join(", ")}. Please review the highlighted fields.`
              : " All mandatory fields were found. Please review before saving."}
          </div>

          {isPotentialDuplicate && duplicateMatches.length > 0 && (
            <div className="duplicate-card">
              <div className="risk-header">
                <strong style={{ fontSize: 13 }}>⚠ Possible Duplicate Complaint</strong>
                <span className="dup-count-badge">{duplicateMatches.length} match{duplicateMatches.length > 1 ? "es" : ""}</span>
              </div>
              {duplicateMatches.map((m) => (
                <div key={m.id} className="dup-match-row">
                  <div className="dup-match-top">
                    <span className="dup-match-title">#{m.id} — {m.product_name || "Unknown product"}</span>
                    <span className="dup-match-score">{Math.round((m.match_score || 0) * 100)}% match</span>
                  </div>
                  <div className="dup-match-meta">
                    Batch: {m.batch_lot_number || "—"} · Customer: {m.customer_name || "—"} · Status: {m.status || "—"}
                  </div>
                  <div className="dup-match-reasons">{(m.match_reasons || []).join(" · ")}</div>
                </div>
              ))}
            </div>
          )}

          {riskClassification && (
            <div className="risk-card">
              <div className="risk-header">
                <strong style={{ fontSize: 13 }}>AI Risk Assessment</strong>
                <span className="risk-badge" data-risk={riskClassification}>{riskClassification}</span>
              </div>
              <p>{riskJustification}</p>
              {capaRecommendation && (
                <>
                  <div className="capa-label">Suggested CAPA (draft)</div>
                  <p>{capaRecommendation}</p>
                </>
              )}
            </div>
          )}
        </>
      )}

      <ChatBox />
    </section>
  );
}
