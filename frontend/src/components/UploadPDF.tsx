import { useState } from "react";
import api from "../api/axios";

interface UploadPDFProps {
  onUploaded: () => void; // callback to refresh list after upload
}

const UploadPDF:React.FC<UploadPDFProps> = ({ onUploaded }: UploadPDFProps) => {

    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);

    const handleUpload = async () => {
        if(!file) return;
        const formData = new FormData();
        formData.append("file", file);

        try {
            setLoading(true);
            const res = await api.post("/api/upload_pdf/", formData);
            alert("PDF uploaded successfully");
            setFile(null);
            onUploaded(); // Refresh the PDF list
        } catch (error) {
            console.error("Upload failed:", error);
            alert("Failed to upload PDF");
        } finally {
            setLoading(false);
        }
    }
    
    return(
        <div className="p-4 border border-green-500 rounded-xl mb-4">
            <input 
                type="file" 
                accept="application/pdf" 
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                disabled={loading}
            />
            <button 
                type="submit" 
                onClick={handleUpload}
                disabled={!file || loading}
                className="bg-green-500 px-4 py-2 text-white mt-2 disabled:opacity-50">
                 {loading ? "Uploading..." : "Upload File"}
            </button>
        </div>
    )
}

export default UploadPDF;