import { useState, useRef } from "react";
import UploadPDF from "./uploadPDF";
import PDFList from "./PDFList";
import PDFPreview from "./PDFPreview";
import PDFChunks from "./PDFChunks";
import ChatUI from "./ChatUI";


const Dashboard:React.FC = () => {
    const [selectedPDF, setSelectedPDF] = useState<any>(null);
    const pdfListRef = useRef<any>(null);

    const handleUploaded = () => {
        // Refresh the PDF list after upload
        if (pdfListRef.current) {
            pdfListRef.current.refresh();
        }
    };

    const handleSelectPDF = (pdf: any) => {
        console.log("Selected PDF:", pdf);
        setSelectedPDF(pdf);
    };

    return(
        <div className="flex gap-4 p-4">
            <div className="w-1/4">
                <UploadPDF onUploaded={handleUploaded}/>
                <PDFList ref={pdfListRef} onSelect={handleSelectPDF} />
            </div>
            
            <div className="flex-1">
                {selectedPDF ? (
                    <>
                        <div className="flex items-center gap-3">
                            <h2 className="text-lg font-bold mb-2">{selectedPDF.title}</h2>
                            {selectedPDF.processing_status && selectedPDF.processing_status !== 'done' && (
                                <span className="text-sm text-yellow-700 font-semibold">{selectedPDF.processing_status}</span>
                            )}
                        </div>
                        <PDFPreview key={selectedPDF.id} fileUrl={selectedPDF.file_url} pdfId={selectedPDF.id} processingStatus={selectedPDF.processing_status} />
                    </>
                ) : (
                    <div className="p-4 text-gray-500">Select a PDF to preview</div>
                )}
            </div>

            <div>
                {selectedPDF ? <PDFChunks key={selectedPDF.id} pdfId={selectedPDF.id} /> : <div className="p-4 text-gray-500">Select a PDF to see chunks</div>}
            </div>

            <div className="w-2/3">
                {selectedPDF && <ChatUI pdfId={selectedPDF.id} />}
            </div>
        </div>
    )
}

export default Dashboard;