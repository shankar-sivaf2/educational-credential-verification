// Measures gas over repeated registrations and writes docs/gas-results.json
// Usage:  npm run gas
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

const N = 20;
const key = (s) => hre.ethers.sha256(hre.ethers.toUtf8Bytes("key:" + s));
const commit = (s) => hre.ethers.sha256(hre.ethers.toUtf8Bytes("commit:" + s));

function stats(values) {
  const nums = values.map(Number);
  const sum = nums.reduce((a, b) => a + b, 0);
  return { samples: nums.length, min: Math.min(...nums), max: Math.max(...nums), mean: Math.round(sum / nums.length) };
}

async function main() {
  const [admin, issuer] = await hre.ethers.getSigners();
  const Registry = await hre.ethers.getContractFactory("CertificateRegistry");
  const registry = await Registry.deploy(admin.address);
  const deployReceipt = await registry.deploymentTransaction().wait();
  await registry.connect(admin).grantRole(await registry.ISSUER_ROLE(), issuer.address);

  const registerGas = [];
  const revokeGas = [];
  for (let i = 0; i < N; i++) {
    const r = await (await registry.connect(issuer).registerCertificate(key(i), commit(i))).wait();
    registerGas.push(r.gasUsed);
  }
  for (let i = 0; i < N; i++) {
    const r = await (await registry.connect(issuer).revokeCertificate(key(i))).wait();
    revokeGas.push(r.gasUsed);
  }

  const result = {
    measuredAt: new Date().toISOString(),
    environment: {
      network: "hardhat in-process",
      hardhat: require("hardhat/package.json").version,
      solidity: hre.config.solidity.compilers[0].version,
      optimizerRuns: hre.config.solidity.compilers[0].settings.optimizer.runs,
      node: process.version,
      platform: `${process.platform} ${process.arch}`,
    },
    deployment: { gas: Number(deployReceipt.gasUsed) },
    registerCertificate: stats(registerGas),
    revokeCertificate: stats(revokeGas),
    onChainBytesPerCertificate: 64, // two 32-byte storage slots: commitment + packed issuer/time/flag
  };

  const out = path.join(__dirname, "..", "..", "docs", "gas-results.json");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  console.log("\nSaved to", out);
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});