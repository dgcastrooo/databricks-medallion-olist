#!/usr/bin/env bash
# cria o Access Connector for Azure Databricks (managed identity) e da a ele o papel
# 'Storage Blob Data Contributor' no storage. e' assim que o Unity Catalog acessa o
# ADLS Gen2 SEM chave/senha — identidade gerenciada, do jeito enterprise.
# o resource ID deste connector e' usado depois pra criar o STORAGE CREDENTIAL no Databricks.
set -euo pipefail
source "$(dirname "$0")/00_variables.sh"

export AC="ac-medallion-olist"
export ST="stmedallionolist"

az databricks access-connector create \
  --name "$AC" --resource-group "$RG" --location "$LOCATION" \
  --identity-type SystemAssigned --output table

PID=$(az databricks access-connector show --name "$AC" -g "$RG" --query identity.principalId -o tsv)
SID=$(az storage account show --name "$ST" -g "$RG" --query id -o tsv)

# retry: a identidade demora alguns segundos pra propagar no Entra ID
for i in $(seq 1 6); do
  if az role assignment create --assignee-object-id "$PID" --assignee-principal-type ServicePrincipal \
       --role "Storage Blob Data Contributor" --scope "$SID" >/dev/null 2>&1; then
    echo "role atribuido (tentativa $i)"; break
  fi
  echo "propagacao... aguardando 10s"; sleep 10
done
