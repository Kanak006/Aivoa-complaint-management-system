import ComplaintForm from "./components/ComplaintForm";
import AIAssistantPanel from "./components/AIAssistantPanel";

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div className="brand"><span className="mark" />AIVOA Complaint Management</div>
          <div className="subtitle">AI-Powered Customer Complaint Management · Pharmaceutical QMS</div>
        </div>
      </header>

      <main className="main-grid">
        <ComplaintForm />
        <AIAssistantPanel />
      </main>
    </div>
  );
}
