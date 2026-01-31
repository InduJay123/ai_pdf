import { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import api from "../api/axios";

interface PDFListProps {
  onSelect: (pdf: any) => void;
}

const PDFList = forwardRef<any, PDFListProps>(({ onSelect }: PDFListProps, ref) => {
    const [pdfs, setPdfs ] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    
    const fetchPdfs = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const res = await api.get("/api/my_pdfs/");
            setPdfs(res.data);
        } catch (error: any) {
            console.error("Failed to fetch PDFs:", error);
            if (error.response?.status === 401) {
                setError("Session expired. Please login again.");
            } else {
                setError("Failed to load PDFs. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    };

    useImperativeHandle(ref, () => ({
        refresh: fetchPdfs
    }));

    useEffect(() => {
        fetchPdfs();
    }, []);

    if (loading) {
        return <div className="p-4 text-gray-500">Loading PDFs...</div>;
    }

    if (error) {
        return <div className="p-4 text-red-600">{error}</div>;
    }

    return(
        <div>
            {pdfs.length === 0 ? (
                <div className="p-4 text-gray-500">No PDFs uploaded yet</div>
            ) : (
                pdfs.map((pdf) => (
                    <div key={pdf.id}  className="p-2 border my-1 cursor-pointer border-blue-400 rounded hover:bg-gray-100 flex items-center justify-between" onClick={() => onSelect(pdf)}>
                        <div>{pdf.title}</div>
                        {pdf.processing_status && pdf.processing_status !== 'done' && (
                            <div className="text-sm text-yellow-700">{pdf.processing_status}</div>
                        )}
                    </div>
                ))
            )}
        </div>
    )
});

PDFList.displayName = "PDFList";
export default PDFList;