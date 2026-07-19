# Databricks notebook source
# MAGIC %md
# MAGIC # Gold — star schema
# MAGIC A partir da silver (normalizada), monta um **star schema** desnormalizado:
# MAGIC 1 fato (`fato_itens_pedido`, grão = item de pedido) + 5 dimensões com **surrogate keys**.
# MAGIC Categoria (EN) e geolocalização são "coladas" nas dimensões (por isso é star, não snowflake).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

def grava_gold(df, nome):
    (df.write.format("delta").mode("overwrite")
       .option("overwriteSchema", "true").saveAsTable(f"olist.gold.{nome}"))
    print(f"olist.gold.{nome}: {df.count():,} linhas")

# COMMAND ----------
# MAGIC %md ## dim_data — calendário gerado a partir das datas de compra

# COMMAND ----------
_bounds = (spark.table("olist.silver.orders")
           .select(F.to_date(F.min("order_purchase_timestamp")).alias("mn"),
                   F.to_date(F.max("order_purchase_timestamp")).alias("mx")))
dim_data = (
    _bounds
    .select(F.explode(F.sequence("mn", "mx", F.expr("interval 1 day"))).alias("data"))
    .withColumn("date_key", F.date_format("data", "yyyyMMdd").cast("int"))  # SK natural da data
    .withColumn("ano", F.year("data"))
    .withColumn("mes", F.month("data"))
    .withColumn("dia", F.dayofmonth("data"))
    .withColumn("trimestre", F.quarter("data"))
    .withColumn("dia_semana", F.dayofweek("data"))
    .withColumn("ano_mes", F.date_format("data", "yyyy-MM"))
    .select("date_key", "data", "ano", "mes", "dia", "trimestre", "dia_semana", "ano_mes")
)
grava_gold(dim_data, "dim_data")

# COMMAND ----------
# MAGIC %md ## dim_cliente — cliente + geolocalização (lat/lng) colada

# COMMAND ----------
_geo = (spark.table("olist.silver.geolocation")
        .select(F.col("geolocation_zip_code_prefix").alias("zip"),
                "geolocation_lat", "geolocation_lng"))
dim_cliente = (
    spark.table("olist.silver.customers")
    .join(_geo, F.col("customer_zip_code_prefix") == F.col("zip"), "left")
    .select("customer_id", "customer_unique_id", "customer_city", "customer_state",
            F.col("geolocation_lat").alias("lat"), F.col("geolocation_lng").alias("lng"))
    .withColumn("sk_cliente", F.row_number().over(Window.orderBy("customer_id")))
    .select("sk_cliente", "customer_id", "customer_unique_id", "customer_city", "customer_state", "lat", "lng")
)
grava_gold(dim_cliente, "dim_cliente")

# COMMAND ----------
# MAGIC %md ## dim_produto — produto + categoria em inglês colada

# COMMAND ----------
dim_produto = (
    spark.table("olist.silver.products")
    .join(spark.table("olist.silver.category_translation"), "product_category_name", "left")
    .select("product_id",
            "product_category_name",
            F.col("product_category_name_english").alias("product_category"),
            "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm")
    .withColumn("sk_produto", F.row_number().over(Window.orderBy("product_id")))
    .select("sk_produto", "product_id", "product_category_name", "product_category",
            "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm")
)
grava_gold(dim_produto, "dim_produto")

# COMMAND ----------
# MAGIC %md ## dim_vendedor — vendedor + cidade/estado

# COMMAND ----------
dim_vendedor = (
    spark.table("olist.silver.sellers")
    .select("seller_id", "seller_city", "seller_state")
    .withColumn("sk_vendedor", F.row_number().over(Window.orderBy("seller_id")))
    .select("sk_vendedor", "seller_id", "seller_city", "seller_state")
)
grava_gold(dim_vendedor, "dim_vendedor")

# COMMAND ----------
# MAGIC %md ## dim_pedido — atributos do pedido (status e datas)

# COMMAND ----------
dim_pedido = (
    spark.table("olist.silver.orders")
    .select("order_id", "order_status",
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date")
    .withColumn("sk_pedido", F.row_number().over(Window.orderBy("order_id")))
    .select("sk_pedido", "order_id", "order_status",
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date")
)
grava_gold(dim_pedido, "dim_pedido")

# COMMAND ----------
# MAGIC %md ## fato_itens_pedido — grão = item de pedido; junta tudo pra pegar as SKs

# COMMAND ----------
# lê as dimensões de volta (SKs já persistidas e estáveis)
d_cliente  = spark.table("olist.gold.dim_cliente").select("sk_cliente", "customer_id")
d_produto  = spark.table("olist.gold.dim_produto").select("sk_produto", "product_id")
d_vendedor = spark.table("olist.gold.dim_vendedor").select("sk_vendedor", "seller_id")
d_pedido   = spark.table("olist.gold.dim_pedido").select("sk_pedido", "order_id")

# order_items + orders (pra trazer customer_id e a data da compra)
_orders = spark.table("olist.silver.orders").select("order_id", "customer_id", "order_purchase_timestamp")

fato = (
    spark.table("olist.silver.order_items")
    .join(_orders, "order_id", "left")
    .withColumn("date_key", F.date_format("order_purchase_timestamp", "yyyyMMdd").cast("int"))
    .join(d_pedido, "order_id", "left")
    .join(d_cliente, "customer_id", "left")
    .join(d_produto, "product_id", "left")
    .join(d_vendedor, "seller_id", "left")
    .select("sk_pedido", "sk_cliente", "sk_produto", "sk_vendedor", "date_key",
            "order_id", "order_item_id",          # chaves de negócio (degeneradas)
            F.col("price").alias("preco"),
            F.col("freight_value").alias("frete"))
)
grava_gold(fato, "fato_itens_pedido")

# COMMAND ----------
# MAGIC %md ## Qualidade — integridade referencial (órfãos = FK sem dimensão)

# COMMAND ----------
_f = spark.table("olist.gold.fato_itens_pedido")
_total = _f.count()
for fk in ["sk_pedido", "sk_cliente", "sk_produto", "sk_vendedor", "date_key"]:
    orfaos = _f.filter(F.col(fk).isNull()).count()
    print(f"{fk}: {orfaos:,} órfãos de {_total:,} ({'OK' if orfaos == 0 else 'ATENÇÃO'})")

# COMMAND ----------
# MAGIC %sql
# MAGIC SHOW TABLES IN olist.gold;
