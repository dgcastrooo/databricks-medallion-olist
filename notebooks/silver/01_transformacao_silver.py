# Databricks notebook source
# MAGIC %md
# MAGIC # Silver — limpeza, tipagem, dedup + quarentena
# MAGIC Lê `olist.bronze.*`, **limpa** (tipos/padronização/dedup) e **valida**.
# MAGIC Linha boa → `olist.silver.<tabela>`; linha reprovada → `olist.silver.<tabela>_quarantine` (com `_motivo_quarentena`).
# MAGIC Integridade referencial (órfãos) fica pra gold.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

NADA = F.lit(None).cast("string")  # "sem motivo" = linha válida

def grava_silver(df, nome, chaves, motivo):
    """separa válidos x quarentena e grava as duas tabelas Delta."""
    ts = F.current_timestamp()
    df = df.withColumn("_motivo_quarentena", motivo)
    validos = (df.filter(F.col("_motivo_quarentena").isNull())
                 .drop("_motivo_quarentena").withColumn("_silver_ts", ts))
    quarentena = df.filter(F.col("_motivo_quarentena").isNotNull()).withColumn("_silver_ts", ts)

    (validos.write.format("delta").mode("overwrite")
       .option("overwriteSchema", "true").saveAsTable(f"olist.silver.{nome}"))
    (quarentena.write.format("delta").mode("overwrite")
       .option("overwriteSchema", "true").saveAsTable(f"olist.silver.{nome}_quarantine"))

    tot, q = validos.count(), quarentena.count()
    uniq = validos.select(*chaves).distinct().count()
    print(f"olist.silver.{nome}: {tot:,} válidos | {q:,} quarentena | chave {chaves} única? {'OK' if tot==uniq else 'DUP!'}")

# COMMAND ----------
# MAGIC %md ## customers

# COMMAND ----------
customers = (
    spark.table("olist.bronze.customers")
    .withColumn("customer_zip_code_prefix", F.lpad(F.col("customer_zip_code_prefix").cast("string"), 5, "0"))
    .withColumn("customer_city", F.lower(F.trim("customer_city")))
    .withColumn("customer_state", F.upper(F.trim("customer_state")))
    .select("customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state")
    .dropDuplicates(["customer_id"])
)
motivo = F.when(F.col("customer_id").isNull(), "customer_id nulo").otherwise(NADA)
grava_silver(customers, "customers", ["customer_id"], motivo)

# COMMAND ----------
# MAGIC %md ## geolocation — 1 linha por CEP

# COMMAND ----------
geolocation = (
    spark.table("olist.bronze.geolocation")
    .withColumn("geolocation_zip_code_prefix", F.lpad(F.col("geolocation_zip_code_prefix").cast("string"), 5, "0"))
    .withColumn("geolocation_city", F.lower(F.trim("geolocation_city")))
    .withColumn("geolocation_state", F.upper(F.trim("geolocation_state")))
    .groupBy("geolocation_zip_code_prefix")
    .agg(
        F.round(F.avg("geolocation_lat"), 6).alias("geolocation_lat"),
        F.round(F.avg("geolocation_lng"), 6).alias("geolocation_lng"),
        F.mode("geolocation_city").alias("geolocation_city"),
        F.mode("geolocation_state").alias("geolocation_state"),
    )
)
motivo = F.when(F.col("geolocation_zip_code_prefix").isNull(), "cep nulo").otherwise(NADA)
grava_silver(geolocation, "geolocation", ["geolocation_zip_code_prefix"], motivo)

# COMMAND ----------
# MAGIC %md ## order_items — chave (order_id, order_item_id); valores >= 0

# COMMAND ----------
order_items = (
    spark.table("olist.bronze.order_items")
    .withColumn("shipping_limit_date", F.try_to_timestamp("shipping_limit_date"))
    .withColumn("price", F.col("price").cast("decimal(10,2)"))
    .withColumn("freight_value", F.col("freight_value").cast("decimal(10,2)"))
    .select("order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value")
    .dropDuplicates(["order_id", "order_item_id"])
)
motivo = (
    F.when(F.col("order_id").isNull() | F.col("order_item_id").isNull(), "chave nula")
     .when(F.col("price") < 0, "price negativo")
     .when(F.col("freight_value") < 0, "freight negativo")
     .otherwise(NADA)
)
grava_silver(order_items, "order_items", ["order_id", "order_item_id"], motivo)

# COMMAND ----------
# MAGIC %md ## order_payments — chave (order_id, payment_sequential); valor >= 0

