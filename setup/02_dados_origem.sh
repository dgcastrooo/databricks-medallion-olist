#!/usr/bin/env bash
# Fase 2 — baixa o dataset Olist (Kaggle) e sobe os CSVs crus pro container bronze (raw/olist).
#
# pre-requisitos:
#   - token da Kaggle configurado em ~/.kaggle/access_token (formato novo KGAT_...) — NUNCA commitar.
#   - kaggle CLI instalada no venv do projeto (.venv).
#
# obs: 'az storage fs directory upload' usa azcopy por baixo; como o azcopy nao baixou
# neste ambiente, subimos arquivo a arquivo com 'az storage fs file upload' (usa o SDK).
set -euo pipefail
source "$(dirname "$0")/../infra/00_variables.sh"
export ST="stmedallionolist"

# 1) baixar do Kaggle pra data/olist (gitignored)
./.venv/bin/kaggle datasets download -d olistbr/brazilian-ecommerce -p data/olist --unzip

# 2) subir os CSVs pro lake (bronze/raw/olist)
KEY=$(az storage account keys list --account-name "$ST" -g "$RG" --query "[0].value" -o tsv)
for f in data/olist/*.csv; do
  name=$(basename "$f")
  az storage fs file upload -f bronze --account-name "$ST" --account-key "$KEY" \
    -s "$f" -p "raw/olist/$name" --overwrite
  echo "subiu: $name"
done

az storage fs file list -f bronze --account-name "$ST" --account-key "$KEY" --path "raw/olist" -o table
