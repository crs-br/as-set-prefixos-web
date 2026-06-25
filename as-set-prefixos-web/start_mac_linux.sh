#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo " Registry Console - prefixos por as-set"
echo "============================================"
echo

PYEXE=""
if command -v python3 >/dev/null 2>&1; then
    PYEXE="python3"
elif command -v python >/dev/null 2>&1; then
    PYEXE="python"
else
    echo "[ERRO] Python 3 nao foi encontrado neste computador."
    echo "macOS: instale com 'brew install python3' ou baixe em https://www.python.org/downloads/"
    echo "Linux: instale com o gerenciador de pacotes da sua distro, ex: 'sudo apt install python3 python3-venv'"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual (.venv) ..."
    "$PYEXE" -m venv .venv || {
        echo "[ERRO] Falha ao criar o ambiente virtual."
        echo "No Linux, pode ser necessario instalar o pacote python3-venv (ex: 'sudo apt install python3-venv')."
        exit 1
    }
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Instalando dependencias (Flask) ..."
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

echo
echo "Iniciando o servidor... o navegador deve abrir automaticamente."
echo "Para encerrar, volte a esta janela e pressione CTRL+C."
echo

python app.py
