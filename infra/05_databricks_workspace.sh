#!/usr/bin/env bash
# cria o workspace Azure Databricks.
# sku 'trial' = 14 dias de DBU gratis com features Premium (necessario pro Unity Catalog;
# o tier Standard NAO suporta UC). no trial paga-se so a VM do cluster.
set -euo pipefail
source "$(dirname "$0")/00_variables.sh"

export WS="dbw-medallion-olist"

az databricks workspace create \
  --name "$WS" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku trial \
  --output table
