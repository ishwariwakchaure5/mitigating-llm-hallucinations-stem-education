"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  Plus,
  BookOpen,
  FileText,
  Search,
  LogOut,
  User,
  Loader2,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth";
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  created_at: string;
  document_count?: number;
  chunk_count?: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, logout } = useAuthStore();
  const { toast } = useToast();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    fetchKnowledgeBases();
  }, [token, router]);

  const fetchKnowledgeBases = async () => {
    try {
      const response = await api.get("/knowledge-bases/");
      setKbs(response.data);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load knowledge bases",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  const filteredKbs = kbs.filter(
    (kb) =>
      kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      kb.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      {/* Navigation */}
      <nav className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <span className="text-lg font-bold gradient-text block">STEM Verification</span>
              <span className="text-xs text-muted-foreground">Hallucination Mitigation</span>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              <span>{user?.email || "User"}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2">Knowledge Bases</h1>
          <p className="text-muted-foreground">
            Build verified STEM knowledge bases to detect AI hallucinations
          </p>
        </motion.div>

        {/* Search and Create */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex gap-4 mb-8 flex-wrap"
        >
          <div className="relative flex-1 min-w-[300px]">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search knowledge bases..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button
            size="lg"
            className="gradient-bg"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Knowledge Base
          </Button>
        </motion.div>

        {/* Knowledge Bases Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : filteredKbs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-20"
          >
            <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">
              {searchQuery ? "No results found" : "No knowledge bases yet"}
            </h3>
            <p className="text-muted-foreground mb-6">
              {searchQuery
                ? "Try a different search term"
                : "Create your first knowledge base to get started"}
            </p>
            {!searchQuery && (
              <Button
                size="lg"
                className="gradient-bg"
                onClick={() => setShowCreateModal(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Knowledge Base
              </Button>
            )}
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredKbs.map((kb, index) => (
              <motion.div
                key={kb.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
                  <Link href={`/kb/${kb.id}`}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="bg-primary/10 p-3 rounded-lg group-hover:bg-primary/20 transition-colors">
                          <FileText className="h-6 w-6 text-primary" />
                        </div>
                      </div>
                      <CardTitle className="mt-4 group-hover:text-primary transition-colors">
                        {kb.name}
                      </CardTitle>
                      <CardDescription className="line-clamp-2">
                        {kb.description || "No description"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <FileText className="h-4 w-4" />
                          <span>{kb.document_count || 0} docs</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <BookOpen className="h-4 w-4" />
                          <span>{kb.chunk_count || 0} chunks</span>
                        </div>
                      </div>
                      <div className="mt-4 text-xs text-muted-foreground">
                        Created {formatDate(kb.created_at)}
                      </div>
                    </CardContent>
                  </Link>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Create KB Modal would go here - simplified for now */}
      {showCreateModal && (
        <CreateKBModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchKnowledgeBases();
          }}
        />
      )}
    </div>
  );
}

function CreateKBModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { toast } = useToast();
  const [formData, setFormData] = useState({ name: "", description: "" });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await api.post("/knowledge-bases/", formData);
      toast({
        title: "Success",
        description: "Knowledge base created successfully",
      });
      onSuccess();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to create knowledge base",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full"
      >
        <h2 className="text-2xl font-bold mb-4">Create Knowledge Base</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Name</label>
            <Input
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              placeholder="My Knowledge Base"
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">
              Description
            </label>
            <Input
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              placeholder="Optional description"
            />
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1 gradient-bg"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create"
              )}
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
