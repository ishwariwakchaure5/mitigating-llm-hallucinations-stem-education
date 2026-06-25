"""
VERA end-to-end pipeline test.
Usage:  python tests/vera_pipeline_test.py
Requires: httpx (already in backend venv)
"""

import sys
import time
from pathlib import Path

import httpx

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── config ────────────────────────────────────────────────────────────────────

BASE       = "http://localhost:8000"
PDF_PATH   = Path(__file__).parent / "vera_test_document.pdf"
EMAIL      = "pipelinetest@vera.dev"
PASSWORD   = "testpass123"
NAME       = "Pipeline Tester"
POLL_EVERY = 5          # seconds between status checks
POLL_MAX   = 300        # total timeout for document processing

CLAIMS = [
    {
        "text": "Newton's second law states that F = ma, where F is net force, m is mass, and a is acceleration",
        "expected": "correct",
    },
    {
        "text": "The Carnot efficiency is eta = 1 - T_C/T_H where T_C is cold reservoir and T_H is hot reservoir temperature in Kelvin",
        "expected": "correct",
    },
    {
        "text": "Kinetic energy is given by KE = mv squared with no half factor",
        "expected": "wrong",
    },
    {
        "text": "A free-body diagram shows all forces on an isolated object including normal force weight friction and applied force",
        "expected": "correct",
    },
    {
        "text": "Newton's second law states that force equals mass divided by acceleration F = m divided by a",
        "expected": "wrong",
    },
    {
        "text": "The ideal gas law is PV = nRT where R is the universal gas constant 8.314 J per mol per Kelvin",
        "expected": "correct",
    },
    {
        "text": (
            "Newton's second law states that F = ma, where F is net force, m is mass, and a is acceleration. "
            "Kinetic energy is given by KE = mv squared with no half factor."
        ),
        "expected": "mixed",
    },
    {
        "text": (
            "The Carnot efficiency is eta = 1 - T_C/T_H where T_C is cold reservoir and T_H is hot reservoir temperature in Kelvin. "
            "Newton's second law states that F = ma, where F is net force, m is mass, and a is acceleration. "
            "The ideal gas law is PV = nRT where R is the universal gas constant 8.314 J per mol per Kelvin"
        ),
        "expected": "correct",
    },
]

# ── helpers ───────────────────────────────────────────────────────────────────

