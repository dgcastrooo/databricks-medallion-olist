# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — ingestão do Olist
# MAGIC Lê os CSVs crus de `bronze/raw/olist/` e grava como tabelas Delta em `olist.bronze`.
# MAGIC Sem limpeza: só adiciona metadados de ingestão. Tipagem/dedup ficam pra silver.

# COMMAND ----------

from pyspark.sql.functions import current_timestamp, lit

RAW = "abfss://bronze@stmedallionolist.dfs.core.windows.net/raw/olist"

# nome-limpo -> arquivo de origem
TABELAS = {
    "customers":            "olist_customers_dataset.csv",
    "geolocation":          "olist_geolocation_dataset.csv",
    "order_items":          "olist_order_items_dataset.csv",
    "order_payments":       "olist_order_payments_dataset.csv",
    "order_reviews":        "olist_order_reviews_dataset.csv",
    "orders":               "olist_orders_dataset.csv",
    "products":             "olist_products_dataset.csv",
    "sellers":              "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# COMMAND ----------

for tabela, arquivo in TABELAS.items():
    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)   # bronze infere; tipagem explícita é na silver
        .option("multiLine", True)     # comentários do olist têm quebra de linha
        .option("escape", '"')          # aspas dentro de campo entre aspas
        .csv(f"{RAW}/{arquivo}")
        .withColumn("_ingestion_ts", current_timestamp())  # quando entrou
        .withColumn("_source_file", lit(arquivo))           # de onde veio
    )
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")   # o schema inferido mudou (multiLine); sobrescreve
        .saveAsTable(f"olist.bronze.{tabela}")
    )
    print(f"olist.bronze.{tabela}: {df.count()} linhas, {len(df.columns)} colunas")

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW TABLES IN olist.bronze;
