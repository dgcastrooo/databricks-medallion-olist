# data/

Os arquivos brutos ficam aqui localmente, mas **não vão pro git** (ver `.gitignore`) — dado bruto não se versiona.

## Dataset

**Brazilian E-Commerce Public Dataset by Olist** (Kaggle) — ~100k pedidos reais de e-commerce brasileiro, em tabelas normalizadas (estilo OLTP):

- `olist_orders_dataset` — pedidos
- `olist_order_items_dataset` — itens de cada pedido
- `olist_customers_dataset` — clientes
- `olist_products_dataset` — produtos
- `olist_sellers_dataset` — vendedores
- `olist_order_payments_dataset` — pagamentos
- `olist_order_reviews_dataset` — avaliações
- `olist_geolocation_dataset` — geolocalização (CEP)
- `product_category_name_translation` — tradução das categorias

Fonte: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
