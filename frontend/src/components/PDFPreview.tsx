import { Viewer, Worker } from "@react-pdf-viewer/core";
import "@react-pdf-viewer/core/lib/styles/index.css";
import { useState, useEffect } from "react";
import api from "../api/axios";

const PDFPreview = ({ fileUrl }: { fileUrl: string }) => {
    const [error, setError] = useState<string | null>(null);
    const [pdfData, setPdfData] = useState<Uint8Array | null>(null);
    const [loading, setLoading] = useState(true);
    
    if(!fileUrl) return <div className="p-4 text-gray-500"> Select a PDF to Preview </div>
    
    useEffect(() => {
        // Reset state when fileUrl changes
        setLoading(true);
        setPdfData(null);
        setError(null);
        
        // Fetch PDF through axios (which includes auth token)
        const fetchPdf = async () => {
            try {
                const response = await api.get(fileUrl, { responseType: 'arraybuffer' });
                const arrayBuffer = new Uint8Array(response.data);
                setPdfData(arrayBuffer);
                setError(null);
            } catch (err: any) {
                console.error("Failed to load PDF:", err);
                setError(`Failed to load PDF: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };
        
        fetchPdf();
    }, [fileUrl]);
    
    if (error) {
        return <div className="p-4 text-red-600">{error}</div>;
    }
    
    if (loading || !pdfData) {
        return <div className="p-4 text-gray-500">Loading PDF...</div>;
    }
    
    return(
        <div className="border-blue-500 h-96 overflow-auto bg-gray-50">
            <Worker 
                workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js"
                onError={(error) => {
                    console.error("PDF Worker error:", error);
                    setError("Failed to load PDF worker");
                }}
            >
                <Viewer 
                    fileUrl={pdfData}
                    onError={(error) => {
                        console.error("PDF Viewer error:", error);
                        setError("Failed to display PDF");
                    }}
                />
            </Worker>
        </div>
    )
}

export default PDFPreview;