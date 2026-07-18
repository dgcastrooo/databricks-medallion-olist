#!/usr/bin/env bash
# cria o resource group — o container de todos os recursos do projeto.
# apagar ele no fim (az group delete) derruba tudo de uma vez = teardown total.
set -euo pipefail
source "$(dirname "$0")/00_variables.sh"

az group create --name "$RG" --location "$LOCATION" --output table
