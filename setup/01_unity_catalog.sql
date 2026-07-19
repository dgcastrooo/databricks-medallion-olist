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
--    o metastore nao tem storage root (modelo "Default Storage"), entao o catalog
--    precisa de um MANAGED LOCATION explicito -> apontamos pro NOSSO ADLS Gen2.
--    catalog usa o container bronze como raiz; silver e gold cada um no seu container.
CREATE CATALOG IF NOT EXISTS olist
  MANAGED LOCATION 'abfss://bronze@stmedallionolist.dfs.core.windows.net/'
  COMMENT 'lakehouse olist - e-commerce brasileiro';

CREATE SCHEMA IF NOT EXISTS olist.bronze
  COMMENT 'dado cru ingerido';                       -- herda a raiz do catalog (bronze)
CREATE SCHEMA IF NOT EXISTS olist.silver
  MANAGED LOCATION 'abfss://silver@stmedallionolist.dfs.core.windows.net/'
  COMMENT 'dado limpo e tipado';
CREATE SCHEMA IF NOT EXISTS olist.gold
  MANAGED LOCATION 'abfss://gold@stmedallionolist.dfs.core.windows.net/'
  COMMENT 'star schema pronto pra BI';

-- 3) verificacao
SHOW EXTERNAL LOCATIONS;
SHOW SCHEMAS IN olist;
