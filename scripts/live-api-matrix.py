from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

import httpx


BASE = os.environ.get("MP_API_URL", "http://127.0.0.1:8000").rstrip("/")
HMS_BASE = os.environ.get("HMS_API_URL", "http://127.0.0.1:18080").rstrip("/")
MP_KEY = os.environ.get("MP_API_KEY", "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd")
HMS_KEY = os.environ.get("HMS_API_KEY", "hms_tenant_luna_change_me")
AUTH = {"Authorization": f"Bearer {MP_KEY}"}
RESULT_PATH = Path(
    os.environ.get("MP_MATRIX_RESULT_PATH", str(Path(__file__).with_name("live_api_results.json")))
)
RUN = f"matrix-{uuid.uuid4().hex[:10]}"
results: list[dict[str, Any]] = []


def body_preview(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text[:500]


def call(
    client: httpx.Client,
    name: str,
    method: str,
    path: str,
    expected: int | set[int],
    *,
    auth: bool = True,
    base: str = BASE,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    expected_set = {expected} if isinstance(expected, int) else set(expected)
    merged_headers = dict(AUTH if auth else {})
    if headers:
        merged_headers.update(headers)
    response = client.request(method, f"{base}{path}", headers=merged_headers, **kwargs)
    passed = response.status_code in expected_set
    results.append(
        {
            "name": name,
            "method": method,
            "path": path,
            "expected_status": sorted(expected_set),
            "actual_status": response.status_code,
            "passed": passed,
            "body": body_preview(response),
        }
    )
    if not passed:
        raise AssertionError(
            f"{name}: expected {sorted(expected_set)}, got {response.status_code}: "
            f"{response.text[:1000]}"
        )
    return response


def check(name: str, condition: bool, detail: Any) -> None:
    results.append({"name": name, "kind": "assertion", "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def policy_payload(app_id: str, agent_id: str, action: str, *, cross_brand: bool = False):
    return {
        "app_id": app_id,
        "agent_id": agent_id,
        "auto_write_rules": [
            {
                "memory_type": "preference",
                "action": action,
                "sensitivity": "S0",
                "ttl_days": None,
            }
        ],
        "portability": {
            "layer": "portable",
            "cross_device": True,
            "cross_role": True,
            "cross_model": True,
            "cross_brand_app": cross_brand,
        },
        "retrieval": {
            "max_memories_per_response": 3,
            "include_sensitive_in_prompt": False,
        },
    }


def ingest_payload(user_id: str, agent_id: str, relationship_id: str, label: str, *, device_id=None):
    payload = {
        "user_id": user_id,
        "agent_id": agent_id,
        "relationship_id": relationship_id,
        "source_type": "explicit_instruction",
        "content": f"{RUN} remembers {label}",
        "quote": f"Remember {label}",
        "event_id": f"evt-{RUN}-{label.replace(' ', '-')}",
    }
    if device_id is not None:
        payload["device_id"] = device_id
    return payload


def main() -> None:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        health = call(client, "public health", "GET", "/v1/health", 200, auth=False).json()
        check("health reports complete demo stack", health == {
            "mp": "ok", "hms": "ok", "db": "ok", "memory_engine": "demo"
        }, health)
        call(client, "Swagger HTML", "GET", "/docs", 200, auth=False)
        openapi = call(client, "OpenAPI JSON", "GET", "/openapi.json", 200, auth=False).json()
        operations = {
            (method.upper(), path)
            for path, item in openapi["paths"].items()
            for method in item
            if method.lower() in {"get", "post", "patch", "delete", "put"}
        }
        required_operations = {
            ("GET", "/v1/apps"),
            ("GET", "/v1/apps/{app_id}"),
            ("POST", "/v1/apps/{app_id}/api-keys"),
            ("POST", "/v1/apps/{app_id}/api-keys/{key_id}/rotate"),
            ("PATCH", "/v1/users/{user_id}/consent"),
            ("POST", "/v1/debug/traces/{trace_id}/feedback"),
            ("GET", "/v1/team"),
            ("POST", "/v1/team/invites"),
            ("GET", "/v1/public/team-invites/{token}"),
            ("POST", "/v1/public/team-invites/{token}/accept"),
        }
        check(
            "OpenAPI exposes the complete remediated product surface",
            len(operations) == 37 and required_operations <= operations,
            sorted(operations),
        )

        call(client, "HMS public health", "GET", "/health", 200, auth=False, base=HMS_BASE)
        call(client, "HMS banks reject missing auth", "GET", "/v1/default/banks", 401, auth=False, base=HMS_BASE)
        hms_banks = call(
            client,
            "HMS banks accept tenant auth",
            "GET",
            "/v1/default/banks",
            200,
            auth=False,
            base=HMS_BASE,
            headers={"Authorization": f"Bearer {HMS_KEY}"},
        ).json()
        check("HMS seed has four or more banks", len(hms_banks["banks"]) >= 4, hms_banks)

        call(client, "business endpoint rejects missing auth", "GET", "/v1/memories", 401, auth=False)
        call(
            client,
            "business endpoint rejects bad scheme",
            "GET",
            "/v1/memories",
            401,
            auth=False,
            headers={"Authorization": "Basic invalid"},
        )
        call(
            client,
            "business endpoint rejects unknown key",
            "GET",
            "/v1/memories",
            401,
            auth=False,
            headers={"Authorization": "Bearer mp_sandbox_unknown"},
        )
        call(client, "seed bearer authenticates", "GET", "/v1/memories?page_size=1", 200)
        call(
            client,
            "documented bare token authenticates",
            "GET",
            "/v1/memories?page_size=1",
            200,
            auth=False,
            headers={"Authorization": MP_KEY},
        )

        app_created = call(
            client,
            "create disposable app",
            "POST",
            "/v1/apps",
            201,
            json={
                "name": RUN,
                "product_type": "hybrid",
                "environment": "sandbox",
                "data_region": "ap-southeast-1",
                "show_powered_by": True,
            },
        ).json()
        app_id = app_created["app"]["id"]
        generated_key = app_created["api_key"]["key"]
        check("created app returns a usable full key", generated_key.startswith("mp_sandbox_"), app_created)
        call(
            client,
            "new app key authenticates same tenant",
            "GET",
            "/v1/memories?page_size=1",
            200,
            auth=False,
            headers={"Authorization": f"Bearer {generated_key}"},
        )
        apps = call(client, "list apps includes created app", "GET", "/v1/apps", 200).json()
        check("created app appears in list", app_id in {item["id"] for item in apps["items"]}, apps)
        app_detail = call(client, "read created app detail", "GET", f"/v1/apps/{app_id}", 200).json()
        check("app detail masks stored keys", all("key" not in item for item in app_detail["api_keys"]), app_detail)
        extra_key = call(
            client,
            "create additional app key",
            "POST",
            f"/v1/apps/{app_id}/api-keys",
            201,
            json={"label": "matrix key", "environment": "sandbox"},
        ).json()
        check("additional key is returned once in full", extra_key["key"].startswith("mp_sandbox_"), extra_key)
        rotated_key = call(
            client,
            "rotate additional app key",
            "POST",
            f"/v1/apps/{app_id}/api-keys/{extra_key['id']}/rotate",
            201,
        ).json()
        call(
            client,
            "rotated old key is revoked",
            "GET",
            "/v1/memories?page_size=1",
            401,
            auth=False,
            headers={"Authorization": f"Bearer {extra_key['key']}"},
        )
        call(
            client,
            "rotated new key authenticates",
            "GET",
            "/v1/memories?page_size=1",
            200,
            auth=False,
            headers={"Authorization": f"Bearer {rotated_key['key']}"},
        )

        team_before = call(client, "read tenant team", "GET", "/v1/team", 200).json()
        invite_created = call(
            client,
            "create one-time team invite",
            "POST",
            "/v1/team/invites",
            201,
            json={"email": f"{RUN}@example.com", "role": "Support"},
        ).json()
        invite_token = invite_created["token"]
        invite_preview = call(
            client,
            "public invite preview",
            "GET",
            f"/v1/public/team-invites/{invite_token}",
            200,
            auth=False,
        ).json()
        check("invite preview is tenant-scoped", invite_preview["email"] == f"{RUN}@example.com", invite_preview)
        accepted_member = call(
            client,
            "public invite acceptance",
            "POST",
            f"/v1/public/team-invites/{invite_token}/accept",
            200,
            auth=False,
            json={"name": f"Member {RUN}", "avatar_color": "#123456"},
        ).json()
        call(
            client,
            "accepted invite cannot be reused",
            "POST",
            f"/v1/public/team-invites/{invite_token}/accept",
            409,
            auth=False,
            json={"name": "Duplicate"},
        )
        team_after = call(client, "accepted member appears in team", "GET", "/v1/team", 200).json()
        check(
            "team member persisted exactly once",
            len(team_after["members"]) == len(team_before["members"]) + 1
            and accepted_member["id"] in {item["id"] for item in team_after["members"]},
            team_after,
        )

        agent = call(
            client,
            "create disposable agent",
            "POST",
            "/v1/agents",
            201,
            json={
                "app_id": app_id,
                "name": f"Agent {RUN}",
                "type": "robot",
                "persona_version": "v-test",
                "allowed_memory_types": ["preference", "event", "relationship"],
                "emoji": "T",
            },
        ).json()
        agent_id = agent["id"]
        user_payload = {
            "app_id": app_id,
            "external_user_id": RUN,
            "age_group": "adult",
            "region": "CN",
            "display_name": f"User {RUN}",
        }
        user_first = call(client, "create disposable user", "POST", "/v1/users", 201, json=user_payload).json()
        user_second = call(client, "idempotent user sync", "POST", "/v1/users", 201, json=user_payload).json()
        user_id = user_first["id"]
        check("user create is idempotent", user_second["id"] == user_id, {"first": user_first, "second": user_second})
        consent_off = call(
            client,
            "explicitly disable memory consent",
            "PATCH",
            f"/v1/users/{user_id}/consent",
            200,
            json={"memory_enabled": False},
        ).json()
        check("consent false persists", consent_off["memory_enabled"] is False, consent_off)
        consent_on = call(
            client,
            "explicitly enable memory consent",
            "PATCH",
            f"/v1/users/{user_id}/consent",
            200,
            json={"memory_enabled": True},
        ).json()
        check("consent true persists", consent_on["memory_enabled"] is True, consent_on)

        base_rel = call(
            client,
            "create base relationship",
            "POST",
            "/v1/relationships",
            201,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "relationship_type": "robot",
                "memory_enabled": True,
            },
        ).json()
        base_rel_id = base_rel["id"]

        def register_device(label: str):
            return call(
                client,
                f"register device {label}",
                "POST",
                "/v1/devices/register",
                201,
                json={
                    "model": f"Matrix {label}",
                    "generation": "v-test",
                    "serial_number_hash": f"{RUN}-{label}",
                },
            ).json()

        unbind_device = register_device("unbind")
        unbind_id = unbind_device["device"]["id"]
        call(
            client,
            "bind rejects wrong pairing code",
            "POST",
            "/v1/devices/bind",
            403,
            json={"device_id": unbind_id, "user_id": user_id, "pairing_code": "wrong"},
        )
        call(
            client,
            "bind schema rejects missing pairing code",
            "POST",
            "/v1/devices/bind",
            422,
            json={"device_id": unbind_id, "user_id": user_id},
        )
        call(
            client,
            "bind registered device",
            "POST",
            "/v1/devices/bind",
            200,
            json={
                "device_id": unbind_id,
                "user_id": user_id,
                "pairing_code": unbind_device["pairing_code"],
            },
        )
        call(
            client,
            "duplicate bind conflicts",
            "POST",
            "/v1/devices/bind",
            409,
            json={
                "device_id": unbind_id,
                "user_id": user_id,
                "pairing_code": unbind_device["pairing_code"],
            },
        )
        call(client, "unbind bound device", "POST", "/v1/devices/unbind", 200, json={"device_id": unbind_id})
        call(client, "duplicate unbind conflicts", "POST", "/v1/devices/unbind", 409, json={"device_id": unbind_id})

        wipe_device = register_device("wipe")
        wipe_id = wipe_device["device"]["id"]
        call(
            client,
            "bind wipe-test device",
            "POST",
            "/v1/devices/bind",
            200,
            json={"device_id": wipe_id, "user_id": user_id, "pairing_code": wipe_device["pairing_code"]},
        )
        wipe_rel_id = call(
            client,
            "create wipe-test relationship",
            "POST",
            "/v1/relationships",
            201,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "device_id": wipe_id,
                "relationship_type": "robot",
                "memory_enabled": True,
            },
        ).json()["id"]

        source_device = register_device("source")
        source_id = source_device["device"]["id"]
        call(
            client,
            "bind migration source device",
            "POST",
            "/v1/devices/bind",
            200,
            json={"device_id": source_id, "user_id": user_id, "pairing_code": source_device["pairing_code"]},
        )
        target_device = register_device("target")
        target_id = target_device["device"]["id"]
        source_rel_id = call(
            client,
            "create migration source relationship",
            "POST",
            "/v1/relationships",
            201,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "device_id": source_id,
                "relationship_type": "robot",
                "memory_enabled": True,
            },
        ).json()["id"]

        call(
            client,
            "policy rejects cross-brand portability",
            "POST",
            "/v1/policies",
            422,
            json=policy_payload(app_id, agent_id, "block", cross_brand=True),
        )
        call(
            client,
            "create blocking policy",
            "POST",
            "/v1/policies",
            201,
            json=policy_payload(app_id, agent_id, "block"),
        )
        blocked = call(
            client,
            "live policy blocks ingest",
            "POST",
            "/v1/events/ingest",
            201,
            json=ingest_payload(user_id, agent_id, base_rel_id, "blocked preference"),
        ).json()
        check("blocked ingest returns BLOCKED only", [r["action"] for r in blocked["results"]] == ["BLOCKED"], blocked)

        call(
            client,
            "update policy to confirmation",
            "POST",
            "/v1/policies",
            200,
            json=policy_payload(app_id, agent_id, "confirm"),
        )
        candidate = call(
            client,
            "confirmation ingest creates candidate",
            "POST",
            "/v1/events/ingest",
            201,
            json=ingest_payload(user_id, agent_id, base_rel_id, "candidate preference"),
        ).json()
        candidate_id = next(item["id"] for item in candidate["results"] if item["action"] == "ADD")
        candidate_row = call(
            client,
            "candidate visible in filtered list",
            "GET",
            f"/v1/memories?user_id={user_id}&status=candidate",
            200,
        ).json()
        check("candidate list contains new memory", candidate_id in {r["id"] for r in candidate_row["items"]}, candidate_row)
        activated = call(
            client,
            "legal candidate-to-active transition",
            "PATCH",
            f"/v1/memories/{candidate_id}",
            200,
            json={"status": "active"},
        ).json()
        check("candidate activated", activated["status"] == "active", activated)

        call(
            client,
            "update policy to auto-write",
            "POST",
            "/v1/policies",
            200,
            json=policy_payload(app_id, agent_id, "auto_write"),
        )
        source_ingest = call(
            client,
            "ingest portable device-only migration memory",
            "POST",
            "/v1/events/ingest",
            201,
            json=ingest_payload(user_id, agent_id, source_rel_id, "portable source token", device_id=source_id),
        ).json()
        source_memory_id = next(item["id"] for item in source_ingest["results"] if item["action"] == "ADD")
        wipe_ingest = call(
            client,
            "ingest wipe-test device-only memory",
            "POST",
            "/v1/events/ingest",
            201,
            json=ingest_payload(user_id, agent_id, wipe_rel_id, "wipe exclusion token", device_id=wipe_id),
        ).json()
        wipe_memory_id = next(item["id"] for item in wipe_ingest["results"] if item["action"] == "ADD")

        without_device = call(
            client,
            "device-only memory excluded without device caller",
            "POST",
            "/v1/memories/retrieve",
            200,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "relationship_id": source_rel_id,
                "query": "portable source token",
                "model": "live-matrix",
            },
        ).json()
        check("non-device caller cannot see device-only memory", source_memory_id not in {r["id"] for r in without_device["results"]}, without_device)
        with_device = call(
            client,
            "bound device retrieves device-only memory",
            "POST",
            "/v1/memories/retrieve",
            200,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "relationship_id": source_rel_id,
                "device_id": source_id,
                "query": "portable source token",
                "model": "live-matrix",
            },
        ).json()
        check("bound device sees device-only memory", source_memory_id in {r["id"] for r in with_device["results"]}, with_device)
        trace_id = with_device["trace_id"]
        trace = call(client, "retrieve trace round trip", "GET", f"/v1/debug/traces/{trace_id}", 200).json()
        check("trace records query and projection", trace["query"] == "portable source token" and trace["projected"], trace)
        trace_with_feedback = call(
            client,
            "persist trace feedback",
            "POST",
            f"/v1/debug/traces/{trace_id}/feedback",
            200,
            json={"memory_id": source_memory_id, "category": "useful"},
        ).json()
        check(
            "trace feedback survives response round trip",
            trace_with_feedback["feedback"]["memory_id"] == source_memory_id
            and trace_with_feedback["feedback"]["category"] == "useful",
            trace_with_feedback,
        )

        wipe_result = call(client, "wipe bound device", "POST", "/v1/devices/wipe", 200, json={"device_id": wipe_id}).json()
        check("wipe tombstones its device-only memory", wipe_result["tombstoned_memories"] >= 1, wipe_result)
        wiped_retrieve = call(
            client,
            "wiped device cannot retrieve",
            "POST",
            "/v1/memories/retrieve",
            200,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "relationship_id": wipe_rel_id,
                "device_id": wipe_id,
                "query": "wipe exclusion token",
                "model": "live-matrix",
            },
        ).json()
        check("wiped memory excluded", wipe_memory_id not in {r["id"] for r in wiped_retrieve["results"]}, wiped_retrieve)

        active_list = call(
            client,
            "all documented memory filters and pagination",
            "GET",
            (
                f"/v1/memories?user_id={user_id}&type=preference&status=active&"
                f"scope=device_only&relationship_id={source_rel_id}&agent_id={agent_id}&"
                f"device_id={source_id}&page=1&page_size=1"
            ),
            200,
        ).json()
        check("seven filters select source memory", active_list["total"] >= 1 and active_list["items"][0]["id"] == source_memory_id, active_list)

        edited = call(
            client,
            "content edit creates version",
            "PATCH",
            f"/v1/memories/{candidate_id}",
            200,
            json={"content": f"{RUN} edited preference"},
        ).json()
        edited_id = edited["id"]
        check("edit preserves supersedes chain", edited["version"] == 2 and edited["supersedes"] == candidate_id, edited)
        call(
            client,
            "illegal active-to-candidate transition conflicts",
            "PATCH",
            f"/v1/memories/{edited_id}",
            409,
            json={"status": "candidate"},
        )
        archived = call(
            client,
            "archive edited memory before deletion",
            "PATCH",
            f"/v1/memories/{edited_id}",
            200,
            json={"status": "archived"},
        ).json()
        check("edited memory archived", archived["status"] == "archived", archived)
        deleted = call(client, "tombstone archived memory", "DELETE", f"/v1/memories/{edited_id}", 200).json()
        check("delete is tombstone", deleted["status"] == "deleted", deleted)
        deleted_list = call(
            client,
            "deleted opt-in list",
            "GET",
            f"/v1/memories?user_id={user_id}&status=deleted&include_deleted=true",
            200,
        ).json()
        check("include_deleted exposes tombstone", edited_id in {r["id"] for r in deleted_list["items"]}, deleted_list)

        preview_payload = {
            "user_id": user_id,
            "source_relationship_id": source_rel_id,
            "target_relationship_id": f"target-{RUN}",
            "source_device_id": source_id,
            "target_device_id": target_id,
        }
        preview = call(client, "migration preview", "POST", "/v1/migrations/preview", 201, json=preview_payload).json()
        migration_id = preview["migration_id"]
        check("preview recommends portable source memory", source_memory_id in preview["recommended"]["memory_ids"], preview)
        preview_again = call(client, "migration preview idempotent", "POST", "/v1/migrations/preview", 200, json=preview_payload).json()
        check("preview reuses migration id", preview_again["migration_id"] == migration_id, preview_again)
        executed = call(
            client,
            "execute migration and remove old access",
            "POST",
            "/v1/migrations/execute",
            200,
            json={
                "migration_id": migration_id,
                "selected_memory_ids": [source_memory_id],
                "old_device_access": "remove",
            },
        ).json()
        check("migration completes", executed["status"] == "completed", executed)
        looked_up = call(client, "migration lookup", "GET", f"/v1/migrations/{migration_id}", 200).json()
        check("lookup preserves selection", looked_up["selected_memory_ids"] == [source_memory_id], looked_up)
        rolled_back = call(client, "migration rollback", "POST", f"/v1/migrations/{migration_id}/rollback", 200).json()
        check("migration rolls back", rolled_back["status"] == "rolled_back", rolled_back)

        audit_all = call(client, "audit list pagination", "GET", "/v1/audit_logs?page=1&page_size=5", 200).json()
        check("audit paginates", len(audit_all["items"]) <= 5 and audit_all["total"] >= len(audit_all["items"]), audit_all)
        call(client, "audit action filter", "GET", "/v1/audit_logs?action=memory.edited", 200)
        call(
            client,
            "aggregate reversed window rejected",
            "GET",
            "/v1/usage?since=2026-07-22T10%3A00%3A00Z&until=2026-07-22T09%3A00%3A00Z",
            422,
        )
        usage = call(client, "usage five dimensions", "GET", "/v1/usage", 200).json()
        check(
            "usage exposes all five dimensions",
            set(usage) == {
                "since",
                "until",
                "memory_mau",
                "memory_ops",
                "storage",
                "device_activations",
                "migration_count",
            },
            usage,
        )

        export_id = call(
            client,
            "create asynchronous export",
            "POST",
            "/v1/exports",
            202,
            json={"user_id": user_id},
        ).json()["export_id"]
        export_status = None
        for _ in range(20):
            export_status = call(client, "poll export status", "GET", f"/v1/exports/{export_id}", 200).json()
            if export_status["status"] != "pending":
                break
            time.sleep(0.1)
        check("export completed", export_status and export_status["status"] == "completed", export_status)
        parsed = urllib.parse.urlsplit(export_status["download_url"])
        token = urllib.parse.parse_qs(parsed.query)["token"][0]
        call(
            client,
            "export rejects wrong token",
            "GET",
            f"/v1/exports/{export_id}/download?token=wrong",
            403,
        )
        bundle = call(
            client,
            "download model-neutral export",
            "GET",
            f"/v1/exports/{export_id}/download?token={urllib.parse.quote(token)}",
            200,
        ).json()
        serialized_bundle = json.dumps(bundle).lower()
        check(
            "export is neutral and secret-free",
            bundle["format"] == "memory-passport/v1"
            and "embedding" not in serialized_bundle
            and MP_KEY.lower() not in serialized_bundle,
            {"format": bundle.get("format"), "memory_count": len(bundle.get("memories", []))},
        )
        call(
            client,
            "export token is one-shot",
            "GET",
            f"/v1/exports/{export_id}/download?token={urllib.parse.quote(token)}",
            403,
        )

        deletion = call(client, "delete disposable user", "POST", "/v1/delete_user", 200, json={"user_id": user_id}).json()
        check(
            "delete-user cascades and revokes passport",
            deletion["hms_bank_deleted"] and deletion["passport_status"] == "deleted" and deletion["tombstoned_memories"] >= 1,
            deletion,
        )
        after_delete = call(
            client,
            "deleted passport retrieve short-circuits",
            "POST",
            "/v1/memories/retrieve",
            200,
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "relationship_id": source_rel_id,
                "query": "portable source token",
                "model": "live-matrix",
            },
        ).json()
        check("deleted user retrieve is empty but traced", after_delete["results"] == [] and after_delete["trace_id"], after_delete)


if __name__ == "__main__":
    exit_code = 0
    error = None
    try:
        main()
    except Exception as exc:
        exit_code = 1
        error = f"{type(exc).__name__}: {exc}"
        print(error, file=sys.stderr)
    finally:
        summary = {
            "run": RUN,
            "passed": sum(1 for item in results if item.get("passed")),
            "failed": sum(1 for item in results if not item.get("passed")),
            "total": len(results),
            "error": error,
            "results": results,
        }
        RESULT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: summary[k] for k in ("run", "passed", "failed", "total", "error")}, ensure_ascii=False))
    raise SystemExit(exit_code)
