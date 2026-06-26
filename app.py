"""
app.py - backend Flask para a interface web de coleta de prefixos por as-set.

Como rodar:
    pip install -r requirements.txt
    python3 app.py
    -> abre automaticamente http://127.0.0.1:5000 no navegador

Requer saida de rede liberada na porta 43/tcp para os servidores IRR e para
whois.registro.br. As consultas reais acontecem aqui no backend; o frontend
so conversa com este servidor via HTTP/SSE.
"""

import json
import threading
import webbrowser

from flask import Flask, Response, request, send_from_directory

import collect_as_set_lib as lib

HOST = "127.0.0.1"
PORT = 5000

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/collect")
def api_collect():
    as_set = (request.args.get("as_set") or "").strip()

    def error_stream(message):
        yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"

    if not as_set:
        return Response(error_stream("Informe o nome de um as-set (ex: AS-28173)."),
                         mimetype="text/event-stream")

    try:
        delay = float(request.args.get("delay", 1.5))
    except ValueError:
        delay = 1.5
    delay = max(0.0, min(delay, 30.0))

    radb_server = (request.args.get("radb_server") or "whois.radb.net").strip() or "whois.radb.net"
    irr_servers_raw = (request.args.get("irr_servers") or radb_server).strip()
    irr_servers = [s.strip() for s in irr_servers_raw.split(",") if s.strip()] or [radb_server]

    skip_registrobr = (request.args.get("skip_registrobr") or "false").lower() == "true"
    skip_irr = (request.args.get("skip_irr") or "false").lower() == "true"
    check_conflicts = (request.args.get("check_conflicts") or "true").lower() == "true"

    def generate():
        try:
            for event in lib.collect_stream(
                as_set, delay=delay, radb_server=radb_server, irr_servers=irr_servers,
                skip_registrobr=skip_registrobr, skip_irr=skip_irr, check_conflicts=check_conflicts,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:  # nao deixa a stream cair em silencio
            yield f"data: {json.dumps({'type': 'error', 'message': f'Erro inesperado: {e}'})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    url = f"http://{HOST}:{PORT}"
    print(f"\n  Servidor rodando em {url}")
    print("  Abrindo o navegador automaticamente... (se nao abrir, acesse o endereco acima manualmente)")
    print("  Pressione CTRL+C nesta janela para encerrar.\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
