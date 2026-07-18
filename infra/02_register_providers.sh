#!/usr/bin/env bash
# registra os resource providers usados pelo projeto.
# necessario em subscription nova: por padrao quase tudo vem NotRegistered,
# e tentar criar o recurso antes disso falha com o erro enganoso "SubscriptionNotFound".
# registro e' gratuito, por-subscription, feito uma unica vez.
set -euo pipefail
source "$(dirname "$0")/00_variables.sh"

for ns in Microsoft.Storage Microsoft.Databricks Microsoft.Compute Microsoft.Network Microsoft.KeyVault; do
  az provider register --namespace "$ns"
done

# espera o Storage (o primeiro que precisamos) sair de Registering -> Registered
az provider register --namespace Microsoft.Storage --wait
echo "Microsoft.Storage -> $(az provider show --namespace Microsoft.Storage --query registrationState -o tsv)"
