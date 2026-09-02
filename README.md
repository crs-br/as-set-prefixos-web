# Registry Console — prefixos por as-set e ASN

Coleta prefixos IPv4/IPv6 via **AS-SET** ou por **ASN específico**, cruzando alocação registrada no `whois.registro.br` com objetos `route:`/`route6:` do IRR. O sistema executa as consultas com aceleração **multithread**, sumariza os blocos sem redundâncias, detecta conflitos de origem (MOAS) capturando e-mails de contato (`changed:`/`notify:`) para acionamento de NOC, extrai registros brutos RPSL e exporta prefix-lists Juniper e ACLs Huawei.

Requer conexão com a internet com saída liberada na porta 43/tcp (protocolo whois) — é assim que o programa fala com `whois.radb.net`, `whois.registro.br` e demais servidores IRR.

---

## Funcionalidades

* **Consulta por AS-SET:** Expande recursivamente os membros no IRR e coleta os prefixos de todos os ASNs associados AS-65001].
* **Consulta por ASN específico:** Permite auditar diretamente um ASN avulso (ex: `AS65001` ou `65001`).
* **Multithreading:** Coleta paralela de dados de múltiplos ASNs e verificação concorrente de conflitos MOAS em múltiplos servidores IRR.
* **Detecção de Conflitos (MOAS) com E-mails de NOC:** Identifica anúncios concorrentes no IRR e extrai endereços de e-mail dos campos `changed:` e `notify:` com links `mailto:` diretos.
* **Visualização e Download RPSL (Raw):** Extração completa dos objetos `aut-num` e `route:`/`route6:` direto da base IRR em formato de texto (`irr_records.txt`).
* **Sumarização Inteligente:** Elimina sub-redes redundantes que já estejam contidas em blocos maiores[cite: 3, 5].
* **Exportações:** Arquivos planos (`v4.txt`, `v6.txt`), prefix-list Juniper (`.txt`), ACL Huawei (`.txt`) e relatórios em CSV (Resumo, Bruto e Conflitos com e-mail).

## Instalação via git (alternativa ao zip)

```bash
git clone https://github.com/<seu-usuario>/as-set-prefixos-web.git
cd as-set-prefixos-web
```

Depois siga a seção "Como rodar" abaixo normalmente.

## Como rodar

### Windows
1. Extraia este zip em qualquer pasta.
2. Dê duplo clique em **`start_windows.bat`**.
3. Na primeira vez, uma janela preta (terminal) vai aparecer, instalar o
   necessário e abrir o navegador automaticamente em `http://127.0.0.1:5000`.
4. Para parar, feche a janela do terminal (ou `CTRL+C`).

> Se o Windows perguntar algo sobre "Windows protegeu seu PC" (SmartScreen),
> clique em "Mais informações" → "Executar assim mesmo" — é só um aviso
> padrão para scripts `.bat` baixados da internet.

### macOS
1. Extraia o zip.
2. Abra o **Terminal** (Spotlight → digite "Terminal").
3. Arraste a pasta extraída para a janela do Terminal para preencher o
   caminho automaticamente, ou digite `cd ` e o caminho da pasta.
4. Rode:
   ```bash
   bash start_mac_linux.sh
   ```
5. O navegador deve abrir automaticamente em `http://127.0.0.1:5000`.
6. Para parar, volte ao Terminal e pressione `CTRL+C`.

> Se aparecer erro de "externally-managed-environment" ao instalar pacotes
> Python fora deste script, é o motivo de usarmos um ambiente virtual
> (`.venv`) — o script já cuida disso automaticamente.

### Linux
1. Extraia o zip.
2. Abra um terminal na pasta extraída.
3. Rode:
   ```bash
   bash start_mac_linux.sh
   ```
4. Se faltar o módulo de ambiente virtual, instale com o gerenciador de
   pacotes da sua distribuição, por exemplo:
   ```bash
   sudo apt install python3 python3-venv   # Debian/Ubuntu
   sudo dnf install python3                # Fedora
   ```
5. O navegador deve abrir automaticamente em `http://127.0.0.1:5000`.

---

## Uso manual (qualquer sistema, sem os scripts)

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
python3 app.py
```

Depois acesse `http://127.0.0.1:5000` no navegador.

---

## Estrutura dos arquivos

```
.
├── app.py                  # backend Flask com rotas SSE (/api/collect e /api/collect_asn)
├── collect_as_set_lib.py   # motor multithread de consultas Whois/IRR, agregação e extração RPSL
├── requirements.txt        # dependências Python (só Flask)
├── static/
│   └── index.html          # interface web (modos AS-SET/ASN, terminal, tabelas, visualizador RPSL)
├── docs/
│   └── DOCUMENTACAO.md     # documentação técnica de campos, regras e arquivos gerados
├── CHANGELOG.md            # histórico detalhado de versões e alterações
├── start_windows.bat
├── start_mac_linux.sh
├── LICENSE
└── README.md
```

## Rodando de novo depois da primeira vez

Não precisa repetir a instalação — é só rodar o script de novo
(`start_windows.bat` ou `bash start_mac_linux.sh`). Ele detecta que o `.venv`
já existe e só reinstala dependências se necessário.

## Problemas comuns

- **`ModuleNotFoundError: No module named 'flask'`** — você rodou
  `python app.py` direto, sem usar o script de inicialização (que cria o
  ambiente virtual e instala o Flask antes). Use o script, ou rode
  manualmente os passos da seção "Uso manual" acima.

- **Página em branco / "Not Found" ao abrir `http://127.0.0.1:5000`** —
  confirme que a pasta `static/` (com `index.html` dentro) está no mesmo
  lugar que `app.py`. Não mova ou renomeie esses arquivos individualmente.

- **A coleta trava ou demora muito** — normal para as-sets com muitos ASNs:
  o programa espera um intervalo (`delay`) entre consultas para não ser
  bloqueado pelos servidores. Aumente o delay nas opções avançadas se notar
  erros de conexão recusada.

- **Porta 5000 já em uso** — outro programa (ou outra instância deste app já
  aberta) está usando a porta. Feche a outra instância, ou edite a constante
  `PORT` no topo do `app.py` para outro valor (ex: 5050) e acesse
  `http://127.0.0.1:5050`.

## Licença

Distribuído sob a licença MIT — veja o arquivo `LICENSE`. Use, modifique e
redistribua livremente, mantendo o aviso de copyright original.

