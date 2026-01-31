import { useState } from "react";
import api from "../api/axios";

export default function ChatUI({ pdfId }: { pdfId: number }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");

  const askQuestion = async () => {
    if (!input.trim()) return;

    // Add user message to UI
    setMessages((prev) => [...prev, { role: "user", text: input }]);

    const token = localStorage.getItem("access");

    const res = await api.post(`/api/ask_pdf/${pdfId}/`, 
      { question: input },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    setMessages((prev) => [...prev, { role: "assistant", text: res.data.answer }]);
    setInput("");
  };

  return (
    <div className="flex flex-col h-full border rounded p-4">
      <div className="flex-1 overflow-auto">
        <h4 className="text-blue-900 font-bold">Chat</h4>
        {messages.map((m, i) => (
          <div key={i} className={`my-2 p-2 rounded ${m.role === "user" ? "bg-blue-200" : "bg-green-200"}`}>
            {m.text}
          </div>
        ))}
      </div>

      <div className="flex gap-2 mt-4">
        <input 
          className="flex-1 border p-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something..."
        />
        <button onClick={askQuestion} className="bg-blue-600 text-white px-4 rounded">
          Send
        </button>
      </div>
    </div>
  );
}
