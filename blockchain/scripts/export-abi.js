// Copies the compiled ABI into the backend so Python and Solidity always agree.
// Run automatically by deploy.js, or manually:  npm run export-abi
const fs = require("fs");
const path = require("path");

function exportAbi() {
  const artifact = path.join(
    __dirname, "..", "artifacts", "contracts", "CertificateRegistry.sol", "CertificateRegistry.json"
  );
  if (!fs.existsSync(artifact)) {
    throw new Error("Artifact not found. Run `npx hardhat compile` first.");
  }
  const { abi } = JSON.parse(fs.readFileSync(artifact, "utf8"));
  const target = path.join(
    __dirname, "..", "..", "backend", "app", "blockchain", "abi", "CertificateRegistry.json"
  );
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify({ contractName: "CertificateRegistry", abi }, null, 2));
  console.log("ABI written to", target);
}

module.exports = { exportAbi };

if (require.main === module) exportAbi();