def _die(msg: str) -> None:
    print(f"\nFATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def _check(r: httpx.Response, step: str) -> dict:
    if r.status_code not in (200, 201, 202):
        print(f"\n[{step}] HTTP {r.status_code}: {r.text}")
        sys.exit(1)
    return r.json()


def _short(text: str, n: int = 70) -> str:
    return text[:n] + "..." if len(text) > n else text


# ── step 1: auth ──────────────────────────────────────────────────────────────

def step_auth(client: httpx.Client) -> str:
    try:
        r = client.post(
            f"{BASE}/api/v1/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "name": NAME},
        )
        if r.status_code == 409:
            r = client.post(
                f"{BASE}/api/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
            )
        data = _check(r, "AUTH")
    except httpx.RequestError as e:
        _die(f"Auth request error: {e}")

    token = data.get("access_token")
    if not token:
        _die(f"No access_token in response: {data}")
    print("AUTH OK")
    return token


# ── step 2: create KB ─────────────────────────────────────────────────────────

def step_create_kb(client: httpx.Client) -> str:
    try:
        r = client.post(
            f"{BASE}/api/v1/knowledge-bases/",
            json={"name": "Physics Pipeline Test", "subject": "Physics"},
        )
        data = _check(r, "CREATE KB")
    except httpx.RequestError as e:
        _die(f"Create KB request error: {e}")

    kb_id = data["id"]
    print(f"KB CREATED: {kb_id}")
    return kb_id


# ── step 3: upload PDF ────────────────────────────────────────────────────────

def step_upload(client: httpx.Client, kb_id: str) -> str:
    if not PDF_PATH.exists():
        _die(f"Test PDF not found: {PDF_PATH}")

    try:
        with open(PDF_PATH, "rb") as fh:
            r = client.post(
                f"{BASE}/api/v1/knowledge-bases/{kb_id}/upload",
                files={"files": (PDF_PATH.name, fh, "application/pdf")},
                timeout=60,
            )
        data = _check(r, "UPLOAD")
    except httpx.RequestError as e:
        _die(f"Upload request error: {e}")

    docs = data.get("documents", [])
    if not docs:
        _die(f"No documents in upload response: {data}")
    doc_id = docs[0]["id"]
    print(f"UPLOAD ACCEPTED: {doc_id}")
    return doc_id


# ── step 4: poll until ready ──────────────────────────────────────────────────

def step_poll(client: httpx.Client, doc_id: str) -> None:
    elapsed = 0
    while elapsed < POLL_MAX:
        time.sleep(POLL_EVERY)
        elapsed += POLL_EVERY
        print(f"  polling {elapsed}s...", flush=True)
        try:
            r = client.get(f"{BASE}/api/v1/documents/{doc_id}/status")
            data = _check(r, "POLL")
        except httpx.RequestError as e:
            _die(f"Poll request error: {e}")

        status = data.get("status")
        if status == "ready":
            print("DOCUMENT READY")
            return
        if status == "failed":
            err = data.get("error_message") or data.get("errorMessage") or "unknown error"
            print(f"DOCUMENT FAILED: {err}")
            sys.exit(1)

    _die(f"Document did not become ready within {POLL_MAX}s")


# ── step 5: assert indexing ───────────────────────────────────────────────────

def step_assert_indexing(client: httpx.Client, kb_id: str) -> dict:
    try:
        r = client.get(f"{BASE}/api/v1/knowledge-bases/{kb_id}")
        kb = _check(r, "GET KB")
    except httpx.RequestError as e:
        _die(f"Get KB request error: {e}")

    chunk_count    = kb.get("chunk_count", 0)
    equation_count = kb.get("equation_count", 0)
    diagram_count  = kb.get("diagram_count", 0)

    def _pf(v: int, gt: int = 0) -> str:
        return "PASS" if v > gt else "FAIL"

    print(f"chunks:    {chunk_count}   {_pf(chunk_count)}")
    print(f"equations: {equation_count}   {_pf(equation_count)}")
    print(f"diagrams:  {diagram_count}   {_pf(diagram_count)}")

    return {"chunks": chunk_count, "equations": equation_count, "diagrams": diagram_count}


# ── step 6: run verifications ─────────────────────────────────────────────────

def step_verify(client: httpx.Client, kb_id: str) -> list:
    results = []
    for i, claim in enumerate(CLAIMS, 1):
        try:
            r = client.post(
                f"{BASE}/api/v1/verify/{kb_id}",
                json={"claim_text": claim["text"]},
                timeout=300,
            )
            data = _check(r, f"VERIFY {i}")
        except httpx.RequestError as e:
            print(f"[{i}] REQUEST ERROR: {e}")
            results.append({"pass": False, "claim": claim, "data": {}})
            continue

        verdict    = data.get("verdict", "unknown")
        confidence = data.get("confidence", 0.0)
        path_a     = data.get("path_a_score", 0.0)
        path_b     = data.get("path_b_score", 0.0)
        path_c     = data.get("path_c_score", 0.0)
        evidence   = data.get("evidence", [])
        passed     = verdict == claim["expected"]

        best_pg    = evidence[0].get("page_number") if evidence else "—"
        best_sc    = evidence[0].get("score", 0.0)  if evidence else 0.0

        tag = "PASS" if passed else "FAIL"
        print(f"[{i}] {tag}")
        print(f"     claim:      {_short(claim['text'])}")
        print(f"     verdict:    {verdict}  (expected: {claim['expected']})")
        print(f"     confidence: {round(confidence * 100)}%")
        print(f"     path_a: {round(path_a, 3)}  path_b: {round(path_b, 3)}  path_c: {round(path_c, 3)}")
        print(f"     evidence: {len(evidence)} chunks, best match p.{best_pg} ({round(best_sc * 100)}%)")

        results.append({"pass": passed, "claim": claim, "data": data})

    return results


# ── step 7: cleanup ───────────────────────────────────────────────────────────

def step_cleanup(client: httpx.Client, kb_id: str) -> None:
    try:
        r = client.delete(f"{BASE}/api/v1/knowledge-bases/{kb_id}")
        if r.status_code not in (200, 204):
            print(f"  Cleanup warning: HTTP {r.status_code}")
    except httpx.RequestError as e:
        print(f"  Cleanup warning: {e}")
    print("KB DELETED")


# ── step 8: final report ──────────────────────────────────────────────────────

def print_report(
    auth_ok: bool,
    upload_ok: bool,
    processing_ok: bool,
    indexing: dict,
    verify_results: list,
) -> bool:
    matched = sum(1 for r in verify_results if r["pass"])
    total   = len(verify_results)
    overall = auth_ok and upload_ok and processing_ok and matched == total

    print()
    print("════════════════════════════════")
    print("  VERA PIPELINE TEST RESULTS")
    print("════════════════════════════════")
    print(f"  Auth          {'PASS' if auth_ok        else 'FAIL'}")
    print(f"  Upload        {'PASS' if upload_ok      else 'FAIL'}")
    print(f"  Processing    {'PASS' if processing_ok  else 'FAIL'}")
    print(f"  Indexing      chunks={indexing.get('chunks',0)}  equations={indexing.get('equations',0)}  diagrams={indexing.get('diagrams',0)}")
    print(f"  Verdicts      {matched}/{total} matched expected")
    print("────────────────────────────────")
    for i, r in enumerate(verify_results, 1):
        tag     = "PASS" if r["pass"] else "FAIL"
        verdict = r["data"].get("verdict", "—")
        snippet = _short(r["claim"]["text"], 50)
        print(f"  [{i}] {tag}  {verdict:<10}  \"{snippet}\"")
    print("────────────────────────────────")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print("════════════════════════════════")
    return overall


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    auth_ok      = False
    upload_ok    = False
    processing_ok = False
    indexing     = {}
    verify_results: list = []
    kb_id        = None

    with httpx.Client(timeout=30) as client:
        # 1. Auth
        token = step_auth(client)
        auth_ok = True
        client.headers["Authorization"] = f"Bearer {token}"

        # 2. Create KB
        kb_id = step_create_kb(client)

        # 3. Upload
        doc_id = step_upload(client, kb_id)
        upload_ok = True

        # 4. Poll
        step_poll(client, doc_id)
        processing_ok = True

        # 5. Assert indexing
        indexing = step_assert_indexing(client, kb_id)

        # 6. Verify
        verify_results = step_verify(client, kb_id)

        # 7. Cleanup
        step_cleanup(client, kb_id)

    # 8. Report
    passed = print_report(auth_ok, upload_ok, processing_ok, indexing, verify_results)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
