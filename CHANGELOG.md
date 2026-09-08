# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui[cite: 10].
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)[cite: 10].

## [2.0.0] - 2026-09-01
### Added
- Consulta direta por **ASN específico**: nova modalidade no formulário web que dispensa o uso de um `as-set`, aceitando formatos como `AS65001` ou `65001`.
- Rota de streaming SSE dedicada (`/api/collect_asn` em `app.py`) para processar consultas de ASN único com feedback em tempo real no terminal da interface.
- Coleta de **contatos para resolução de conflitos (MOAS)**: parser de RPSL em `collect_as_set_lib.py` atualizado com captura por expressão regular de e-mails declarados nos campos `changed:` e `notify:`.
- Links interativos `mailto:` na coluna de registros da aba "conflitos" da interface web para acionamento direto dos NOCs responsáveis.
- Coluna `email_contato` incluída na exportação de `prefixos_conflitos.csv`.
- Visualização e download de **registros IRR brutos (RPSL)**: extração integral dos objetos `aut-num` e `route:`/`route6:` direto da porta 43, nova aba "registros irr (raw)" na interface e exportação para `irr_records.txt`.
- Barra seletora de modo no topo da interface web para alternância limpa entre "por AS-SET" e "por ASN específico".

### Changed
- **Aceleração multithread geral**: tanto a varredura de membros do `as-set` quanto a checagem de conflitos de origem (MOAS) foram migradas para pools de execução concorrente (`ThreadPoolExecutor`), reduzindo o tempo de coleta e auditoria em larga escala.
- A checagem de conflitos MOAS deixa de ser estritamente sequencial com pausas artificiais e passa a consultar os prefixos em paralelo contra os servidores IRR configurados.
- Interface adaptada com alternância dinâmica dos campos de entrada (`as-set` vs `ASN específico`) e opções avançadas contextuais.

## [1.1.1] - 2026-06-25
### Changed
- `docs/DOCUMENTACAO.md`: exemplos de ASN e blocos reais substituídos por
  faixas reservadas para documentação (`192.0.2.0/24`, `198.51.100.0/24` —
  RFC 5737; `2001:db8::/32` — RFC 3849; `AS64500`/`AS-EXEMPLO` — RFC 5398),
  sem referência a clientes ou ASNs reais[cite: 10].

## [1.1.0] - 2026-06-25
### Added
- `docs/DOCUMENTACAO.md`: referência completa da interface web (cada campo,
  botão e aba) e do formato/propósito de cada arquivo gerado (CSV, TXT,
  prefix-list Juniper, ACL Huawei)[cite: 10].

## [1.0.0] - 2026-06-25
### Added
- Scripts de inicialização multiplataforma (`start_windows.bat`, `start_mac_linux.sh`)
  que criam o ambiente virtual, instalam as dependências e abrem o navegador
  automaticamente[cite: 10].
- `.gitignore` e `LICENSE` (MIT) para publicação do projeto no GitHub[cite: 10].

### Changed
- `app.py` passa a abrir o navegador automaticamente e desliga o modo
  debug/reloader do Flask (mais adequado para distribuição a usuários finais)[cite: 10].

## [0.9.1] - 2026-06-25
### Fixed
- Falso-positivo na detecção de conflito de origem (MOAS): um bloco menos
  específico de outra organização (ex: um `/19` que apenas continha o `/22`
  verificado) estava sendo confundido com conflito real[cite: 10]. A consulta por
  prefixo agora usa a flag `-x` (match exato) e também filtra no cliente
  comparando redes via `ipaddress`, não strings[cite: 10].

## [0.9.0] - 2026-06-25
### Added
- Detecção real de conflito de origem (MOAS) no backend: para cada prefixo
  único encontrado no IRR, consulta o(s) servidor(es) pelo prefixo exato
  (sem filtro de origem), capturando ASNs em conflito mesmo fora do as-set
  analisado[cite: 10].
- Checkbox "verificar conflitos de origem (MOAS) no IRR" na interface[cite: 10].

### Changed
- Aba "conflitos" passa a usar os dados computados pelo backend em vez de
  uma lógica client-side com visibilidade limitada (a versão anterior só
  detectava conflitos entre ASNs que já eram membros do as-set analisado)[cite: 10].

## [0.8.0] - 2026-06-25
### Added
- Aba "conflitos" na interface (versão inicial, client-side) para sinalizar
  prefixos com múltiplos registros de origem no IRR[cite: 10].
- Download de CSV de conflitos[cite: 10].

## [0.7.1] - 2026-06-25
### Changed
- Nome padrão da prefix-list Juniper v4 alterado de `CLIENTES` para
  `CLIENTES-V4` (simetria com `CLIENTES-V6`)[cite: 10].
- Extensão dos arquivos de prefix-list Juniper alterada de `.set` para `.txt`[cite: 10].

## [0.7.0] - 2026-06-25
### Added
- Exportação de ACL Huawei (`acl name ... advance` / `acl ipv6 name ...
  advance`) a partir da lista sumarizada, com conversão automática de
  prefixo CIDR para máscara wildcard em IPv4[cite: 10].

## [0.6.0] - 2026-06-25
### Added
- Exportação de prefix-list Juniper (`set policy-options prefix-list ...`)
  para IPv4 e IPv6, com nomes de lista configuráveis na interface[cite: 10].

## [0.5.0] - 2026-06-25
### Added
- Interface web (Flask + HTML/JS) com streaming de progresso em tempo real
  (SSE), abas de resultado (resumo/bruto) e downloads de CSV/TXT direto do
  navegador[cite: 10].
- `collect_as_set_lib.py`: biblioteca compartilhada com a lógica de coleta,
  reaproveitável pelo backend web[cite: 10].

## [0.4.0] - 2026-06-25
### Added
- Sumarização/agregação de prefixos por ASN+família: remove prefixos do IRR
  cobertos por um bloco já alocado no registro.br (ou por outro bloco maior
  do próprio IRR), evitando prefix-lists redundantes[cite: 10].
- `prefixos_resumo.csv` como saída adicional; `prefixos_v4.txt`/
  `prefixos_v6.txt` passam a refletir a lista sumarizada[cite: 10].

## [0.3.0] - 2026-06-25
### Added
- Coleta de objetos `route:`/`route6:` do IRR via lookup inverso por origem
  (`-i origin AS<asn>`), capturando blocos alugados/anunciados via upstream
  que não aparecem como alocação direta no registro.br[cite: 10].
- Colunas `fonte` (alocação/irr) e `fonte_detalhe` (registro de origem:
  RADB, ARIN, RIPE etc.) no CSV[cite: 10].

## [0.2.0] - 2026-06-25
### Fixed
- Classificação incorreta de família IPv4/IPv6: o whois.registro.br não usa
  de forma confiável um campo `inet6num:` separado — blocos IPv6 também
  podem aparecer sob `inetnum:`[cite: 10]. A família passou a ser determinada pelo
  conteúdo do prefixo, não pelo nome do campo[cite: 10].

## [0.1.0] - 2026-06-25
### Added
- Script inicial (`collect_as_set_prefixes.py`): expande um as-set no RADB
  (`!i<as-set>,1`) recursivamente em ASNs membros, e consulta o
  whois.registro.br para coletar os blocos IPv4/IPv6 alocados a cada ASN[cite: 10].
  Saída em CSV + listas planas `_v4.txt`/`_v6.txt`[cite: 10].