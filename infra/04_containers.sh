#!/usr/bin/env bash
# cria os containers (filesystems) das 3 camadas medallion no ADLS Gen2.
# a chave e' buscada em runtime via `az` (nunca fica hardcoded/commitada).
# obs: usar account-key aqui e' so pra bootstrap; o acesso do Databricks aos
# dados vai ser via managed identity (Access Connector) + Unity Catalog, sem chave.
set -euo pipefail
source "$(dirname "$0")/00_variables.sh"

export ST="stmedallionolist"
KEY=$(az storage account keys list --account-name "$ST" -g "$RG" --query "[0].value" -o tsv)

for c in bronze silver gold; do
  az storage fs create -n "$c" --account-name "$ST" --account-key "$KEY"
done

az storage fs list --account-name "$ST" --account-key "$KEY" --query "[].name" -o tsv
