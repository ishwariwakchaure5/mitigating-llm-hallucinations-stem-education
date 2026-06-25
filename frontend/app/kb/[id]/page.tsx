"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  Upload,
  FileText,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Trash2,
  Send,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { useAuthStore } from "@/store/auth";
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
import { formatDateTime, getVerdictColor, getConfidenceColor } from "@/lib/utils";
import Link from "next/link";
import { useDropzone } from "react-dropzone";

interface Document {
  id: string;
  filename: string;
  status: string;
  uploaded_at: string;
  page_count?: number;
}

interface VerificationResult {
  id: string;
  claim_text: string;
  verdict: string;
  confidence: number;
  created_at: string;
  evidence: any[];
}

export default function KnowledgeBasePage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuthStore();
  const { toast } = useToast();
  const kbId = params.id as string;

  const [kb, setKb] = useState<any>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [verifications, setVerifications] = useState<VerificationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [claimText, setClaimText] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [activeTab, setActiveTab] = useState<"documents" | "verify" | "history">("documents");

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    fetchData();
  }, [token, kbId]);

  const fetchData = async () => {
    try {
      const [kbRes, docsRes, historyRes] = await Promise.all([
        api.get(`/knowledge-bases/${kbId}`),
        api.get(`/knowledge-bases/${kbId}/documents`),
        api.get(`/verify/${kbId}/history`),
      ]);
      setKb(kbRes.data);
      setDocuments(docsRes.data);
      setVerifications(historyRes.data);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load knowledge base",
      });
      router.push("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      await api.post(`/knowledge-bases/${kbId}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast({
        title: "Upload started",
        description: "Document is being processed",
      });
      fetchData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: "Could not upload document",
      });
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
  });

  const handleVerify = async () => {
    if (!claimText.trim()) return;

    setIsVerifying(true);
    try {
      const response = await api.post(`/verify/${kbId}`, {
        claim_text: claimText,
      });
      toast({
        title: "Verification complete",
        description: `Verdict: ${response.data.verdict}`,
      });
      setVerifications([response.data, ...verifications]);
      setClaimText("");
      setActiveTab("history");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Verification failed",
        description: "Could not verify claim",
      });
    } finally {
      setIsVerifying(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      {/* Navigation */}
      <nav className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Shield className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-bold">{kb?.name}</h1>
            </div>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        {/* Stats Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid md:grid-cols-3 gap-6 mb-8"
        >
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{documents.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Text Chunks
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{kb?.chunk_count || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Verifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{verifications.length}</div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b">
          {[
            { key: "documents", label: "Documents", icon: FileText },
            { key: "verify", label: "Verify Claims", icon: ShieldCheck },
            { key: "history", label: "History", icon: CheckCircle2 },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === "documents" && (
            <motion.div
              key="documents"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Upload Area */}
              <Card>
                <CardHeader>
                  <CardTitle>Upload Document</CardTitle>
                  <CardDescription>
                    Upload PDF documents to your knowledge base
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
                      isDragActive
                        ? "border-primary bg-primary/5"
                        : "border-muted-foreground/25 hover:border-primary/50"
                    }`}
                  >
                    <input {...getInputProps()} />
                    <Upload className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-lg font-medium mb-2">
                      {isDragActive
                        ? "Drop your PDF here"
                        : "Drag & drop a PDF here"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      or click to browse files
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Documents List */}
              <div className="space-y-4">
                {documents.map((doc) => (
                  <Card key={doc.id}>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="bg-primary/10 p-3 rounded-lg">
                            <FileText className="h-6 w-6 text-primary" />
                          </div>
                          <div>
                            <h3 className="font-semibold">{doc.filename}</h3>
                            <p className="text-sm text-muted-foreground">
                              Uploaded {formatDateTime(doc.uploaded_at)}
                              {doc.page_count && ` • ${doc.page_count} pages`}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-medium ${
                              doc.status === "ready"
                                ? "bg-green-100 text-green-700"
                                : doc.status === "processing"
                                ? "bg-blue-100 text-blue-700"
                                : "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {doc.status}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === "verify" && (
            <motion.div
              key="verify"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Verify a Claim</CardTitle>
                  <CardDescription>
                    Enter AI-generated content or claims to check for hallucinations against your knowledge base
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Textarea
                    placeholder="Enter your claim here... For example: 'The Pythagorean theorem states that a² + b² = c²'"
                    value={claimText}
                    onChange={(e) => setClaimText(e.target.value)}
                    rows={6}
                    className="resize-none"
                  />
                  <Button
                    onClick={handleVerify}
                    disabled={isVerifying || !claimText.trim()}
                    className="w-full gradient-bg"
                    size="lg"
                  >
                    {isVerifying ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Verifying...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Verify Claim
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {activeTab === "history" && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              {verifications.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      No verifications yet. Start by verifying a claim!
                    </p>
                  </CardContent>
                </Card>
              ) : (
                verifications.map((result) => (
                  <Card key={result.id} className="overflow-hidden">
                    <CardHeader className={getVerdictColor(result.verdict)}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            {result.verdict === "correct" && (
                              <CheckCircle2 className="h-5 w-5" />
                            )}
                            {result.verdict === "wrong" && (
                              <XCircle className="h-5 w-5" />
                            )}
                            {(result.verdict === "mixed" ||
                              result.verdict === "uncertain") && (
                              <AlertCircle className="h-5 w-5" />
                            )}
                            <span className="font-bold uppercase text-sm">
                              {result.verdict}
                            </span>
                          </div>
                          <p className="text-sm">
                            {formatDateTime(result.created_at)}
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold">
                            {Math.round(result.confidence * 100)}%
                          </div>
                          <div className="text-xs">Confidence</div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-6">
                      <p className="mb-4 text-sm leading-relaxed">
                        {result.claim_text}
                      </p>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">
                            Confidence Score
                          </span>
                          <span className="font-medium">
                            {Math.round(result.confidence * 100)}%
                          </span>
                        </div>
                        <Progress
                          value={result.confidence * 100}
                          className="h-2"
                        />
                      </div>
                      {result.evidence?.length > 0 && (
                        <div className="mt-4 pt-4 border-t">
                          <h4 className="text-sm font-semibold mb-2">
                            Evidence ({result.evidence.length})
                          </h4>
                          <div className="space-y-2">
                            {result.evidence.slice(0, 2).map((ev, idx) => (
                              <div
                                key={idx}
                                className="text-xs bg-muted p-3 rounded"
                              >
                                <p className="text-muted-foreground">
                                  {ev.text?.substring(0, 150)}...
                                </p>
                                {ev.page_number && (
                                  <p className="mt-1 text-primary font-medium">
                                    Page {ev.page_number}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
