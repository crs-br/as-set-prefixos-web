"""
collect_as_set_lib.py

Biblioteca com a logica de coleta usada pela interface web (app.py):

  1) Expande um as-set no RADB (protocolo IRRd, query '!i<set>,1').
  2) Para cada ASN membro, consulta whois.registro.br para os blocos
     ALOCADOS (fonte = "alocacao").
  3) Para cada ASN membro, consulta servidor(es) IRR via lookup inverso
     '-i origin AS<asn>' para os objetos route:/route6: registrados
     (fonte = "irr") -- cobre blocos alugados/anunciados via upstream.
  4) Sumariza por ASN+familia: remove prefixos do IRR que ja estao
     cobertos por um bloco maior (alocacao ou outro bloco do IRR).

Nenhuma dependencia externa (so biblioteca padrao). Roda via socket TCP
direto na porta 43 -- nao depende do binario 'whois' do sistema.
"""

import ipaddress
import re
import socket
import time

ASN_RE = re.compile(r'\bAS(\d+)\b')
CONTROL_LINE_RE = re.compile(r'^[A-Z]\d*$')


def query_irrd(server: str, query: str, port: int = 43, timeout: float = 10.0) -> str:
    """Envia uma query crua ao servidor whois (protocolo IRRd) e retorna a resposta completa."""
    with socket.create_connection((server, port), timeout=timeout) as sock:
        sock.sendall((query + "\r\n").encode("utf-8"))
        sock.settimeout(timeout)
        chunks = []
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
        except socket.timeout:
            pass
        return b"".join(chunks).decode("utf-8", errors="replace")


def expand_as_set(as_set: str, server: str = "whois.radb.net") -> set:
    """Expande recursivamente um as-set ('!i<set>,1') e retorna os ASNs membros."""
    raw = query_irrd(server, f"!i{as_set},1")
    return set(int(m.group(1)) for m in ASN_RE.finditer(raw))


def query_registrobr(asn: int, server: str = "whois.registro.br") -> list:
    """
    Retorna lista de dicts {familia, prefixo} com os blocos ALOCADOS a esse
    ASN segundo o whois.registro.br.

    O whois.registro.br nao usa de forma confiavel um campo separado
    'inet6num:' -- blocos v6 tambem podem vir sob 'inetnum:'. A familia e
    determinada pelo CONTEUDO do prefixo, nao pelo nome do campo.
    """
    raw = query_irrd(server, str(asn))
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
    """Faz parse de objetos RPSL route:/route6: separados por linha em branco."""
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
        m = re.match(r'^(route6?|origin|descr|source|mnt-by):\s*(.*)$', line, re.IGNORECASE)
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
    if current:
        flush()
    return objects


def query_irr_routes_by_origin(asn: int, server: str) -> list:
    """Retorna objetos route:/route6: com origin=AS<asn> registrados em `server`."""
    raw = query_irrd(server, f"-i origin AS{asn}")
    objs = parse_rpsl_objects(raw)
    return [
        {
            "familia": o["familia"],
            "prefixo": o["prefixo"],
            "fonte_detalhe": o.get("source", server),
            "descr": o.get("descr", ""),
        }
        for o in objs
    ]


def _same_network(a: str, b: str) -> bool:
    """Compara dois prefixos como REDES (nao como string), tolerando diferencas
    de formatacao (maiusculas/minusculas em IPv6, forma comprimida, etc)."""
    try:
        return ipaddress.ip_network(a, strict=False) == ipaddress.ip_network(b, strict=False)
    except ValueError:
        return a == b


def query_irr_objects_by_prefix(prefix: str, server: str) -> list:
    """
    Consulta um servidor IRR pelo PREFIXO exato (sem filtrar por origin) e
    retorna TODOS os objetos route:/route6: registrados para esse prefixo --
    inclusive de ASNs fora do as-set analisado. E' assim que se detecta um
    conflito real de origem (MOAS - multiple origin AS), exatamente como uma
    consulta manual 'whois -h <server> <prefixo>' faria.

    Usa a flag '-x' (match exato) para o servidor NAO devolver blocos menos
    ou mais especificos que contenham/estejam contidos no prefixo consultado
    -- sem isso, um bloco agregado (ex: um /19 de outra organizacao que so
    por coincidencia contem o /22 que estamos checando) pode aparecer junto
    e ser confundido com um conflito real.
    """
    raw = query_irrd(server, f"-x {prefix}")
    objs = parse_rpsl_objects(raw)
    # defesa extra: alguns servidores ignoram '-x' silenciosamente, entao
    # tambem filtramos no cliente, comparando REDES (nao strings), para
    # garantir que so objetos do prefixo EXATO entrem na verificacao.
    return [o for o in objs if "prefixo" in o and _same_network(o["prefixo"], prefix)]


def sort_key_net(net) -> tuple:
    return (net.version, net.network_address.packed, net.prefixlen)