# COMMAND ----------
order_payments = (
    spark.table("olist.bronze.order_payments")
    .withColumn("payment_type", F.lower(F.trim("payment_type")))
    .withColumn("payment_value", F.col("payment_value").cast("decimal(10,2)"))
    .select("order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value")
    .dropDuplicates(["order_id", "payment_sequential"])
)
motivo = (
    F.when(F.col("order_id").isNull() | F.col("payment_sequential").isNull(), "chave nula")
     .when(F.col("payment_value") < 0, "payment_value negativo")
     .otherwise(NADA)
)
grava_silver(order_payments, "order_payments", ["order_id", "payment_sequential"], motivo)

# COMMAND ----------
# MAGIC %md ## order_reviews — dedup review_id (mais recente); score 1..5

# COMMAND ----------
w_review = Window.partitionBy("review_id").orderBy(F.col("review_answer_timestamp").desc())
order_reviews = (
    spark.table("olist.bronze.order_reviews")
    .withColumn("review_creation_date", F.try_to_timestamp("review_creation_date"))
    .withColumn("review_answer_timestamp", F.try_to_timestamp("review_answer_timestamp"))
    .withColumn("_rn", F.row_number().over(w_review))
    .filter(F.col("_rn") == 1).drop("_rn")
    .select("review_id", "order_id", "review_score", "review_comment_title",
            "review_comment_message", "review_creation_date", "review_answer_timestamp")
)
motivo = (
    F.when(F.col("review_id").isNull(), "review_id nulo")
     .when(~F.col("review_score").between(1, 5), "score fora de 1..5")
     .otherwise(NADA)
)
grava_silver(order_reviews, "order_reviews", ["review_id"], motivo)

# COMMAND ----------
# MAGIC %md ## orders — datas viram timestamp; compra deve existir

# COMMAND ----------
_date_cols = [
    "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
    "order_delivered_customer_date", "order_estimated_delivery_date",
]
orders = spark.table("olist.bronze.orders").withColumn("order_status", F.lower(F.trim("order_status")))
for c in _date_cols:
    orders = orders.withColumn(c, F.try_to_timestamp(c))
orders = orders.select("order_id", "customer_id", "order_status", *_date_cols).dropDuplicates(["order_id"])
motivo = (
    F.when(F.col("order_id").isNull() | F.col("customer_id").isNull(), "chave nula")
     .when(F.col("order_purchase_timestamp").isNull(), "data de compra ausente")
     .otherwise(NADA)
)
grava_silver(orders, "orders", ["order_id"], motivo)

# COMMAND ----------
# MAGIC %md ## products — corrige typos, contadores viram int

# COMMAND ----------
products = (
    spark.table("olist.bronze.products")
    .withColumnRenamed("product_name_lenght", "product_name_length")
    .withColumnRenamed("product_description_lenght", "product_description_length")
    .withColumn("product_name_length", F.col("product_name_length").cast("int"))
    .withColumn("product_description_length", F.col("product_description_length").cast("int"))
    .withColumn("product_photos_qty", F.col("product_photos_qty").cast("int"))
    .withColumn("product_weight_g", F.col("product_weight_g").cast("int"))
    .withColumn("product_length_cm", F.col("product_length_cm").cast("int"))
    .withColumn("product_height_cm", F.col("product_height_cm").cast("int"))
    .withColumn("product_width_cm", F.col("product_width_cm").cast("int"))
    .withColumn("product_category_name", F.lower(F.trim("product_category_name")))
    .select("product_id", "product_category_name", "product_name_length", "product_description_length",
            "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm")
    .dropDuplicates(["product_id"])
)
motivo = F.when(F.col("product_id").isNull(), "product_id nulo").otherwise(NADA)
grava_silver(products, "products", ["product_id"], motivo)

# COMMAND ----------
# MAGIC %md ## sellers

# COMMAND ----------
sellers = (
    spark.table("olist.bronze.sellers")
    .withColumn("seller_zip_code_prefix", F.lpad(F.col("seller_zip_code_prefix").cast("string"), 5, "0"))
    .withColumn("seller_city", F.lower(F.trim("seller_city")))
    .withColumn("seller_state", F.upper(F.trim("seller_state")))
    .select("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state")
    .dropDuplicates(["seller_id"])
)
motivo = F.when(F.col("seller_id").isNull(), "seller_id nulo").otherwise(NADA)
grava_silver(sellers, "sellers", ["seller_id"], motivo)

# COMMAND ----------
# MAGIC %md ## category_translation

# COMMAND ----------
category_translation = (
    spark.table("olist.bronze.category_translation")
    .withColumn("product_category_name", F.lower(F.trim("product_category_name")))
    .withColumn("product_category_name_english", F.lower(F.trim("product_category_name_english")))
    .dropDuplicates(["product_category_name"])
)
motivo = F.when(F.col("product_category_name").isNull(), "categoria nula").otherwise(NADA)
grava_silver(category_translation, "category_translation", ["product_category_name"], motivo)

# COMMAND ----------
# MAGIC %sql
# MAGIC -- válidas + quarentena lado a lado
# MAGIC SHOW TABLES IN olist.silver;
