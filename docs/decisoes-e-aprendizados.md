# Decisões & Aprendizados

Documento de estudo do projeto — o *porquê* de cada escolha, as etapas, os perrengues resolvidos e um resumo estilo entrevista por fase. (O `README.md` é a vitrine; este arquivo é o making-of.)

---

## Decisões macro

| Decisão | Escolha | Por quê |
|---|---|---|
| **Compute** | Azure Databricks direto (não Free Edition) | Um ambiente só, na conta Azure, lendo do próprio ADLS Gen2 — mais clean e bate com o CV (vaga Azure/Databricks). Crédito free ($200) sobra; o risco é esquecer cluster ligado, não o custo total. |
| **Dataset** | Olist (e-commerce brasileiro, Kaggle) | Dado real, reconhecível, normalizado (estilo OLTP). A modelagem em star schema é **nossa** — é o exercício. Melhor que dado sintético pra praticar joins/desnormalização. |
| **Arquitetura** | Medallion (bronze→silver→gold) + Lakehouse + ELT | Padrão de mercado: carrega cru e transforma no destino; Delta dá ACID sobre o lake. |

---

## Fase 0 — Setup

**Objetivo:** preparar conta, ferramentas e repositório antes de tocar em dado.

**Decisões e aprendizados:**
- **Isolar a conta Azure pessoal da corporativa** com a variável `AZURE_CONFIG_DIR=~/.azure-pessoal`. O `az login` normal *acumula* contas no mesmo `~/.azure` e troca o contexto ativo — risco de rodar comando na subscription errada. Apontar `AZURE_CONFIG_DIR` pra outra pasta mantém as duas identidades 100% separadas. É o jeito profissional de gerenciar múltiplos contextos.
- **Budget alert:** a UI de Budgets veio bloqueada (comum em Free Trial — escopo de billing limitado). Sem problema: **no Free Trial não há cobrança além do crédito** (serviços são suspensos quando acaba). O freio real é disciplina de `auto-terminate` + teardown.
- **IaC vs. script imperativo:** usamos `az` CLI versionado em `infra/` — provisionamento *scriptado* e reproduzível, mas não é IaC declarativo de verdade (isso seria Terraform/Bicep). Distinção que vale citar em entrevista.

**Resumo de entrevista:** *"Comecei isolando o contexto do Azure CLI pra não misturar minha conta pessoal com a corporativa, montei o repositório com estrutura Medallion e versionei todo o provisionamento como scripts."*

---

## Fase 1 — Infra & Governança

**Objetivo:** provisionar a base (storage, compute, governança) antes do dado.

**Ordem e decisões:**
1. **Resource Group** (`rg-medallion-olist`, região `eastus2`) — container de tudo; `az group delete` no fim = teardown total. Região East US 2 pela **cota de vCPU mais folgada** no Free (evita "quota exceeded" no cluster) e por ser barata/completa. Regra: **tudo na mesma região** (evita custo de tráfego).
2. **Registro de resource providers** — em subscription nova quase tudo vem `NotRegistered`; criar recurso antes disso falha com o erro enganoso **`SubscriptionNotFound`**. Registro é grátis, por-subscription, uma vez. Registramos Storage, Databricks, Compute, Network, KeyVault.
3. **ADLS Gen2** (`stmedallionolist`) — a flag **`--enable-hierarchical-namespace true`** é o que torna a conta "Gen2" (diretórios reais, ACLs POSIX, listagem eficiente) em vez de blob plano. SKU `Standard_LRS` (mais barato).
4. **Containers** `bronze/silver/gold` — um por camada. Escolha didática (mapeia 1:1 a arquitetura). *Nota de escala:* em produção grande, a separação real costuma ser por ambiente/domínio, com o medallion como schemas no UC — não por camada física.
5. **Workspace Databricks** (`dbw-medallion-olist`, SKU **`trial`**) — trial dá 14 dias de **DBU grátis** com features **Premium**, necessárias pro **Unity Catalog** (o tier Standard NÃO suporta UC). Paga-se só a VM.
6. **Access Connector** (`ac-medallion-olist`, managed identity) + papel **`Storage Blob Data Contributor`** no storage — é assim que o UC acessa o lake **sem chave/senha**. O role assignment precisa de retry (a identidade demora a propagar no Entra ID).
7. **Unity Catalog** — `cred_olist` (storage credential apontando pro Access Connector, criado pela **UI** porque o SQL de credential no Azure é inconsistente) → **external locations** (bronze/silver/gold) → **catalog `olist`** + schemas bronze/silver/gold.
   - **Perrengue do metastore:** `CREATE CATALOG` sem `MANAGED LOCATION` falhou com *"Metastore storage root URL does not exist / Default Storage is enabled"*. No modelo novo de metastore ("Default Storage"), o metastore não tem root — o catálogo precisa de um `MANAGED LOCATION` explícito. Apontamos pro nosso ADLS (dado no próprio lake, governado pelo UC).

**Conceitos-chave (entrevista):**
- **Managed identity > chave:** acesso ao storage via Access Connector, sem segredo em lugar nenhum.
- **Storage credential → external location → catalog/schema:** a cadeia de governança do Unity Catalog.
- **External location vs. managed location:** a primeira governa *acesso* a um caminho; a segunda define *onde* tabelas gerenciadas guardam dado.

**Resumo de entrevista:** *"Montei a governança do jeito enterprise: identidade gerenciada via Access Connector com RBAC no storage, e no Unity Catalog encadeei storage credential → external locations → catalog e schemas, com as managed locations apontando pro meu ADLS Gen2. Assim o dado fica no meu lake e o acesso é 100% governado, sem chave."*
