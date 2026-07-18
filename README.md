# databricks-medallion-olist

Pipeline de dados end-to-end em **arquitetura Medallion** (bronze → silver → gold) sobre o **Azure**, usando **Databricks + Delta Lake + Unity Catalog**, com dados reais de e-commerce brasileiro (dataset Olist).

> 🚧 Em construção — projeto de portfólio, evoluindo por fases.

## Objetivo

Modelar um lakehouse completo a partir de dados transacionais crus (estilo OLTP) até um **star schema** pronto pra consumo em BI — mostrando ingestão, limpeza, modelagem dimensional, orquestração e governança.

## Stack

| Camada | Ferramenta |
|---|---|
| Data lake | Azure Data Lake Storage Gen2 |
| Processamento | Azure Databricks (Spark / PySpark) |
| Formato de tabela | Delta Lake |
| Governança | Unity Catalog |
| Orquestração | Databricks Workflows |
| Consumo | Power BI / Databricks SQL |

## Arquitetura

```
Olist (OLTP normalizado)
      │  ingestão
      ▼
   BRONZE  ── dado cru em Delta
      │  limpeza, tipagem, dedup
      ▼
   SILVER  ── dado confiável
      │  modelagem dimensional
      ▼
    GOLD   ── star schema (fato + dimensões)
      │
      ▼
  Power BI / Databricks SQL
```

## Status por fase

- [ ] Fase 0 — setup (conta, repo, ferramentas)
- [ ] Fase 1 — infra (ADLS Gen2, workspace, Unity Catalog)
- [ ] Fase 2 — dados de origem (Olist)
- [ ] Fase 3 — bronze
- [ ] Fase 4 — silver
- [ ] Fase 5 — gold (star schema)
- [ ] Fase 6 — orquestração + governança
- [ ] Fase 7 — dashboard
- [ ] Fase 8 — documentação final
