import { useState, useRef } from "react";
import { Upload, FileText, X, CheckCircle, Loader2 } from "lucide-react";
import Layout from "../components/Layout";
import { toast } from "../hooks/use-toast";

const UploadPage = () => {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [simplifiedText, setSimplifiedText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = () => {
    setIsDragging(false);
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (validateFile(droppedFile)) {
      setFile(droppedFile);
    }
  };
  
  const validateFile = (file: File) => {
    const allowedTypes = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/jpeg", "image/png"];
    
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF, DOCX, or image file",
        variant: "destructive",
      });
      return false;
    }
    
    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      toast({
        title: "File too large",
        description: "Please upload a file smaller than 10MB",
        variant: "destructive",
      });
      return false;
    }
    
    return true;
  };
  
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
    }
  };
  
  const simplifyDocument = async () => {
    if (!file) return;
    
    setIsProcessing(true);
    
    // Simulate API call
    setTimeout(() => {
      setSimplifiedText(`
**Simplified Document Summary:**

This document appears to be a legal agreement regarding property rental/lease.

**Key Points:**

1. **Parties Involved:** The agreement is between the landlord (property owner) and tenant (renter).

2. **Property Details:** The property is located at the specified address and includes basic amenities.

3. **Rental Terms:**
   - Monthly rent amount is clearly specified
   - Payment is due on the 1st of each month
   - Late payment may incur additional fees

4. **Duration:** The lease period is for 12 months starting from the date of agreement.

5. **Security Deposit:** An amount equal to two months' rent is required as security deposit.

6. **Responsibilities:**
   - Tenant: Keep property clean, pay utilities, report damages
   - Landlord: Maintain property, handle major repairs

7. **Termination:** Either party must give 30 days notice before terminating the agreement.

**Important Rights:**
- You have the right to peaceful enjoyment of the property
- The landlord cannot enter without proper notice
- You can request necessary repairs
- Security deposit must be returned within 30 days after lease ends

**Recommendations:**
- Keep copies of all rent receipts
- Document property condition with photos
- Communicate all issues in writing
- Review local tenant protection laws
      `);
      setIsProcessing(false);
      toast({
        title: "Document simplified successfully!",
        description: "Your document has been analyzed and simplified.",
      });
    }, 2000);
  };
  
  const removeFile = () => {
    setFile(null);
    setSimplifiedText("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };
  
  return (
    <Layout>
      <div className="container mx-auto px-4 py-12 max-w-5xl">
        <div className="text-center mb-10 animate-fade-up">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Upload Legal Document
          </h1>
          <p className="text-lg text-muted-foreground">
            Upload your legal document and get it simplified in plain language
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div className="animate-fade-up" style={{ animationDelay: "0.1s" }}>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                isDragging
                  ? "border-primary bg-primary/5 scale-105"
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                onChange={handleFileSelect}
                className="hidden"
              />
              
              {!file ? (
                <>
                  <Upload className="h-12 w-12 text-primary mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    Drop your document here
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    or click to browse
                  </p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center justify-center rounded-lg gradient-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:shadow-lg transition-all duration-300"
                  >
                    Choose File
                  </button>
                  <p className="text-xs text-muted-foreground mt-4">
                    Supported: PDF, DOCX, JPG, PNG (Max 10MB)
                  </p>
                </>
              ) : (
                <div className="space-y-4">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
                  <div className="flex items-center justify-center space-x-2">
                    <FileText className="h-5 w-5 text-primary" />
                    <span className="text-sm font-medium text-foreground">
                      {file.name}
                    </span>
                    <button
                      onClick={removeFile}
                      className="p-1 hover:bg-destructive/10 rounded transition-colors"
                    >
                      <X className="h-4 w-4 text-destructive" />
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    onClick={simplifyDocument}
                    disabled={isProcessing}
                    className="inline-flex items-center justify-center rounded-lg gradient-secondary px-6 py-2 text-sm font-medium text-secondary-foreground hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      "Simplify Document"
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* Simplified Text Display */}
          <div className="animate-fade-up" style={{ animationDelay: "0.2s" }}>
            <div className="border border-border rounded-xl p-6 h-full bg-card">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Simplified Version
              </h3>
              
              {simplifiedText ? (
                <div className="prose prose-sm max-w-none">
                  <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {simplifiedText}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-center">
                  <FileText className="h-12 w-12 text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground">
                    Upload a document to see the simplified version here
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default UploadPage;