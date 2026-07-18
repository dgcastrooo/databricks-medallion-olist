-- Unity Catalog — external locations + catalog + schemas do lakehouse olist.
-- rodar no SQL Editor do Databricks com o Serverless Starter Warehouse.
-- pre-requisito: storage credential `cred_olist` ja criado na UI
-- (Azure Managed Identity apontando pro Access Connector ac-medallion-olist).

-- 1) EXTERNAL LOCATIONS: uma por container do ADLS Gen2, governadas pelo credential.
--    e' isto que da acesso GOVERNADO ao storage — nada de chave/connection string.
CREATE EXTERNAL LOCATION IF NOT EXISTS olist_bronze
  URL 'abfss://bronze@stmedallionolist.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL cred_olist)
  COMMENT 'camada bronze (dado cru)';

CREATE EXTERNAL LOCATION IF NOT EXISTS olist_silver
  URL 'abfss://silver@stmedallionolist.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL cred_olist)
  COMMENT 'camada silver (limpo)';

CREATE EXTERNAL LOCATION IF NOT EXISTS olist_gold
  URL 'abfss://gold@stmedallionolist.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL cred_olist)
  COMMENT 'camada gold (star schema)';

-- 2) CATALOG + SCHEMAS: o medallion como estrutura logica no Unity Catalog.
CREATE CATALOG IF NOT EXISTS olist COMMENT 'lakehouse olist - e-commerce brasileiro';
CREATE SCHEMA  IF NOT EXISTS olist.bronze COMMENT 'dado cru ingerido';
CREATE SCHEMA  IF NOT EXISTS olist.silver COMMENT 'dado limpo e tipado';
CREATE SCHEMA  IF NOT EXISTS olist.gold   COMMENT 'star schema pronto pra BI';

-- 3) verificacao
SHOW EXTERNAL LOCATIONS;
SHOW SCHEMAS IN olist;
