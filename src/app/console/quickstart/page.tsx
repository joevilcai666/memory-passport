"use client";

import * as React from "react";
import Link from "next/link";
import {
  Terminal,
  Check,
  Loader2,
  Play,
  ArrowRight,
  Package,
  KeyRound,
  Send,
  Download,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/store/memory-store";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

function CodeBlock({ children, lang = "bash" }: { children: React.ReactNode; lang?: string }) {
  return (
    <div className="group relative overflow-hidden rounded-lg border bg-neutral-950 text-neutral-100">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">{lang}</span>
        <button
          onClick={() => {
            navigator.clipboard?.writeText(String(children).replace(/\n/g, "").replace(/<[^>]+>/g, ""));
            toast.success("Copied");
          }}
          className="text-[10px] text-neutral-400 transition-colors hover:text-neutral-100"
        >
          Copy
        </button>
      </div>
      <pre className="overflow-x-auto p-3 text-xs leading-relaxed ds-scroll">
        <code className="font-mono">{children}</code>
      </pre>
    </div>
  );
}

export default function QuickstartPage() {
  const { app, quickstart, runTestEvent, runRetrieveTest } = useMemoryStore();
  const [sendingEvent, setSendingEvent] = React.useState(false);
  const [retrieving, setRetrieving] = React.useState(false);

  const handleSendEvent = () => {
    setSendingEvent(true);
    setTimeout(() => {
      runTestEvent();
      setSendingEvent(false);
      toast.success("Event received · memory created", { description: "mem_quickstart" });
    }, 1100);
  };

  const handleRetrieve = () => {
    setRetrieving(true);
    setTimeout(() => {
      runRetrieveTest();
      setRetrieving(false);
      toast.success("Retrieve succeeded", { description: "3 memories returned across gpt-4o" });
    }, 1100);
  };

  const steps = [
    { icon: Package, label: "Install the SDK", done: true },
    { icon: KeyRound, label: "Initialize with API key", done: true },
    { icon: Send, label: "Send first event", done: quickstart.firstEventSent },
    { icon: Download, label: "Retrieve memory", done: quickstart.firstRetrieveDone },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium tracking-tight">Quickstart</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Ship a working memory loop in under 2 hours. Sandbox-safe.
        </p>
      </div>

      {/* Integration status checklist */}
      <Card>
        <CardHeader>
          <CardTitle>Integration status</CardTitle>
          <CardDescription>Updates live as you complete each step.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-4">
            {steps.map((s, i) => {
              const Icon = s.icon;
              return (
                <div
                  key={i}
                  className={cn(
                    "relative rounded-lg border p-4 transition-colors",
                    s.done ? "border-emerald-500/30 bg-emerald-500/5" : "bg-muted/30",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <Icon
                      className={cn("size-4", s.done ? "text-emerald-500" : "text-muted-foreground")}
                      strokeWidth={1.5}
                    />
                    {s.done ? (
                      <div className="flex size-5 items-center justify-center rounded-full bg-emerald-500 text-white">
                        <Check className="size-3" />
                      </div>
                    ) : (
                      <div className="size-5 rounded-full border-2 border-muted-foreground/30" />
                    )}
                  </div>
                  <p className="mt-3 text-xs font-medium leading-snug">
                    <span className="text-muted-foreground">{i + 1}.</span> {s.label}
                  </p>
                </div>
              );
            })}
          </div>
          {quickstart.firstRetrieveDone && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
              <Check className="size-4 text-emerald-500" />
              <span>Integration complete. View the memory in the</span>
              <Button variant="link" size="sm" asChild className="h-auto p-0">
                <Link href="/console/memory/debugger">
                  Debugger <ArrowRight className="size-3" />
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Steps */}
      <div className="space-y-4">
        {/* Step 1 */}
        <StepCard step={1} title="Install the SDK" icon={Package} done>
          <p className="text-sm text-muted-foreground">JavaScript / TypeScript SDK. Also available: Python, REST, React components.</p>
          <CodeBlock>npm install @memory-passport/client</CodeBlock>
        </StepCard>

        {/* Step 2 */}
        <StepCard step={2} title="Initialize" icon={KeyRound} done>
          <p className="text-sm text-muted-foreground">
            Initialize from your server runtime. Tenant keys must never ship to a browser.
          </p>
          <CodeBlock lang="typescript">{`import { MemoryPassport } from "@memory-passport/client";

const mp = new MemoryPassport({
  apiKey: process.env.MP_API_KEY,
  appId: "${app.id}",
});`}</CodeBlock>
        </StepCard>

        {/* Step 3 */}
        <StepCard step={3} title="Send an event" icon={Send} done={quickstart.firstEventSent}>
          <p className="text-sm text-muted-foreground">
            Ingest a chat event. Low-sensitivity memories auto-write; sensitive ones queue for confirmation.
          </p>
          <CodeBlock lang="typescript">{`await mp.ingest({
  user_id: "usr_mia",
  agent_id: "agt_luna",
  event: {
    type: "chat",
    content: "At night I prefer calmer replies.",
  },
});`}</CodeBlock>
          <div className="flex items-center gap-2 pt-1">
            <Button onClick={handleSendEvent} disabled={sendingEvent || quickstart.firstEventSent}>
              {sendingEvent ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              {quickstart.firstEventSent ? "Event sent" : "Run test event"}
            </Button>
            {quickstart.firstEventSent && (
              <Badge variant="success" className="gap-1">
                <Check className="size-3" />
                mem_quickstart created
              </Badge>
            )}
          </div>
        </StepCard>

        {/* Step 4 */}
        <StepCard step={4} title="Retrieve memory" icon={Download} done={quickstart.firstRetrieveDone}>
          <p className="text-sm text-muted-foreground">
            Retrieve relevant memories before a response. Returned as a plain-text projection.
          </p>
          <CodeBlock lang="typescript">{`const { projection, memories } = await mp.retrieve({
  user_id: "usr_mia",
  agent_id: "agt_luna",
  query: "how should I talk to Mia tonight?",
});

// projection → inject into your model prompt
console.log(projection);
// Relevant long-term memories for this user:
// - The user prefers calm, light conversations at night.
// - The user calls this companion "Luna".
// - The user does not want work topics after 10pm.`}</CodeBlock>
          <div className="flex items-center gap-2 pt-1">
            <Button
              variant="outline"
              onClick={handleRetrieve}
              disabled={retrieving || quickstart.firstRetrieveDone || !quickstart.firstEventSent}
            >
              {retrieving ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              {quickstart.firstRetrieveDone ? "Retrieve done" : "Run retrieve test"}
            </Button>
            {!quickstart.firstEventSent && (
              <span className="text-xs text-muted-foreground">Send an event first.</span>
            )}
          </div>
        </StepCard>
      </div>

      {/* Next steps */}
      <Card className="border-dashed bg-muted/20">
        <CardContent className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
          <Terminal className="size-5 text-muted-foreground" strokeWidth={1.5} />
          <div className="flex-1">
            <p className="text-sm font-medium">What&apos;s next?</p>
            <p className="text-xs text-muted-foreground">
              Tune the memory policy, debug a specific memory, or simulate a v1→v2 migration.
            </p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" asChild>
              <Link href="/console/memory/policy">Policy</Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/console/memory/debugger">Debugger</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/app/migrate">
                Try migration
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StepCard({
  step,
  title,
  icon: Icon,
  done,
  children,
}: {
  step: number;
  title: string;
  icon: typeof Package;
  done?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card className={cn(done && "border-l-2 border-l-emerald-500")}>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex size-8 items-center justify-center rounded-lg",
              done ? "bg-emerald-500/10 text-emerald-500" : "bg-muted text-muted-foreground",
            )}
          >
            <Icon className="size-4" strokeWidth={1.5} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-muted-foreground">STEP {step}</span>
            <CardTitle className="text-base">{title}</CardTitle>
          </div>
          {done && (
            <Badge variant="success" className="ml-auto gap-1 text-[10px]">
              <Check className="size-3" /> Done
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}
