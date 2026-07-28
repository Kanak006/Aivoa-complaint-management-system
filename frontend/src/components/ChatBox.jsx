import { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { sendChatMessage } from "../store/complaintSlice";

export default function ChatBox() {
  const dispatch = useDispatch();
  const messages = useSelector((s) => s.complaint.chatMessages);
  const chatState = useSelector((s) => s.complaint.chatState);
  const [input, setInput] = useState("");

  const send = () => {
    if (!input.trim() || chatState === "loading") return;
    dispatch(sendChatMessage(input));
    setInput("");
  };

  return (
    <div className="chat-section">
      <strong style={{ fontSize: 12.5 }}>AI ASSISTANT</strong>
      <div className="chat-log" style={{ marginTop: 10 }}>
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>{m.text}</div>
        ))}
        {chatState === "loading" && (
          <div className="chat-msg assistant">Thinking...</div>
        )}
      </div>
      <div className="chat-input-row">
        <input
          placeholder="Ask me anything about this complaint..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="chat-send" onClick={send}>➤</button>
      </div>
      <div className="chat-disclaimer">AI responses may contain errors. Please verify information.</div>
    </div>
  );
}
