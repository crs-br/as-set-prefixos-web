"""
collect_as_set_lib.py - Versão de Alta Performance Multithreaded

Funcionalidades:
  1) Expansão de AS-SET e consulta direta por ASN único.
  2) Modo de listagem rápida: expande apenas os ASNs do AS-SET sem coletar prefixos.
  3) Coleta concorrente (multithreading) de blocos alocados no Registro.br
     e rotas nos servidores IRR.
  4) Sumarização inteligente e agregação de prefixos.
  5) Checagem multithread de conflitos de origem (MOAS).
  6) Extração do campo de e-mail de contato (changed:/notify:) para contato de NOC.
  7) Extração de objetos brutos RPSL completos (aut-num, route/route6).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import re
import socket
import threading
import time

ASN_RE = re.compile(r'\bAS(\d+)\b')
CONTROL_LINE_RE = re.compile(r'^[A-Z]\d*$')
EMAIL_RE = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')


def query_irrd_direct(server: str, query: str, port: int = 43, timeout: float = 7.0) -> str:
    """Socket rápido pontual para servidores IRR e Whois."""
    try:
        with socket.create_connection((server, port), timeout=timeout) as sock:
            sock.sendall((query.strip() + "\r\n").encode("utf-8"))
            sock.settimeout(timeout)
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks).decode("utf-8", errors="replace")
    except OSError:
        return ""


def expand_as_set(as_set: str, server: str = "whois.radb.net") -> set:
    """Expande o as-set no IRR e extrai os ASNs membros."""
    raw = query_irrd_direct(server, f"!i{as_set},1")
    return set(int(m.group(1)) for m in ASN_RE.finditer(raw))


def query_registrobr(asn: int, server: str = "whois.registro.br") -> list:
    """Consulta os blocos alocados no Registro.br para um ASN."""
    raw = query_irrd_direct(server, str(asn))
    results = []
    for line in raw.splitlines():
        line = line.strip()
        if line.lower().startswith("inetnum:") or line.lower().startswith("inet6num:"):
            prefix = line.split(":", 1)[1].strip().split("#", 1)[0].strip()
            if not prefix:
                continue
            try:
                net = ipaddress.ip_network(prefix, strict=False)
                fam = "v6" if net.version == 6 else "v4"
            except ValueError:
                fam = "v6" if ":" in prefix else "v4"
            results.append({"familia": fam, "prefixo": prefix})
    return results


def parse_rpsl_objects(raw: str) -> list:
    """Faz o parse de blocos RPSL (route/route6), capturando também emails de contato em changed: e notify:."""
    objects = []
    current = {}

    def flush():
        if current.get("prefixo") and current.get("familia"):
            objects.append(dict(current))

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                flush()
                current.clear()
            continue
        if CONTROL_LINE_RE.match(line):
            continue
        m = re.match(r'^(route6?|origin|descr|source|mnt-by|changed|notify):\s*(.*)$', line, re.IGNORECASE)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2).strip()
        if key in ("route", "route6"):
            if current.get("prefixo"):
                flush()
                current.clear()
            current["familia"] = "v6" if key == "route6" else "v4"
            current["prefixo"] = value
        elif key == "origin":
            current["origin"] = value.upper()
        elif key == "descr":
            current["descr"] = (current.get("descr", "") + " | " + value).strip(" |")
        elif key == "source":
            current["source"] = value
        elif key == "mnt-by":
            current["mnt_by"] = (current.get("mnt_by", "") + " | " + value).strip(" |")
        elif key in ("changed", "notify"):
            emails = EMAIL_RE.findall(value)
            if emails:
                existing = current.get("contact_email", "")
                all_emails = set(existing.split(", ")) if existing else set()
                all_emails.update(emails)
                current["contact_email"] = ", ".join(sorted(all_emails))

    if current:
        flush()
    return objects


def query_irr_routes_by_origin(asn: int, server: str) -> list:
    """Busca rotas registradas no IRR por AS de origem."""
    raw = query_irrd_direct(server, f"-i origin AS{asn}")
    objs = parse_rpsl_objects(raw)
    return [
        {
            "familia": o["familia"],
            "prefixo": o["prefixo"],
            "fonte_detalhe": o.get("source", server),
            "descr": o.get("descr", ""),
            "contact_email": o.get("contact_email", ""),
        }
        for o in objs
    ]


def query_irr_raw_records_by_origin(asn: int, server: str) -> str:
    """Obtém objetos textuais RPSL brutos (aut-num e route/route6)."""
    raw_autnum = query_irrd_direct(server, f"AS{asn}")
    raw_routes = query_irrd_direct(server, f"-i origin AS{asn}")

    parts = [f"### [IRR: {server}] OBJETO AUT-NUM AS{asn} ###\n{raw_autnum.strip()}"]
    if raw_routes.strip():
        parts.append(f"### [IRR: {server}] OBJETOS ROUTE/ROUTE6 COM ORIGIN AS{asn} ###\n{raw_routes.strip()}")
    return "\n\n".join(parts)


def _same_network(a: str, b: str) -> bool:
    try:
        return ipaddress.ip_network(a, strict=False) == ipaddress.ip_network(b, strict=False)
    except ValueError:
        return a == b


def query_irr_objects_by_prefix(prefix: str, server: str) -> list:
    """Consulta objetos exatos por prefixo para apurar múltiplos ASNs de origem (MOAS)."""
    raw = query_irrd_direct(server, f"-x {prefix}")
    objs = parse_rpsl_objects(raw)
    return [o for o in objs if "prefixo" in o and _same_network(o["prefixo"], prefix)]


def sort_key_net(net) -> tuple:
    return (net.version, net.network_address.packed, net.prefixlen)


def sort_key_prefix(prefix: str):
    try:
        return sort_key_net(ipaddress.ip_network(prefix, strict=False))
    except ValueError:
        return (9, b"", 0)


def aggregate_prefixes(items: list) -> list:
    """Sumarização: remove sub-redes contidas em blocos maiores da mesma família."""
    parsed = []
    for it in items:
        try:
            net = ipaddress.ip_network(it["prefixo"], strict=False)
        except ValueError:
            continue
        parsed.append((net, it["fonte"]))

    parsed.sort(key=lambda x: (x[0].prefixlen, 0 if x[1] == "alocacao" else 1))

    kept = []
    for net, fonte in parsed:
        covered = any(net == kn or net.subnet_of(kn) for kn, _ in kept)
        if not covered:
            kept.append((net, fonte))

    kept.sort(key=lambda x: sort_key_net(x[0]))
    return [{"prefixo": str(net), "fonte": fonte} for net, fonte in kept]


def _fetch_single_asn_data(asn: int, irr_servers: list, skip_registrobr: bool,
                           skip_irr: bool, fetch_raw_irr: bool):
    """Executa a coleta completa de um único ASN isolado."""
    asn_rows = []
    raw_texts = []

    if not skip_registrobr:
        for item in query_registrobr(asn):
            asn_rows.append({
                "asn": f"AS{asn}",
                "familia": item["familia"],
                "prefixo": item["prefixo"],
                "fonte": "alocacao",
                "fonte_detalhe": "registro.br",
                "descr": ""
            })

    if not skip_irr:
        seen_irr = set()
        for server in irr_servers:
            for item in query_irr_routes_by_origin(asn, server):
                key = (item["familia"], item["prefixo"], item["fonte_detalhe"])
                if key in seen_irr:
                    continue
                seen_irr.add(key)
                asn_rows.append({
                    "asn": f"AS{asn}",
                    "familia": item["familia"],
                    "prefixo": item["prefixo"],
                    "fonte": "irr",
                    "fonte_detalhe": item["fonte_detalhe"],
                    "descr": item["descr"]
                })

            if fetch_raw_irr:
                rec_text = query_irr_raw_records_by_origin(asn, server)
                if rec_text.strip():
                    raw_texts.append(rec_text)

    return asn, asn_rows, raw_texts


def _check_single_prefix_conflict(prefix_tuple, irr_servers):
    """Consulta um prefixo em múltiplos IRRs para detectar MOAS, incluindo emails de contato."""
    familia, prefix = prefix_tuple
    origins_seen = {}
    for server in irr_servers:
        objs = query_irr_objects_by_prefix(prefix, server)
        for o in objs:
            origin = o.get("origin", "").strip()
            if not origin:
                continue
            contact = o.get("contact_email", "")
            key = (origin, o.get("source", server), contact)
            if key not in origins_seen:
                origins_seen[key] = {
                    "asn": origin,
                    "fonte_detalhe": o.get("source", server),
                    "descr": o.get("descr", ""),
                    "email": contact or "-",
                }

    distinct_asns = sorted({rec["asn"] for rec in origins_seen.values()})
    if len(distinct_asns) >= 2:
        return {
            "familia": familia,
            "prefixo": prefix,
            "asns": distinct_asns,
            "records": list(origins_seen.values()),
        }
    return None


def _process_asn_list_multithreaded(asns_sorted: list, irr_servers: list,
                                    skip_registrobr: bool, skip_irr: bool,
                                    check_conflicts: bool, fetch_raw_irr: bool = False):
    """Pipeline multithread para consulta dos ASNs e verificação de conflitos."""
    rows = []
    raw_irr_texts = []
    total_asns = len(asns_sorted)

    yield {"type": "log", "message": f"Coletando dados de {total_asns} ASN(s) via multithreading..."}

    asn_workers = min(10, max(2, total_asns))
    completed_asns = 0

    with ThreadPoolExecutor(max_workers=asn_workers) as executor:
        futures = {
            executor.submit(_fetch_single_asn_data, asn, irr_servers, skip_registrobr, skip_irr, fetch_raw_irr): asn
            for asn in asns_sorted
        }

        for fut in as_completed(futures):
            completed_asns += 1
            asn, asn_rows, raw_texts = fut.result()
            rows.extend(asn_rows)
            raw_irr_texts.extend(raw_texts)

            yield {
                "type": "progress",
                "current": completed_asns,
                "total": total_asns,
                "message": f"[{completed_asns}/{total_asns}] AS{asn} processado ({len(asn_rows)} prefixos)"
            }

    grouped = {}
    for r in rows:
        grouped.setdefault((r["asn"], r["familia"]), []).append({"prefixo": r["prefixo"], "fonte": r["fonte"]})

    summary_rows = []
    for (asn, familia), items in grouped.items():
        for item in aggregate_prefixes(items):
            summary_rows.append({
                "asn": asn,
                "familia": familia,
                "prefixo": item["prefixo"],
                "fonte": item["fonte"]
            })

    summary_rows.sort(key=lambda r: (r["asn"], r["familia"], sort_key_prefix(r["prefixo"])))

    conflicts = []
    if not skip_irr and check_conflicts:
        unique_prefixes = sorted({(r["familia"], r["prefixo"]) for r in rows if r["fonte"] == "irr"})
        total_p = len(unique_prefixes)
        if total_p > 0:
            yield {"type": "log", "message": f"Analisando conflitos de origem (MOAS) em {total_p} prefixo(s)..."}

            conflict_workers = min(12, max(2, total_p))
            completed_p = 0

            with ThreadPoolExecutor(max_workers=conflict_workers) as executor:
                conflict_futures = {
                    executor.submit(_check_single_prefix_conflict, p, irr_servers): p
                    for p in unique_prefixes
                }

                for fut in as_completed(conflict_futures):
                    completed_p += 1
                    res = fut.result()
                    if res:
                        conflicts.append(res)
                    if completed_p % 10 == 0 or completed_p == total_p:
                        yield {
                            "type": "progress",
                            "current": completed_p,
                            "total": total_p,
                            "message": f"  [conflitos {completed_p}/{total_p}] prefixos analisados..."
                        }

    yield {
        "type": "done",
        "asns": [f"AS{a}" for a in asns_sorted],
        "raw_rows": rows,
        "summary_rows": summary_rows,
        "conflicts": conflicts,
        "raw_irr_text": "\n\n".join(raw_irr_texts).strip()
    }


def collect_stream(as_set: str, delay: float = 0.0, radb_server: str = "whois.radb.net",
                   irr_servers=("whois.radb.net",), skip_registrobr: bool = False,
                   skip_irr: bool = False, check_conflicts: bool = True,
                   asns_only: bool = False):
    """Executa a coleta do as-set com aceleração multithread ou apenas lista os ASNs membros."""
    yield {"type": "log", "message": f"Expandindo as-set {as_set} em {radb_server} ..."}
    try:
        asns = expand_as_set(as_set, server=radb_server)
    except OSError as e:
        yield {"type": "error", "message": f"Erro ao consultar {radb_server}: {e}"}
        return

    if not asns:
        yield {"type": "error", "message": f"Nenhum ASN encontrado para {as_set}. Confira o nome do as-set."}
        return

    asns_sorted = sorted(asns)
    asn_list_str = [f"AS{a}" for a in asns_sorted]
    yield {"type": "log", "message": f"{len(asns_sorted)} ASN(s) encontrado(s): " +
                                      ", ".join(asn_list_str)}

    # Se a opção de apenas listar ASNs estiver ativada, encerra aqui sem consultar Whois/IRR
    if asns_only:
        yield {
            "type": "done",
            "asns_only": True,
            "asns": asn_list_str,
            "raw_rows": [],
            "summary_rows": [],
            "conflicts": [],
            "raw_irr_text": ""
        }
        return

    yield from _process_asn_list_multithreaded(
        asns_sorted,
        list(irr_servers),
        skip_registrobr,
        skip_irr,
        check_conflicts,
        fetch_raw_irr=False
    )


def collect_asn_stream(asn_input: str, delay: float = 0.0, irr_servers=("whois.radb.net",),
                       skip_registrobr: bool = False, skip_irr: bool = False,
                       check_conflicts: bool = True, fetch_raw_irr: bool = True):
    """Executa a consulta de um ASN específico com aceleração multithread."""
    match = re.search(r'\d+', asn_input)
    if not match:
        yield {"type": "error", "message": f"ASN inválido: '{asn_input}'."}
        return

    asn_int = int(match.group(0))
    yield {"type": "log", "message": f"Iniciando consulta para ASN: AS{asn_int} ..."}

    yield from _process_asn_list_multithreaded(
        [asn_int],
        list(irr_servers),
        skip_registrobr,
        skip_irr,
        check_conflicts,
        fetch_raw_irr=fetch_raw_irr
    )