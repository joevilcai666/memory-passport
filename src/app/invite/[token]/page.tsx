"use client";

import * as React from "react";
import { CheckCircle2, Loader2, ShieldCheck, UserPlus } from "lucide-react";
import { useParams } from "next/navigation";

import { PoweredByMemoryPassport } from "@/components/brand/PoweredByMemoryPassport";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";
import type { PublicTeamInvite, TeamMember } from "@/lib/types";

export default function InviteAcceptancePage() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const [invite, setInvite] = React.useState<PublicTeamInvite | null>(null);
  const [member, setMember] = React.useState<TeamMember | null>(null);
  const [name, setName] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [accepting, setAccepting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    api.previewTeamInvite(token)
      .then((preview) => {
        if (!active) return;
        setInvite(preview);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "The invitation could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  const accept = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim() || accepting) return;
    setAccepting(true);
    try {
      const accepted = await api.acceptTeamInvite(token, { name: name.trim() });
      setMember(accepted);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The invitation could not be accepted.");
    } finally {
      setAccepting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {member ? <CheckCircle2 className="size-5" /> : <UserPlus className="size-5" />}
          </div>
          <CardTitle>
            {loading
              ? "Loading invitation"
              : member
                ? "Invitation accepted"
                : invite
                  ? `Join ${invite.tenant_name}`
                  : "Invitation unavailable"}
          </CardTitle>
          <CardDescription>
            {member
              ? `${member.name} now has ${member.role} access.`
              : invite
                ? `${invite.email} was invited as ${invite.role}.`
                : "This link may be invalid, expired, or already used."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : member ? (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4 text-center text-sm">
              You can now close this page and sign in to the console.
            </div>
          ) : invite ? (
            <form onSubmit={accept} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="invite-name">Your name</Label>
                <Input
                  id="invite-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  autoComplete="name"
                  required
                />
              </div>
              {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={!name.trim() || accepting}>
                {accepting ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
                {accepting ? "Accepting..." : "Accept invitation"}
              </Button>
            </form>
          ) : (
            <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-center text-sm text-destructive">
              {error ?? "The invitation could not be loaded."}
            </p>
          )}
          <div className="mt-6 border-t pt-4">
            <PoweredByMemoryPassport />
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
