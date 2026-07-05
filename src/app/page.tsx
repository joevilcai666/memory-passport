import Link from "next/link";
import {
  ArrowRight,
  Smartphone,
  Brain,
  ShieldCheck,
  Fingerprint,
  Plane,
  KeyRound,
  Layers,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StampMark } from "@/components/brand/StampMark";
import { PoweredByMemoryPassport } from "@/components/brand/PoweredByMemoryPassport";

const principles = [
  {
    icon: Fingerprint,
    title: "Non-custodial",
    body: "Memories belong to the user's Passport — not the app. Anchored by passport_id, never the vendor.",
  },
  {
    icon: Plane,
    title: "Portable-native",
    body: "Cross-device, cross-role, cross-model by architecture. The wedge, written in from day one.",
  },
  {
    icon: ShieldCheck,
    title: "Yours to control",
    body: "Viewable, editable, deletable. Tombstone-proven. Every access writes the audit log.",
  },
];

const axes = [
  { label: "Cross-device", note: "within brand", b2b: "Ally", llm: "—", priority: "P0 wedge" },
  { label: "Cross-role", note: "within brand", b2b: "Ally", llm: "—", priority: "P0" },
  { label: "Cross-model", note: "LLM-neutral", b2b: "Ally", llm: "Strong defense", priority: "P0 moat" },
  { label: "Cross-brand app", note: "Luna → other", b2b: "Hostile", llm: "—", priority: "P2 deferred" },
];

export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b bg-background/70 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <div className="inline-flex items-center gap-2.5">
            <StampMark className="size-7 text-primary" />
            <span className="font-semibold tracking-tight text-[15px]">Memory Passport</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
              <Link href="/console">Console</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/console">
                Start building
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-4xl px-5 pb-16 pt-20 text-center md:pt-28">
          <Badge variant="ink" className="mb-6 gap-1.5">
            <span className="size-1.5 rounded-full bg-primary" />
            Portable memory infrastructure · v0.1
          </Badge>

          <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
            Switch devices,
            <br />
            not relationships.
            <br />
            <span className="text-primary">Switch models, not memory.</span>
          </h1>

          <p className="mx-auto mt-6 max-w-xl text-pretty text-base text-muted-foreground md:text-lg">
            A user-owned, cross-model, cross-device long-term memory layer for AI
            companions and robots. Embedded as an SDK — the relationship travels
            with the user, not the vendor.
          </p>

          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" asChild className="w-full sm:w-auto">
              <Link href="/console">
                <Layers className="size-4" />
                I&apos;m building a companion
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild className="w-full sm:w-auto">
              <Link href="/app/memory">
                <Smartphone className="size-4" />
                See it as a user
              </Link>
            </Button>
          </div>

          <p className="mt-4 text-xs text-muted-foreground/70">
            Walk the Luna story end-to-end: setup → memories form →{" "}
            <Link href="/app/migrate" className="underline underline-offset-2 hover:text-foreground">
              v1→v2 migration
            </Link>
          </p>
        </div>
      </section>

      {/* The Privy analogy / non-custodial */}
      <section className="border-t bg-muted/30">
        <div className="mx-auto max-w-5xl px-5 py-16">
          <div className="grid gap-10 md:grid-cols-[1fr_1.2fr] md:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                The idea
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
                Like a wallet. But for memory.
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground md:text-base">
                Privy made the wallet non-custodial and portable across apps. We
                do the same for memory: the soul isn&apos;t &quot;memory&quot; —
                every LLM will ship that. The soul is that memory{" "}
                <span className="font-medium text-foreground">
                  belongs to the user and travels cross-model.
                </span>{" "}
                That&apos;s the only thing that defends against vendor lock-in.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {principles.map((p) => (
                <div
                  key={p.title}
                  className="rounded-xl border bg-card p-5 shadow-sm"
                >
                  <p.icon className="size-5 text-primary" strokeWidth={1.5} />
                  <h3 className="mt-3 text-sm font-semibold">{p.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {p.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* The four axes of portability */}
      <section className="border-t">
        <div className="mx-auto max-w-5xl px-5 py-16">
          <div className="mb-8 max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Portability, by design
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              Four axes. Three shipping in v0.1.
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              The non-consensus alpha: memory must be cross-model neutral —
              because only that defends against LLM-vendor, hardware-generation,
              and single-app lock-in.
            </p>
          </div>

          <div className="overflow-hidden rounded-xl border">
            <div className="grid grid-cols-[1.4fr_0.8fr_1fr_0.9fr] border-b bg-muted/40 px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              <div>Axis</div>
              <div>B2B</div>
              <div>LLM defense</div>
              <div>Priority</div>
            </div>
            {axes.map((a, i) => (
              <div
                key={a.label}
                className={`grid grid-cols-[1.4fr_0.8fr_1fr_0.9fr] items-center px-4 py-3.5 text-sm ${
                  i < axes.length - 1 ? "border-b" : ""
                }`}
              >
                <div>
                  <div className="font-medium">{a.label}</div>
                  <div className="text-xs text-muted-foreground">{a.note}</div>
                </div>
                <div className="text-muted-foreground">{a.b2b}</div>
                <div className="text-muted-foreground">{a.llm}</div>
                <div>
                  {a.priority.includes("deferred") ? (
                    <Badge variant="outline" className="text-[10px]">{a.priority}</Badge>
                  ) : (
                    <Badge variant="ink" className="text-[10px]">{a.priority}</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The wedge demo CTA */}
      <section className="border-t bg-primary text-primary-foreground">
        <div className="mx-auto max-w-4xl px-5 py-16 text-center md:py-20">
          <Brain className="mx-auto size-7 opacity-90" strokeWidth={1.5} />
          <h2 className="mt-4 text-2xl font-semibold tracking-tight md:text-4xl">
            Upgrade the body. Keep the relationship.
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-pretty text-sm text-primary-foreground/80 md:text-base">
            The canonical demo: a user moves from Luna Robot v1 to v2. Their
            memories are reviewed, selected, and inherited — across devices and
            models. This is the wedge that proves portability.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" variant="secondary" asChild>
              <Link href="/app/migrate">
                See the migration
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button
              size="lg"
              variant="outline"
              asChild
              className="border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
            >
              <Link href="/console">
                <KeyRound className="size-4" />
                Explore the console
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="mx-auto max-w-5xl px-5 py-12">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="inline-flex items-center gap-2.5">
              <StampMark className="size-6 text-primary" />
              <span className="text-sm font-semibold">Memory Passport</span>
            </div>
            <div className="flex items-center gap-5 text-xs text-muted-foreground">
              <Link href="/console" className="hover:text-foreground">Console</Link>
              <Link href="/app/memory" className="hover:text-foreground">Memory Center</Link>
              <Link href="/app/consent" className="hover:text-foreground">Consent</Link>
            </div>
          </div>
          <div className="mt-8 flex items-center justify-center gap-2 text-xs text-muted-foreground/70">
            <Check className="size-3" />
            <span>Prototype · seeded with the Luna dataset · no real backend</span>
          </div>
        </div>
      </footer>

      {/* The watermark seeds the network effect even here */}
      <div className="border-t bg-muted/30">
        <div className="mx-auto max-w-5xl px-5 py-6">
          <PoweredByMemoryPassport align="start" />
        </div>
      </div>
    </div>
  );
}
