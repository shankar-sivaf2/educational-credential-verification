// Deploys CertificateRegistry to the network given by --network and tells the backend
// where it is.  Usage (node must be running):  npm run deploy
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { exportAbi } = require("./export-abi");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const Registry = await hre.ethers.getContractFactory("CertificateRegistry");
  const registry = await Registry.deploy(deployer.address);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const network = await hre.ethers.provider.getNetwork();

  const abiDir = path.join(__dirname, "..", "..", "backend", "app", "blockchain", "abi");
  fs.mkdirSync(abiDir, { recursive: true });
  fs.writeFileSync(
    path.join(abiDir, "deployment.json"),
    JSON.stringify(
      {
        address,
        chainId: Number(network.chainId),
        deployer: deployer.address,
        deployedAt: new Date().toISOString(),
      },
      null,
      2
    )
  );
  exportAbi();

  console.log("\nCertificateRegistry deployed to:", address);
  console.log("Chain ID:", Number(network.chainId));
  console.log("Deployer (admin + first issuer):", deployer.address);
  console.log("\nThe backend signs with ISSUER_PRIVATE_KEY. For local development that must be");
  console.log("Hardhat account #0, which is the deployer above. Restart the backend if it is running.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});