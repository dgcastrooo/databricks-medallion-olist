#!/usr/bin/env bash
# variaveis comuns do provisionamento — os outros scripts dao `source` aqui.
# uso: source infra/00_variables.sh

# isola a conta pessoal do azure (nao mistura com a conta da empresa)
export AZURE_CONFIG_DIR="$HOME/.azure-pessoal"

export RG="rg-medallion-olist"       # resource group (apagar isso no fim = teardown total)
export LOCATION="eastus2"            # tudo na mesma regiao pra evitar custo de trafego
