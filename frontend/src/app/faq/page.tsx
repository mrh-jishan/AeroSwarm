import type { Metadata } from "next";
import { PublicPageShell } from "@/components/PublicPageShell";
import { absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "FAQ",
  description: "Answers to common questions about AeroSwarm, self-hosting, GitHub integration, and review flow.",
};

const faqs = [
  {
    question: "What does AeroSwarm actually do?",
    answer:
      "It turns a software request into isolated parallel tasks, launches coding agents against those scopes, then brings the output back through preflight checks and human approval.",
  },
  {
    question: "Is this meant to replace engineers?",
    answer:
      "No. The product is designed to accelerate implementation and reduce low-leverage coordination work, while keeping human review in the delivery path.",
  },
  {
    question: "Can this run against private repositories?",
    answer:
      "Yes. The current product is oriented around private-repo workflows and supports GitHub provider connections, pull request sync, and self-managed infrastructure.",
  },
  {
    question: "Why not just use a single coding agent?",
    answer:
      "Single-agent loops work well for linear tasks. AeroSwarm is for work that benefits from parallel isolation across multiple scopes and still needs merge discipline at the end.",
  },
];

export default function FaqPage() {
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
    url: absoluteUrl("/faq"),
  };

  return (
    <PublicPageShell
      eyebrow="FAQ"
      title="Frequently asked questions"
      description="Short answers for prospects and teams evaluating whether AeroSwarm fits their software delivery workflow."
    >
      <div className="grid gap-4">
        {faqs.map((faq) => (
          <article key={faq.question} className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <h2 className="text-xl font-semibold text-white">{faq.question}</h2>
            <p className="mt-3 text-slate-300">{faq.answer}</p>
          </article>
        ))}
      </div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
    </PublicPageShell>
  );
}
