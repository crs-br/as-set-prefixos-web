# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.1.1] - 2026-06-25
### Changed
- `docs/DOCUMENTACAO.md`: exemplos de ASN e blocos reais substituídos por
  faixas reservadas para documentação (`192.0.2.0/24`, `198.51.100.0/24` —
  RFC 5737; `2001:db8::/32` — RFC 3849; `AS64500`/`AS-EXEMPLO` — RFC 5398),
  sem referência a clientes ou ASNs reais.

## [1.1.0] - 2026-06-25
### Added
- `docs/DOCUMENTACAO.md`: referência completa da interface web (cada campo,
  botão e aba) e do formato/propósito de cada arquivo gerado (CSV, TXT,
  prefix-list Juniper, ACL Huawei).

## [1.0.0] - 2026-06-25
### Added
- Scripts de inicialização multiplataforma (`start_windows.bat`, `start_mac_linux.sh`)
  que criam o ambiente virtual, instalam as dependências e abrem o navegador
  automaticamente.
- `.gitignore` e `LICENSE` (MIT) para publicação do projeto no GitHub.

### Changed
- `app.py` passa a abrir o navegador automaticamente e desliga o modo
  debug/reloader do Flask (mais adequado para distribuição a usuários finais).

## [0.9.1] - 2026-06-25
### Fixed
- Falso-positivo na detecção de conflito de origem (MOAS): um bloco menos
  específico de outra organização (ex: um `/19` que apenas continha o `/22`
  verificado) estava sendo confundido com conflito real. A consulta por
  prefixo agora usa a flag `-x` (match exato) e também filtra no cliente
  comparando redes via `ipaddress`, não strings.

## [0.9.0] - 2026-06-25
### Added
- Detecção real de conflito de origem (MOAS) no backend: para cada prefixo
  único encontrado no IRR, consulta o(s) servidor(es) pelo prefixo exato
  (sem filtro de origem), capturando ASNs em conflito mesmo fora do as-set
  analisado.
- Checkbox "verificar conflitos de origem (MOAS) no IRR" na interface.

### Changed
- Aba "conflitos" passa a usar os dados computados pelo backend em vez de
  uma lógica client-side com visibilidade limitada (a versão anterior só
  detectava conflitos entre ASNs que já eram membros do as-set analisado).

## [0.8.0] - 2026-06-25
### Added
- Aba "conflitos" na interface (versão inicial, client-side) para sinalizar
  prefixos com múltiplos registros de origem no IRR.
- Download de CSV de conflitos.

## [0.7.1] - 2026-06-25
### Changed
- Nome padrão da prefix-list Juniper v4 alterado de `CLIENTES` para
  `CLIENTES-V4` (simetria com `CLIENTES-V6`).
- Extensão dos arquivos de prefix-list Juniper alterada de `.set` para `.txt`.

## [0.7.0] - 2026-06-25
### Added
- Exportação de ACL Huawei (`acl name ... advance` / `acl ipv6 name ...
  advance`) a partir da lista sumarizada, com conversão automática de
  prefixo CIDR para máscara wildcard em IPv4.

## [0.6.0] - 2026-06-25
### Added
- Exportação de prefix-list Juniper (`set policy-options prefix-list ...`)
  para IPv4 e IPv6, com nomes de lista configuráveis na interface.

## [0.5.0] - 2026-06-25
### Added
- Interface web (Flask + HTML/JS) com streaming de progresso em tempo real
  (SSE), abas de resultado (resumo/bruto) e downloads de CSV/TXT direto do
  navegador.
- `collect_as_set_lib.py`: biblioteca compartilhada com a lógica de coleta,
  reaproveitável pelo backend web.

## [0.4.0] - 2026-06-25
### Added
- Sumarização/agregação de prefixos por ASN+família: remove prefixos do IRR
  cobertos por um bloco já alocado no registro.br (ou por outro bloco maior
  do próprio IRR), evitando prefix-lists redundantes.
- `prefixos_resumo.csv` como saída adicional; `prefixos_v4.txt`/
  `prefixos_v6.txt` passam a refletir a lista sumarizada.

## [0.3.0] - 2026-06-25
### Added
- Coleta de objetos `route:`/`route6:` do IRR via lookup inverso por origem
  (`-i origin AS<asn>`), capturando blocos alugados/anunciados via upstream
  que não aparecem como alocação direta no registro.br.
- Colunas `fonte` (alocação/irr) e `fonte_detalhe` (registro de origem:
  RADB, ARIN, RIPE etc.) no CSV.

## [0.2.0] - 2026-06-25
### Fixed
- Classificação incorreta de família IPv4/IPv6: o whois.registro.br não usa
  de forma confiável um campo `inet6num:` separado — blocos IPv6 também
  podem aparecer sob `inetnum:`. A família passou a ser determinada pelo
  conteúdo do prefixo, não pelo nome do campo.

## [0.1.0] - 2026-06-25
### Added
- Script inicial (`collect_as_set_prefixes.py`): expande um as-set no RADB
  (`!i<as-set>,1`) recursivamente em ASNs membros, e consulta o
  whois.registro.br para coletar os blocos IPv4/IPv6 alocados a cada ASN.
  Saída em CSV + listas planas `_v4.txt`/`_v6.txt`.
