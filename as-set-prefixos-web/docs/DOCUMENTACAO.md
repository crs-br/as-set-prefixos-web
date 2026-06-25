# Documentação — Registry Console (prefixos por as-set)

Documentação de referência da interface web e dos arquivos gerados pela
aplicação. Para instalação e execução, veja o [`README.md`](../README.md).

## Sumário

- [Visão geral](#visão-geral)
- [Conceitos-chave](#conceitos-chave)
- [Fluxo de dados](#fluxo-de-dados)
- [Interface web](#interface-web)
  - [1. Parâmetros](#1-parâmetros)
  - [2. Log](#2-log)
  - [3. Resultados](#3-resultados)
- [Arquivos gerados](#arquivos-gerados)
  - [prefixos.csv (bruto)](#prefixoscsv-bruto)
  - [prefixos_resumo.csv](#prefixos_resumocsv)
  - [prefixos_conflitos.csv](#prefixos_conflitoscsv)
  - [prefixos_v4.txt / prefixos_v6.txt](#prefixos_v4txt--prefixos_v6txt)
  - [juniper_prefix-list_\<nome\>.txt](#juniper_prefix-list_nometxt)
  - [huawei_acl_\<nome\>.txt](#huawei_acl_nometxt)

---

## Visão geral

A aplicação parte de um **as-set** registrado no RADB (ex: `AS-28173`),
expande recursivamente todos os ASNs membros, e para cada um coleta:

1. Os blocos **alocados** a esse ASN segundo o `whois.registro.br`.
2. Os blocos **registrados no IRR** (objetos `route:`/`route6:`) com aquele
   ASN como origem — cobre blocos alugados/anunciados via upstream que não
   aparecem como alocação direta.

Em seguida, sumariza o resultado (removendo prefixos redundantes), verifica
se algum prefixo tem **mais de uma origem registrada no IRR** (conflito de
origem / MOAS), e permite exportar a lista final em formato de
configuração para equipamentos Juniper e Huawei.

## Conceitos-chave

| Termo | Significado |
|---|---|
| **as-set** | Objeto RPSL no IRR que agrupa um conjunto de ASNs (ex: todos os clientes de um provedor). |
| **ASN** | Número de Sistema Autônomo — identifica uma rede na internet. |
| **Alocação (registro.br)** | Bloco IPv4/IPv6 formalmente atribuído a um ASN pelo registro brasileiro (NIC.br). |
| **IRR** | Internet Routing Registry — bancos de dados (RADB, RIPE, ARIN, etc.) onde redes registram objetos `route:`/`route6:` autorizando um ASN a anunciar um prefixo via BGP. |
| **Sumarização** | Remoção de prefixos mais específicos que já estão contidos em um bloco maior já presente no resultado (ex: um `/22` alocado torna redundantes `/24`s do IRR contidos nele). |
| **MOAS** (*Multiple Origin AS*) | O mesmo prefixo exato registrado no IRR com ASNs de origem diferentes — pode indicar multihoming legítimo, configuração desatualizada, ou risco de sequestro de rota (hijack). |

## Fluxo de dados

```
as-set (ex: AS-28173)
        │
        ▼
  whois.radb.net  --!i<as-set>,1-->  lista de ASNs membros
        │
        ▼
  para cada ASN:
    ├─ whois.registro.br  ────────────►  blocos ALOCADOS (fonte=alocacao)
    └─ servidor(es) IRR  -i origin AS<asn>->  blocos route/route6 (fonte=irr)
        │
        ▼
  agregação por ASN+família
    (remove prefixos do IRR cobertos por um bloco maior já presente)
        │
        ▼
  verificação de conflito (MOAS)
    para cada prefixo único do IRR:
      servidor(es) IRR  -x <prefixo>-> TODOS os ASNs que registraram
      aquele prefixo EXATO (inclusive fora do as-set)
        │
        ▼
  interface web: abas resumo / bruto / conflitos
        │
        ▼
  downloads: CSV, TXT, prefix-list Juniper, ACL Huawei
```

---

## Interface web

A interface é dividida em três painéis, de cima para baixo.

### 1. Parâmetros

| Campo | Descrição | Padrão |
|---|---|---|
| **as-set** | Nome do as-set no RADB a ser expandido (obrigatório). | — |
| **delay entre consultas (s)** | Intervalo de espera entre consultas consecutivas, para evitar bloqueio/rate-limit dos servidores whois. | `1.5` |
| **pular registro.br (só IRR)** | Não consulta alocação no registro.br — coleta só objetos do IRR. | desmarcado |
| **pular IRR (só registro.br)** | Não consulta objetos route/route6 no IRR — coleta só alocação. | desmarcado |
| **verificar conflitos de origem (MOAS) no IRR** | Ativa a passada extra de verificação de conflito por prefixo exato (ver [Fluxo de dados](#fluxo-de-dados)). Desmarcar agiliza a coleta em as-sets grandes. | marcado |

**Opções avançadas** (recolhidas por padrão):

| Campo | Descrição | Padrão |
|---|---|---|
| servidor para expandir o as-set | Servidor IRRd usado na consulta `!i<as-set>,1`. | `whois.radb.net` |
| servidor(es) para route/route6 | Lista separada por vírgula de servidores IRR a consultar (permite cobrir mirrors específicos, ex: `rr.ntt.net`). | `whois.radb.net` |
| nome prefix-list (juniper v4/v6) | Nome usado na exportação `set policy-options prefix-list ...`. | `CLIENTES-V4` / `CLIENTES-V6` |
| nome acl (huawei v4/v6) | Nome usado na exportação `acl name ... advance`. | `CLIENTES-V4` / `CLIENTES-V6` |

O botão **coletar →** dispara a execução. Fica desabilitado durante a
coleta, junto com uma barra de progresso indicando o ASN/prefixo atual.

### 2. Log

Painel estilo terminal que recebe, em tempo real (via *Server-Sent Events*),
cada etapa da coleta: expansão do as-set, progresso por ASN, erros de
conexão e a mensagem final de conclusão com as contagens de cada categoria.
Não requer atualizar a página — a conexão fica aberta até o evento de
conclusão (`done`) ou erro.

### 3. Resultados

Três abas:

| Aba | Conteúdo |
|---|---|
| **resumo** | Lista sumarizada por ASN+família — a "pegada" final de rede sem prefixos redundantes. Use esta aba como base para os exports de Juniper/Huawei. |
| **bruto** | Todas as entradas encontradas, sem nenhuma supressão — útil para auditoria, conferir de onde cada prefixo veio (`fonte_detalhe`) e sua descrição RPSL (`descr`). |
| **conflitos** | Prefixos com mais de um ASN de origem distinto registrado no IRR (MOAS). A aba fica destacada em vermelho com a contagem (ex: `conflitos (1)`) quando há ocorrências. |

A barra de downloads no topo dos resultados gera os arquivos descritos na
próxima seção — tudo é montado no próprio navegador a partir dos dados já
carregados (não dispara novas consultas de rede).

---

## Arquivos gerados

### prefixos.csv (bruto)

CSV com **todas** as entradas encontradas, sem nenhuma filtragem — serve
como registro de auditoria completo da coleta.

| Coluna | Descrição |
|---|---|
| `asn` | ASN ao qual a entrada pertence (ex: `AS28173`). |
| `familia` | `v4` ou `v6`. |
| `prefixo` | Bloco CIDR (ex: `45.179.120.0/22`). |
| `fonte` | `alocacao` (registro.br) ou `irr` (objeto route/route6). |
| `fonte_detalhe` | Para `alocacao`, sempre `registro.br`. Para `irr`, o registro de origem do objeto (`RADB`, `ARIN`, `RIPE`, `TC`, etc — campo `source:` do RPSL). |
| `descr` | Texto livre do campo `descr:` do objeto RPSL (quando existir). |

### prefixos_resumo.csv

Versão **sumarizada** por ASN+família: remove qualquer prefixo do IRR que
já esteja contido em um bloco maior presente no conjunto (alocação do
registro.br tem prioridade em caso de empate de tamanho). É a base usada
pelos arquivos `_v4.txt`/`_v6.txt` e pelos exports de Juniper/Huawei.

| Coluna | Descrição |
|---|---|
| `asn` | ASN ao qual o prefixo pertence. |
| `familia` | `v4` ou `v6`. |
| `prefixo` | Bloco CIDR já sumarizado. |
| `fonte` | `alocacao` ou `irr` (origem do bloco que "sobreviveu" à sumarização). |

### prefixos_conflitos.csv

Só é gerado (botão habilitado) quando há pelo menos um conflito de origem
(MOAS) detectado. Uma linha por **registro individual** envolvido em algum
conflito (não por grupo) — então um prefixo com 3 objetos no IRR aparece
em 3 linhas.

| Coluna | Descrição |
|---|---|
| `familia` | `v4` ou `v6`. |
| `prefixo` | Prefixo exato em conflito (mesmo prefixo se repete entre as linhas de um mesmo conflito). |
| `asn` | ASN de origem daquele registro específico. |
| `fonte_detalhe` | Registro de origem do objeto (`RADB`, `ARIN`, etc). |
| `descr` | Descrição RPSL daquele objeto, quando existir. |

### prefixos_v4.txt / prefixos_v6.txt

Lista plana, um prefixo por linha, com a **união deduplicada** dos
prefixos da aba "resumo" (sumarizados) — pronta para colar em qualquer
ferramenta de filtro/ACL que aceite uma lista simples de CIDRs.

### juniper_prefix-list_\<nome\>.txt

Comandos de configuração Junos, um por linha, a partir da lista sumarizada:

```
set policy-options prefix-list CLIENTES-V4 45.179.120.0/22
set policy-options prefix-list CLIENTES-V4 209.14.128.0/24
```

O `<nome>` no nome do arquivo reflete o valor preenchido no campo "nome
prefix-list" das opções avançadas (`CLIENTES-V4`/`CLIENTES-V6` por padrão).
Um arquivo é gerado para v4 e outro para v6 (botões separados).

### huawei_acl_\<nome\>.txt

Comandos de ACL avançada no formato VRP (Huawei), com numeração de regra
incremental de 5 em 5:

```
acl name CLIENTES-V4 advance
 rule 5 permit ip source 45.179.120.0 0.0.3.255
 rule 10 permit ip source 209.14.128.0 0.0.0.255
```

Para IPv4, o prefixo CIDR é convertido para **rede + máscara wildcard**
(máscara invertida — ex: `/22` → `0.0.3.255`), formato exigido pelo `rule
... permit ip source`. Para IPv6, o bloco é usado em notação CIDR direta:

```
acl ipv6 name CLIENTES-V6 advance
 rule 5 permit ipv6 source 2804:3154::/32
```
