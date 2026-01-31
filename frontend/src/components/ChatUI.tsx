import { useState } from "react";
import api from "../api/axios";

export default function ChatUI({ pdfId }: { pdfId: number }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const askQuestion = async () => {
    if (!input.trim()) return;

    // Add user message to UI
    setMessages((prev) => [...prev, { role: "user", text: input }]);

    const token = localStorage.getItem("access");
    setIsProcessing(true);
    setIsSending(true);

    try {
      const res = await api.post(`/api/ask_pdf/${pdfId}/`, 
        { question: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMessages((prev) => [...prev, { role: "assistant", text: res.data.answer }]);
      setInput("");
    } catch (err: any) {
      const status = err?.response?.status;
      const data = err?.response?.data;
      let msg = "Request failed";
      if (data && data.error) msg = data.error;

      setMessages((prev) => [...prev, { role: "assistant", text: `${msg} (${status})` }]);
      console.error("ask_pdf error", status, data || err);
    } finally {
      setIsProcessing(false);
      setIsSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full border rounded p-4">
      <div className="flex-1 overflow-auto">
        <h4 className="text-blue-900 font-bold">Chat</h4>

        {isProcessing && <div className="text-yellow-700 font-semibold my-2">Processing...</div>}

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
          disabled={isSending}
        />
        <button onClick={askQuestion} className="bg-blue-600 text-white px-4 rounded" disabled={isSending}>
          {isSending ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
