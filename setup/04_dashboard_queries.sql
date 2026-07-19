-- Queries analíticas sobre o star schema (olist.gold) — base do dashboard.
-- Cada uma junta o fato às dimensões pela surrogate key. Rodar no SQL Editor / datasets do dashboard.

-- 1) KPIs gerais
SELECT
  COUNT(DISTINCT order_id)                              AS pedidos,
  ROUND(SUM(preco), 2)                                 AS receita,
  ROUND(SUM(preco) / COUNT(DISTINCT order_id), 2)      AS ticket_medio,
  ROUND(SUM(frete), 2)                                 AS frete_total
FROM olist.gold.fato_itens_pedido;

-- 2) Receita por mês (série temporal) — usa dim_data
SELECT d.ano_mes, ROUND(SUM(f.preco), 2) AS receita
FROM olist.gold.fato_itens_pedido f
JOIN olist.gold.dim_data d ON f.date_key = d.date_key
GROUP BY d.ano_mes
ORDER BY d.ano_mes;

-- 3) Top 10 categorias por receita — usa dim_produto
SELECT p.product_category AS categoria, ROUND(SUM(f.preco), 2) AS receita
FROM olist.gold.fato_itens_pedido f
JOIN olist.gold.dim_produto p ON f.sk_produto = p.sk_produto
GROUP BY p.product_category
ORDER BY receita DESC
LIMIT 10;

-- 4) Receita e pedidos por estado do cliente — usa dim_cliente
SELECT c.customer_state AS estado,
       ROUND(SUM(f.preco), 2)        AS receita,
       COUNT(DISTINCT f.order_id)    AS pedidos
FROM olist.gold.fato_itens_pedido f
JOIN olist.gold.dim_cliente c ON f.sk_cliente = c.sk_cliente
GROUP BY c.customer_state
ORDER BY receita DESC;
