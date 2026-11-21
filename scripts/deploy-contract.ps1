# Deploy the contract to the running local chain (run after start-blockchain.ps1).
# Run again whenever you restart the blockchain: it writes the new address for the backend.
$ErrorActionPreference = "Stop"
Set-Location "$(Split-Path $PSScriptRoot -Parent)\blockchain"
npm run deploy