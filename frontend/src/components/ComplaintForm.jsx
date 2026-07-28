import { useSelector, useDispatch } from "react-redux";
import { updateField, resetForm, persistComplaint } from "../store/complaintSlice";

const SEVERITY_OPTIONS = ["", "Critical", "Major", "Minor", "Unknown"];
const PRIORITY_OPTIONS = ["", "High", "Medium", "Low", "Unknown"];

function TextField({ name, label, type = "text", missingFields }) {
  const dispatch = useDispatch();
  const value = useSelector((s) => s.complaint.fields[name]) || "";
  const isMissing = missingFields?.includes(name);

  return (
    <div className={`field ${isMissing ? "missing" : ""}`}>
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        type={type}
        value={value}
        placeholder={isMissing ? "Missing — please fill in" : ""}
        onChange={(e) => dispatch(updateField({ name, value: e.target.value }))}
      />
    </div>
  );
}

function SelectField({ name, label, options }) {
  const dispatch = useDispatch();
  const value = useSelector((s) => s.complaint.fields[name]) || "";
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <select
        id={name}
        value={value}
        onChange={(e) => dispatch(updateField({ name, value: e.target.value }))}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt || "Awaiting AI extraction..."}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function ComplaintForm() {
  const dispatch = useDispatch();
  const status = useSelector((s) => s.complaint.status);
  const missingFields = useSelector((s) => s.complaint.missingFields);
  const description = useSelector((s) => s.complaint.fields.description) || "";
  const saveState = useSelector((s) => s.complaint.saveState);
  const savedId = useSelector((s) => s.complaint.savedComplaintId);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Log Customer Complaint</h2>
          <div className="eyebrow">API &amp; FDF Quality Assurance Module</div>
        </div>
        <span className="status-pill" data-status={status}>{status}</span>
      </div>

      <div className="form-body">
        <div className="form-section">
          <div className="section-label"><span className="num">1</span>Origin &amp; Customer Details</div>
          <div className="field-row">
            <TextField name="complaint_source" label="Complaint Source" missingFields={missingFields} />
            <TextField name="customer_name" label="Customer Name" missingFields={missingFields} />
          </div>
        </div>

        <div className="form-section">
          <div className="section-label"><span className="num">2</span>Product &amp; Batch Identification</div>
          <div className="field-row">
            <TextField name="product_name" label="Product Name" missingFields={missingFields} />
            <TextField name="product_strength" label="Product Strength/Grade" />
          </div>
          <div className="field-row">
            <TextField name="batch_lot_number" label="Batch/Lot Number" missingFields={missingFields} />
            <TextField name="manufacturing_date" label="Manufacturing Date" type="date" />
          </div>
          <div className="field-row">
            <TextField name="expiry_date" label="Expiry Date" type="date" />
            <TextField name="quantity_affected" label="Quantity Affected" />
          </div>
        </div>

        <div className="form-section">
          <div className="section-label"><span className="num">3</span>Complaint Details</div>
          <div className="field-row">
            <TextField name="complaint_type" label="Complaint Type" missingFields={missingFields} />
            <TextField name="complaint_date" label="Complaint Date" type="date" />
          </div>
          <div className={`field ${missingFields?.includes("description") ? "missing" : ""}`}>
            <label htmlFor="description">Detailed Complaint Description</label>
            <textarea
              id="description"
              value={description}
              placeholder={missingFields?.includes("description") ? "Missing — please fill in" : ""}
              onChange={(e) => dispatch(updateField({ name: "description", value: e.target.value }))}
            />
          </div>
        </div>

        <div className="form-section">
          <div className="section-label"><span className="num">4</span>Initial Assessment &amp; Priority</div>
          <div className="field-row">
            <SelectField name="initial_severity" label="Initial Severity" options={SEVERITY_OPTIONS} />
            <SelectField name="priority" label="Priority" options={PRIORITY_OPTIONS} />
          </div>
        </div>

        <div className="form-actions">
          <button className="btn btn-ghost" onClick={() => dispatch(resetForm())}>
            Reset Form
          </button>
          <button
            className="btn btn-primary"
            disabled={saveState === "loading"}
            onClick={() => dispatch(persistComplaint())}
          >
            {saveState === "loading"
              ? "Saving..."
              : savedId
              ? `Saved (#${savedId}) — Save Again`
              : "Save Complaint"}
          </button>
        </div>
      </div>
    </section>
  );
}
