"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { motion } from "framer-motion";
import { 
  GraduationCap, 
  BookOpen, 
  CheckCircle2, 
  ArrowRight,
  Shield,
  FileText,
  BarChart3,
  Users,
  Target,
  Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Home() {
  const router = useRouter();
  const { token } = useAuthStore();

  useEffect(() => {
    if (token) {
      router.push("/dashboard");
    }
  }, [token, router]);

  const features = [
    {
      icon: Shield,
      title: "Hallucination Detection",
      description: "Identify when AI outputs deviate from authoritative STEM sources with confidence scoring",
    },
    {
      icon: BookOpen,
      title: "Cross-Referenced Knowledge",
      description: "Build vetted knowledge bases from textbooks, papers, and educational materials",
    },
    {
      icon: FileText,
      title: "Automatic Citations",
      description: "Generate academic-style citations with page numbers and confidence scores",
    },
    {
      icon: BarChart3,
      title: "Evidence-Based Verification",
      description: "Multi-modal verification combining text, equations, and visual diagrams",
    },
    {
      icon: Users,
      title: "Built for Education",
      description: "Designed specifically for educators and students in STEM fields",
    },
    {
      icon: Target,
      title: "Research-Backed",
      description: "Calibrated confidence thresholds based on educational research",
    },
  ];

  const useCases = [
    {
      role: "Educators",
      description: "Verify AI-generated study materials and ensure factual accuracy in classroom resources",
      icon: GraduationCap,
    },
    {
      role: "Students",
      description: "Check homework answers and learning materials against verified sources",
      icon: BookOpen,
    },
    {
      role: "Researchers",
      description: "Validate claims in literature reviews and ensure scientific accuracy",
      icon: Sparkles,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      {/* Navigation */}
      <nav className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2"
          >
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <span className="text-xl font-bold gradient-text block">STEM Hallucination</span>
              <span className="text-xs text-muted-foreground">Mitigation System</span>
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex gap-3"
          >
            <Link href="/login">
              <Button variant="ghost" size="lg">
                Login
              </Button>
            </Link>
            <Link href="/register">
              <Button size="lg" className="gradient-bg">
                Get Started
              </Button>
            </Link>
          </motion.div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center max-w-5xl mx-auto"
        >
          <div className="inline-block mb-4 px-4 py-2 bg-primary/10 rounded-full text-sm font-medium text-primary">
            Research-Backed AI Verification for Education
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 text-balance leading-tight">
            Mitigating LLM{" "}
            <span className="gradient-text">Hallucinations</span>
            <br />
            in STEM Education
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-8 text-balance max-w-3xl mx-auto">
            Evidence-based verification system that detects AI hallucinations using
            cross-referenced knowledge bases, multi-modal verification, and
            automatic citation generation.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/register">
              <Button size="lg" className="gradient-bg text-lg h-14 px-10">
                Start Verifying
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="#features">
              <Button size="lg" variant="outline" className="text-lg h-14 px-10">
                Learn More
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="grid grid-cols-3 gap-8 mt-16 max-w-2xl mx-auto"
          >
            <div>
              <div className="text-3xl font-bold text-primary">95%</div>
              <div className="text-sm text-muted-foreground">Accuracy</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-primary">3+</div>
              <div className="text-sm text-muted-foreground">Verification Paths</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-primary">100%</div>
              <div className="text-sm text-muted-foreground">Cited Sources</div>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section id="features" className="container mx-auto px-4 py-20 bg-white/50 dark:bg-gray-900/50">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">Comprehensive Verification Framework</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Multi-modal evidence-based verification designed specifically for STEM education
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all border border-gray-100 dark:border-gray-700 group hover:border-primary/50"
            >
              <div className="bg-primary/10 w-14 h-14 rounded-xl flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                <feature.icon className="h-7 w-7 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Use Cases */}
      <section className="container mx-auto px-4 py-20">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">Built for Educational Excellence</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Empowering educators, students, and researchers with AI verification tools
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {useCases.map((useCase, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.9 + index * 0.1 }}
              className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary/10 to-purple-100 dark:from-primary/20 dark:to-purple-900/20 p-8"
            >
              <useCase.icon className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-2xl font-bold mb-3">{useCase.role}</h3>
              <p className="text-muted-foreground">{useCase.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="container mx-auto px-4 py-20 bg-white/50 dark:bg-gray-900/50">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">How It Works</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Evidence-based verification in three simple steps
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-12 max-w-5xl mx-auto">
          <div className="relative text-center">
            <div className="bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-full w-16 h-16 flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-lg">
              1
            </div>
            <h3 className="font-bold text-xl mb-3">Upload Knowledge Base</h3>
            <p className="text-muted-foreground">
              Add textbooks, papers, and vetted educational materials to create your reference library
            </p>
          </div>
          <div className="relative text-center">
            <div className="bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-full w-16 h-16 flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-lg">
              2
            </div>
            <h3 className="font-bold text-xl mb-3">Submit for Verification</h3>
            <p className="text-muted-foreground">
              Enter claims, AI-generated content, or student answers for fact-checking
            </p>
          </div>
          <div className="relative text-center">
            <div className="bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-full w-16 h-16 flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-lg">
              3
            </div>
            <h3 className="font-bold text-xl mb-3">Review Results</h3>
            <p className="text-muted-foreground">
              Get confidence scores, automatic citations, and evidence-based verdicts
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.4 }}
          className="bg-gradient-to-br from-primary to-primary/80 rounded-3xl p-12 md:p-16 text-center text-white shadow-2xl"
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to Eliminate AI Hallucinations?
          </h2>
          <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
            Join educators and researchers using evidence-based verification to ensure
            factual accuracy in STEM education.
          </p>
          <Link href="/register">
            <Button size="lg" variant="secondary" className="text-lg h-14 px-10">
              Create Free Account
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-12">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="h-6 w-6 text-primary" />
                <span className="font-bold">STEM Verification</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Mitigating LLM hallucinations through evidence-based verification
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link href="#features">Features</Link></li>
                <li><Link href="#">Documentation</Link></li>
                <li><Link href="#">API Reference</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Research</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link href="#">Publications</Link></li>
                <li><Link href="#">Benchmarks</Link></li>
                <li><Link href="#">Methodology</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link href="#">Contact</Link></li>
                <li><Link href="#">GitHub</Link></li>
                <li><Link href="#">Community</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t pt-8 text-center text-sm text-muted-foreground">
            <p>© 2026 STEM Hallucination Mitigation System - Built for Education, by Researchers</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
