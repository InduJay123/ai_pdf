import { useEffect, useState } from "react";
import api from "../api/axios";

export default function PDFChunks({ pdfId }: { pdfId: number | string | null }) {
  const [chunks, setChunks] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChunks = async () => {
      try {
        setLoading(true);
        setError(null);
        const id = Number(pdfId);
        console.log("Fetching chunks for pdfId:", id);
        const res = await api.get(`/api/pdf_chunks/${id}/`);
        console.log('pdf_chunks response:', res);
        if (Array.isArray(res.data)) {
          setChunks(res.data.map((c: any) => c.chunk_text));
        } else {
          console.warn('pdf_chunks: unexpected response data', res.data);
          setChunks([]);
        }
      } catch (err: any) {
        console.error("Failed to fetch chunks:", err);
        setError(`Failed to load chunks: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    
    if (pdfId !== null && pdfId !== undefined) {
      fetchChunks();
    }
  }, [pdfId]);

  if (loading) {
    return <div className="p-4 text-gray-500">Loading chunks...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  if (chunks.length === 0) {
    return <div className="p-4 text-gray-500">No chunks found</div>;
  }

  return (
    <div className="p-4 border overflow-auto border-blue-600 h-80 bg-gray-50">
      <h3 className="font-bold mb-2">PDF Chunks ({chunks.length})</h3>
      {chunks.map((c, i) => (
        <div key={i} className="mb-3 p-2 bg-white border rounded text-sm">
          <p className="text-gray-600 text-xs mb-1">Chunk {i + 1}</p>
          <p>{c.slice(0, 200)}...</p>
        </div>
      ))}
    </div>
  );
}

