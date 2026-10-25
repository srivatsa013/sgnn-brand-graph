"""Wave 2 GDELT collection. Prepared on 2026-10-25. Not started.

The default command prints the slice count and exits. It does not call
gcloud or bq. --cost-check is the first real step, and only with
--confirm-wave2. The full pass waits for that cost check.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = ROOT / "configs" / "wave2_gdelt_aliases.json"
SLICES = ROOT / "configs" / "wave2_gdelt_slices.jsonl"
CONFIG = ROOT / "configs" / "wave2_gdelt_supervisor.json"
COST = ROOT / "reports" / "wave2_gdelt_cost.json"
CHECK = ROOT / "eval" / "results" / "wave2_gdelt_cost_check.json"
OUT = ROOT / "data" / "interim" / "wave2" / "gdelt"
DISK_PAUSE = 6_000_000_000
SLICE_TIMEOUT = 20 * 60


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def load_aliases() -> list[dict]:
    return json.loads(ALIASES.read_text())["items"]


def load_slices() -> list[dict]:
    return [json.loads(line) for line in SLICES.read_text().splitlines() if line.strip()]


def alias_allowed(node_mids: list[str], alias_mid: str) -> bool:
    return bool(alias_mid) and alias_mid in node_mids


def prepared_ok() -> None:
    items = load_aliases()
    slices = load_slices()
    if len(items) != 30:
        raise SystemExit(f"expected 30 ecosystems, found {len(items)}")
    if len(slices) != 128:
        raise SystemExit(f"expected 128 slices, found {len(slices)}")
    if slices[0]["slice_start"] != "2016-11-14" or slices[-1]["slice_end_exclusive"] != "2026-08-15":
        raise SystemExit("slice span is not 2016-11-14 through 2026-08-15")
    names = [row["name"] for row in items]
    if len(set(names)) != 30:
        raise SystemExit("ecosystem names are not unique")
    for row in items:
        if not row["titles"] or not row["mids"]:
            raise SystemExit(f"{row['name']} is missing a title or a mid")
        for mid in row["mids"]:
            if not mid.startswith("/"):
                raise SystemExit(f"{row['name']} mid {mid} has no path")
        if alias_allowed(row["mids"], "/m/not-this-node"):
            raise SystemExit("a foreign mid was accepted")
        for extra in row["accepted_aliases"]:
            if not alias_allowed(row["mids"], extra.get("mid") or ""):
                raise SystemExit(f"{row['name']} has an alias whose mid does not match")
    neighbors = json.loads(ALIASES.read_text()).get("neighbors") or []
    for row in neighbors:
        if not row.get("title") or not row.get("mid") or not str(row["mid"]).startswith("/"):
            raise SystemExit(f"neighbor {row.get('name')} failed the mid check")
    first = slices[0]["sql"]
    last = slices[-1]["sql"]
    titles = [title for row in items for title in row["titles"]]
    titles += [row["title"] for row in neighbors]
    for title in titles:
        token = "'" + title.replace("\\", "\\\\").replace("'", "\\'") + "'"
        if token not in first or token not in last:
            raise SystemExit(f"{title} is missing from a slice query")
    if slices[0]["slice_start"] == slices[1]["slice_start"]:
        raise SystemExit("slice dates are not distinct")
    print("prepared 30 ecosystems 128 slices mid check holds", flush=True)


def account_row(config: dict, key: str) -> dict:
    for row in config["accounts"]:
        if row["account_key"] == key and row.get("enabled"):
            return row
    raise SystemExit(f"account {key} is not enabled")


def enabled_accounts(config: dict) -> list[dict]:
    return [row for row in config["accounts"] if row.get("enabled")]


def gcloud_value(name: str) -> str:
    proc = subprocess.run(["gcloud", "config", "get-value", name], text=True, capture_output=True)
    return (proc.stdout or "").strip()


def billing_disabled(project: str) -> None:
    proc = subprocess.run(
        ["gcloud", "billing", "projects", "describe", project, "--format=json"],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout)[-1500:])
    payload = json.loads(proc.stdout or "{}")
    if payload.get("billingEnabled") is not False:
        raise SystemExit(f"{project} has billing enabled. Refusing.")


def require_sandbox(row: dict) -> None:
    config = load_config()
    if row["project"] in config["forbidden_projects"]:
        raise SystemExit(f"refusing project {row['project']}")
    if gcloud_value("account") != row["gcloud_account"]:
        raise SystemExit(
            f"active account is {gcloud_value('account')}, expected {row['gcloud_account']}"
        )
    if gcloud_value("project") != row["project"]:
        raise SystemExit(f"active project is {gcloud_value('project')}, expected {row['project']}")
    billing_disabled(row["project"])


def ledger_billed(path: Path, project: str) -> int:
    if not path.exists():
        return 0
    total = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("project_id") != project:
            continue
        if row.get("executed"):
            total += int(row.get("bytes_billed") or 0)
    return total


def append_ledger(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def bq(args: list[str], label: str, deadline: float) -> subprocess.CompletedProcess[str]:
    proc = subprocess.Popen(["bq", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    started = deadline - SLICE_TIMEOUT
    last = 0.0
    while True:
        try:
            out, err = proc.communicate(timeout=20)
            return subprocess.CompletedProcess(["bq", *args], proc.returncode or 0, out, err)
        except subprocess.TimeoutExpired:
            now = time.time()
            if now - last >= 60:
                print(f"heartbeat {label} elapsed {int(now - started)}", flush=True)
                last = now
            if now >= deadline:
                proc.kill()
                proc.communicate()
                raise TimeoutError(label)


def dry_run_bytes(project: str, query: str, label: str) -> int:
    proc = bq(
        ["query", f"--project_id={project}", "--use_legacy_sql=false", "--format=json", "--dry_run", query],
        label,
        time.time() + SLICE_TIMEOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-2000:])
    return int(json.loads(proc.stdout)["statistics"]["query"]["totalBytesProcessed"])


def job_info(project: str, job_id: str, label: str, deadline: float) -> dict:
    proc = bq(["show", "-j", "--format=json", f"--project_id={project}", job_id], label, deadline)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-2000:])
    return json.loads(proc.stdout)


def decode_row(raw: dict) -> dict:
    cells = raw["f"]
    packed = cells[3]["v"] or []
    entities = []
    for item in packed:
        fields = item["v"]["f"]
        entities.append({"mid": fields[1]["v"], "wiki": fields[0]["v"]})
    return {"day": cells[0]["v"], "entities": entities, "score": cells[2]["v"], "url_hash": cells[1]["v"]}


def fetch_results(project: str, job_id: str, dest: Path, label: str, deadline: float) -> int:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    partial = dest.with_name(dest.name + ".partial")
    if partial.exists():
        partial.unlink()
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries/{job_id}"
    page = None
    count = 0
    try:
        with gzip.open(partial, "wt", encoding="utf-8") as handle:
            while True:
                if time.time() >= deadline:
                    raise TimeoutError(label)
                params = {"maxResults": "2000", "location": "US"}
                if page:
                    params["pageToken"] = page
                request = urllib.request.Request(
                    url + "?" + urllib.parse.urlencode(params),
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    payload = json.loads(response.read().decode())
                if not payload.get("jobComplete", True):
                    time.sleep(15)
                    continue
                for raw in payload.get("rows") or []:
                    handle.write(json.dumps(decode_row(raw), separators=(",", ":")) + "\n")
                    count += 1
                page = payload.get("pageToken")
                if not page:
                    break
    except Exception:
        if partial.exists():
            partial.unlink()
        raise
    partial.replace(dest)
    return count


def execute_slice(row: dict, spec: dict, who: dict) -> dict:
    project = who["project"]
    ledger = ROOT / who["ledger"]
    cap = int(who["cap_bytes"])
    query_cap = int(load_config()["query_cap_bytes"])
    dest = OUT / who["account_key"] / f"{spec['slice_start']}.jsonl.gz"
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip {spec['slice_start']}", flush=True)
        return {"slice_start": spec["slice_start"], "skipped": True}
    if shutil.disk_usage(ROOT).free < DISK_PAUSE:
        raise SystemExit(f"free disk under {DISK_PAUSE}")
    estimated = dry_run_bytes(project, spec["sql"], spec["slice_start"] + " dry_run")
    used = ledger_billed(ledger, project)
    append_ledger(
        ledger,
        {
            "purpose": f"wave2_gdelt_{spec['slice_start']}",
            "executed": False,
            "project_id": project,
            "account": who["gcloud_account"],
            "dry_run_bytes": estimated,
            "slice_start": spec["slice_start"],
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    if estimated > query_cap:
        raise SystemExit(f"{spec['slice_start']} dry run {estimated} exceeds 10 GB")
    if used + estimated > cap:
        raise SystemExit(f"{spec['slice_start']} would pass 960 GB on {project}")
    job_id = f"wave2_{spec['slice_start'].replace('-', '')}_{int(time.time())}"
    deadline = time.time() + SLICE_TIMEOUT
    proc = bq(
        [
            "--nosynchronous_mode",
            "query",
            f"--project_id={project}",
            "--use_legacy_sql=false",
            "--format=json",
            f"--job_id={job_id}",
            spec["sql"],
        ],
        spec["slice_start"] + " submit",
        deadline,
    )
    if proc.returncode != 0:
        text = (proc.stderr or "") + (proc.stdout or "")
        if "Already Exists" not in text and "already exists" not in text:
            raise RuntimeError(text[-2000:])
    while True:
        info = job_info(project, job_id, spec["slice_start"] + " wait", deadline)
        state = info["status"]["state"]
        if state == "DONE":
            error = info["status"].get("errorResult")
            if error:
                raise RuntimeError(json.dumps(error))
            break
        if time.time() >= deadline:
            raise TimeoutError(spec["slice_start"])
        time.sleep(20)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = fetch_results(project, job_id, dest, spec["slice_start"] + " fetch", deadline)
    stats = info["statistics"]["query"]
    done = {
        "purpose": f"wave2_gdelt_{spec['slice_start']}",
        "executed": True,
        "project_id": project,
        "account": who["gcloud_account"],
        "job_id": job_id,
        "bytes_processed": int(stats.get("totalBytesProcessed") or 0),
        "bytes_billed": int(stats.get("totalBytesBilled") or 0),
        "result_rows": rows,
        "slice_start": spec["slice_start"],
        "slice_end_exclusive": spec["slice_end_exclusive"],
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    append_ledger(ledger, done)
    print(f"stored {spec['slice_start']} billed {done['bytes_billed']}", flush=True)
    return done


def stored_dry(starts: list[str]) -> dict[str, int]:
    payload = json.loads(COST.read_text())
    found = {row["slice_start"]: int(row["dry_run_bytes"]) for row in payload["slices"] if row.get("usable")}
    missing = [day for day in starts if day not in found]
    if missing:
        raise SystemExit(f"stored dry-run missing for {missing}")
    return {day: found[day] for day in starts}


def cost_check() -> None:
    config = load_config()
    accounts = enabled_accounts(config)
    if len(accounts) != 1:
        raise SystemExit("the cost check runs on the one enabled account")
    who = accounts[0]
    require_sandbox(who)
    by_start = {row["slice_start"]: row for row in load_slices()}
    starts = config["cost_check_slices"]
    dry = stored_dry(starts)
    billed = []
    for day in starts:
        result = execute_slice(by_start[day], by_start[day], who)
        billed.append(int(result["bytes_billed"]))
    numerator = sum(billed)
    denominator = sum(dry.values())
    ratio = numerator / denominator
    payload = {
        "slices": starts,
        "stored_dry_run_bytes": dry,
        "bytes_billed": billed,
        "ratio": ratio,
        "ratio_above": config["ratio_above"],
        "two_accounts_required": ratio > config["ratio_above"],
        "account": who["gcloud_account"],
        "project": who["project"],
    }
    CHECK.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"cost check ratio {ratio:.4f}", flush=True)


def account_with_room(accounts: list[dict], estimated: int) -> dict:
    for who in accounts:
        used = ledger_billed(ROOT / who["ledger"], who["project"])
        if used + estimated <= int(who["cap_bytes"]):
            return who
    raise SystemExit("both accounts are at the 960 GB cap")


def execute_full() -> None:
    if not CHECK.exists():
        raise SystemExit("cost check has not been run")
    checked = json.loads(CHECK.read_text())
    config = load_config()
    accounts = enabled_accounts(config)
    if checked["two_accounts_required"] and len(accounts) < 2:
        raise SystemExit("ratio is above 1.5. Add the second account before the full pass.")
    if not checked["two_accounts_required"]:
        accounts = accounts[:1]
    for who in accounts:
        require_sandbox(who)
    done = {path.name[:10] for path in OUT.glob("*/*.jsonl.gz") if path.stat().st_size > 0}
    for spec in load_slices():
        if spec["slice_start"] in done:
            continue
        estimated = dry_run_bytes(accounts[0]["project"], spec["sql"], spec["slice_start"] + " dry_run")
        who = account_with_room(accounts, estimated)
        execute_slice(spec, spec, who)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--confirm-wave2", action="store_true")
    parser.add_argument("--cost-check", action="store_true")
    parser.add_argument("--execute-full", action="store_true")
    args = parser.parse_args()
    prepared_ok()
    if args.self_check or not args.confirm_wave2:
        print("Wave 2 GDELT is prepared and not started.", flush=True)
        return
    if args.cost_check:
        cost_check()
        return
    if args.execute_full:
        execute_full()
        return
    raise SystemExit("pass --cost-check or --execute-full")


if __name__ == "__main__":
    main()
