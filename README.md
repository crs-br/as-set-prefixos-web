# Registry Console — prefixos por as-set e ASN

Coleta prefixos IPv4/IPv6 via **AS-SET** ou por **ASN específico**, cruzando alocação registrada no `whois.registro.br` com objetos `route:`/`route6:` do IRR. O sistema executa as consultas com aceleração **multithread**, permite a listagem instantânea apenas dos ASNs membros de um AS-SET sem validação de prefixos, sumariza os blocos sem redundâncias, detecta conflitos de origem (MOAS) capturando e-mails de contato (`changed:`/`notify:`) para acionamento de NOC, extrai registros brutos RPSL e exporta prefix-lists Juniper e ACLs Huawei.

Requer conexão com a internet com saída liberada na porta 43/tcp (protocolo whois) — é assim que o programa fala com `whois.radb.net`, `whois.registro.br` e demais servidores IRR.

---

## Funcionalidades

* **Consulta por AS-SET:** Expande recursivamente os membros no IRR e coleta os prefixos de todos os ASNs associados[cite: 3].
* **Modo Apenas ASNs:** Opção para expandir e listar apenas os ASNs membros do as-set instantaneamente, sem passar pela validação de blocos e registros de IRR.
* **Consulta por ASN específico:** Permite auditar diretamente um ASN avulso (ex: `AS65001` ou `65001`).
* **Multithreading:** Coleta paralela de dados de múltiplos ASNs e verificação concorrente de conflitos MOAS em múltiplos servidores IRR.
* **Detecção de Conflitos (MOAS) com E-mails de NOC:** Identifica anúncios concorrentes no IRR e extrai endereços de e-mail dos campos `changed:` e `notify:` com links `mailto:` diretos.
* **Visualização e Download RPSL (Raw):** Extração completa dos objetos `aut-num` e `route:`/`route6:` direto da base IRR em formato de texto (`irr_records.txt`).
* **Sumarização Inteligente:** Elimina sub-redes redundantes que já estejam contidas em blocos maiores[cite: 3, 5].
* **Exportações:** Arquivos planos (`asns.txt`, `v4.txt`, `v6.txt`), prefix-list Juniper (`.txt`), ACL Huawei (`.txt`) e relatórios em CSV (Resumo, Bruto e Conflitos com e-mail).

---

## Instalação via git (alternativa ao zip)

```bash
git clone [https://github.com/](https://github.com/)<seu-usuario>/as-set-prefixos-web.git
cd as-set-prefixos-web