def sort_key_prefix(prefix: str):
    try:
        return sort_key_net(ipaddress.ip_network(prefix, strict=False))
    except ValueError:
        return (9, b"", 0)


def aggregate_prefixes(items: list) -> list:
    """
    Sumariza prefixos da MESMA familia: remove qualquer prefixo contido
    (subnet) dentro de outro prefixo ja presente no conjunto resultante.
    Em empate de tamanho de bloco, prioriza fonte 'alocacao' sobre 'irr'.
    """
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


def collect_stream(as_set: str, delay: float = 1.5, radb_server: str = "whois.radb.net",
                    irr_servers=("whois.radb.net",), skip_registrobr: bool = False,
                    skip_irr: bool = False, check_conflicts: bool = True):
    """
    Generator que executa a coleta completa, emitindo eventos de progresso
    (dicts) a medida que avanca. Termina com um evento {"type": "done", ...}
    contendo raw_rows (bruto), summary_rows (sumarizado) e conflicts (blocos
    com mais de um ASN de origem registrado no IRR -- MOAS).
    """
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
    yield {"type": "log", "message": f"{len(asns_sorted)} ASN(s) encontrado(s): " +
                                      ", ".join(f"AS{a}" for a in asns_sorted)}

    rows = []
    total = len(asns_sorted)
    for i, asn in enumerate(asns_sorted, 1):
        yield {"type": "progress", "current": i, "total": total,
               "message": f"[{i}/{total}] AS{asn}"}

        if not skip_registrobr:
            try:
                for item in query_registrobr(asn):
                    rows.append({"asn": f"AS{asn}", "familia": item["familia"], "prefixo": item["prefixo"],
                                 "fonte": "alocacao", "fonte_detalhe": "registro.br", "descr": ""})
            except OSError as e:
                yield {"type": "log", "message": f"  [!] erro registro.br AS{asn}: {e}"}
            time.sleep(delay)

        if not skip_irr:
            seen_irr = set()
            for server in irr_servers:
                try:
                    for item in query_irr_routes_by_origin(asn, server):
                        key = (item["familia"], item["prefixo"], item["fonte_detalhe"])
                        if key in seen_irr:
                            continue
                        seen_irr.add(key)
                        rows.append({"asn": f"AS{asn}", "familia": item["familia"], "prefixo": item["prefixo"],
                                     "fonte": "irr", "fonte_detalhe": item["fonte_detalhe"], "descr": item["descr"]})
                except OSError as e:
                    yield {"type": "log", "message": f"  [!] erro IRR {server} AS{asn}: {e}"}
                time.sleep(delay)

    grouped = {}
    for r in rows:
        grouped.setdefault((r["asn"], r["familia"]), []).append({"prefixo": r["prefixo"], "fonte": r["fonte"]})

    summary_rows = []
    for (asn, familia), items in grouped.items():
        for item in aggregate_prefixes(items):
            summary_rows.append({"asn": asn, "familia": familia, "prefixo": item["prefixo"], "fonte": item["fonte"]})

    summary_rows.sort(key=lambda r: (r["asn"], r["familia"], sort_key_prefix(r["prefixo"])))

    conflicts = []
    if not skip_irr and check_conflicts:
        unique_prefixes = sorted({(r["familia"], r["prefixo"]) for r in rows if r["fonte"] == "irr"})
        if unique_prefixes:
            yield {"type": "log", "message": f"Verificando conflito de origem (MOAS) em {len(unique_prefixes)} "
                                              f"prefixo(s) unico(s) do IRR -- consulta por prefixo, sem filtro de origin ..."}
        for idx, (familia, prefix) in enumerate(unique_prefixes, 1):
            yield {"type": "progress", "current": idx, "total": len(unique_prefixes),
                   "message": f"  [conflitos {idx}/{len(unique_prefixes)}] {prefix}"}
            origins_seen = {}
            for server in irr_servers:
                try:
                    objs = query_irr_objects_by_prefix(prefix, server)
                except OSError as e:
                    yield {"type": "log", "message": f"    [!] erro ao consultar {server} para {prefix}: {e}"}
                    continue
                for o in objs:
                    origin = o.get("origin", "").strip()
                    if not origin:
                        continue
                    key = (origin, o.get("source", server))
                    if key in origins_seen:
                        continue
                    origins_seen[key] = {
                        "asn": origin, "fonte_detalhe": o.get("source", server), "descr": o.get("descr", ""),
                    }
                time.sleep(delay)

            distinct_asns = sorted({rec["asn"] for rec in origins_seen.values()})
            if len(distinct_asns) >= 2:
                conflicts.append({
                    "familia": familia, "prefixo": prefix, "asns": distinct_asns,
                    "records": list(origins_seen.values()),
                })

    yield {"type": "done", "raw_rows": rows, "summary_rows": summary_rows, "conflicts": conflicts}
