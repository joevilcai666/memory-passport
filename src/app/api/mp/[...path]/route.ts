import { forwardMpRequest } from "@/server/mp-gateway";

type GatewayContext = {
  params: Promise<{ path: string[] }>;
};

async function handle(request: Request, context: GatewayContext) {
  const { path } = await context.params;
  return forwardMpRequest(request, path);
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
