#!/usr/bin/env bash
# cria a storage account ADLS Gen2 — o data lake do projeto.
# a flag --enable-hierarchical-namespace true e' o que torna a conta "Gen2"
# (diretorios de verdade, ACLs POSIX, listagem eficiente) em vez de blob comum.
set -euo pipefail
source "$(dirname "$0")/00_variables.sh"

export ST="stmedallionolist"   # nome unico no mundo, 3-24 chars, so minusculas/numeros

az storage account create \
  --name "$ST" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace true \
  --output table
