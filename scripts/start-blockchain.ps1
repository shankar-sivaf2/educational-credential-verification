# Window 1: local blockchain (keep this window open). Chain resets whenever you restart it.
Set-Location "$(Split-Path $PSScriptRoot -Parent)\blockchain"
npx hardhat node