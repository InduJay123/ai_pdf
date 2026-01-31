import { Viewer, Worker } from "@react-pdf-viewer/core";
import "@react-pdf-viewer/core/lib/styles/index.css";
import { useEffect, useState } from "react";
import api from "../api/axios";

const PDFPreview = ({ fileUrl, pdfId, processingStatus }: { fileUrl: string; pdfId?: number; processingStatus?: string }) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const [processing, setProcessing] = useState(false);
  const [processMessage, setProcessMessage] = useState<string | null>(null);
  const [remoteStatus, setRemoteStatus] = useState<string | null>(processingStatus || null);

  // Auto-poll remote processing status when it's pending/processing
  useEffect(() => {
    if (!pdfId) return;
    if (!remoteStatus) return;
    if (remoteStatus !== 'pending' && remoteStatus !== 'processing') return;

    let cancelled = false;
    const token = localStorage.getItem('access');

    const pollUntilDone = async () => {
      for (let i = 0; i < 30 && !cancelled; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const list = await api.get(`/api/my_pdfs/`, { headers: { Authorization: `Bearer ${token}` } });
          const pdf = list.data.find((p: any) => p.id === pdfId);
          if (pdf) {
            setRemoteStatus(pdf.processing_status);
            if (pdf.processing_status === 'done') {
              // refresh preview
              if (fileUrl) {
                setPdfUrl(null);
                setLoading(true);
                const response = await api.get(fileUrl, { responseType: "arraybuffer" });
                const blob = new Blob([response.data], { type: "application/pdf" });
                const object = URL.createObjectURL(blob);
                setPdfUrl(object);
              }
              return;
            }
            if (pdf.processing_status === 'failed') {
              setProcessMessage(pdf.processing_error || 'Processing failed');
              return;
            }
          }
        } catch (err) {
          console.warn('Status poll failed', err);
        }
      }
    };

    pollUntilDone();
    return () => { cancelled = true };
  }, [pdfId, remoteStatus, fileUrl]);

  useEffect(() => {
    if (!fileUrl) return;

    setLoading(true);
    setError(null);
    setPdfUrl(null);

    let objectUrl: string | null = null;

    const fetchPdf = async () => {
      try {
        const response = await api.get(fileUrl, { responseType: "arraybuffer" });

        const blob = new Blob([response.data], { type: "application/pdf" });
        objectUrl = URL.createObjectURL(blob);
        setPdfUrl(objectUrl);
      } catch (err: any) {
         const status = err?.response?.status;
        const data = err?.response?.data;

        let details = "";
        if (data instanceof ArrayBuffer) {
          details = new TextDecoder("utf-8").decode(new Uint8Array(data));
        } else if (typeof data === "string") {
          details = data;
        } else if (data) {
          details = JSON.stringify(data);
        }

        console.error("PDF view failed:", status, details || err);
        setError(`PDF view failed (${status}). Check console for details.`);
      } finally {
        setLoading(false);
      }
    };

    fetchPdf();

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [fileUrl]);

  const handleReprocess = async () => {
    if (!pdfId) return;
    setProcessing(true);
    setProcessMessage(null);
    const token = localStorage.getItem("access");
    try {
      const res = await api.post(`/api/pdf/${pdfId}/process/`, {}, { headers: { Authorization: `Bearer ${token}` } });
      setProcessMessage(res?.data?.message || "Reprocess completed");
      setRemoteStatus('processing');

      // Poll remote status until done/failed, then refresh preview automatically
      const poll = async () => {
        for (let i = 0; i < 12; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          try {
            const list = await api.get(`/api/my_pdfs/`, { headers: { Authorization: `Bearer ${token}` } });
            const pdf = list.data.find((p: any) => p.id === pdfId);
            if (pdf) {
              setRemoteStatus(pdf.processing_status);
              if (pdf.processing_status === 'done') {
                // refresh preview
                if (fileUrl) {
                  setPdfUrl(null);
                  setLoading(true);
                  const response = await api.get(fileUrl, { responseType: "arraybuffer" });
                  const blob = new Blob([response.data], { type: "application/pdf" });
                  const object = URL.createObjectURL(blob);
                  setPdfUrl(object);
                }
                return;
              }
              if (pdf.processing_status === 'failed') {
                setProcessMessage(pdf.processing_error || 'Processing failed');
                return;
              }
            }
          } catch (err) {
            console.warn('Status poll failed', err);
          }
        }
        setProcessMessage('Processing still in progress...');
      };

      poll();

    } catch (err: any) {
      const status = err?.response?.status;
      const data = err?.response?.data;
      let msg = "Reprocess failed";
      if (data && data.error) msg = data.error;
      setProcessMessage(`${msg} (${status})`);
      console.error("Reprocess error", status, data || err);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div>
      <div className="flex justify-end gap-2 items-center p-2">
        {processMessage && <div className="text-sm text-gray-700">{processMessage}</div>}
        <button
          onClick={handleReprocess}
          disabled={!pdfId || processing}
          className="bg-blue-600 text-white px-3 py-1 rounded disabled:opacity-60"
        >
          {processing ? "Processing..." : "Reprocess"}
        </button>
      </div>

      { !fileUrl ? (
        <div className="p-4 text-gray-500">Select a PDF to Preview</div>
      ) : error ? (
        <div className="p-4 text-red-600">{error}</div>
      ) : (loading || !pdfUrl) ? (
        <div className="p-4 text-gray-500">Loading PDF...</div>
      ) : (
        <div className="border-blue-500 h-96 overflow-auto bg-gray-50">
          <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
            <Viewer fileUrl={pdfUrl} />
          </Worker>
        </div>
      )}
    </div>
  );
};

export default PDFPreview;