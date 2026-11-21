// Gas measurement tests. The limits are loose sanity ceilings, not claims:
// real measurements are printed below and recorded by `npm run gas`.
const { expect } = require("chai");
const { ethers } = require("hardhat");

const key = (s) => ethers.sha256(ethers.toUtf8Bytes("key:" + s));
const commit = (s) => ethers.sha256(ethers.toUtf8Bytes("commit:" + s));

describe("CertificateRegistry gas", () => {
  it("measures registration, revocation and lookup cost", async () => {
    const [admin, issuer] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("CertificateRegistry");
    const registry = await Registry.deploy(admin.address);
    await registry.waitForDeployment();
    await registry.connect(admin).grantRole(await registry.ISSUER_ROLE(), issuer.address);

    const registerReceipt = await (
      await registry.connect(issuer).registerCertificate(key("G1"), commit("G1"))
    ).wait();
    const revokeReceipt = await (await registry.connect(issuer).revokeCertificate(key("G1"))).wait();
    const lookupGas = await registry.getCertificate.estimateGas(key("G1"));

    console.table({
      registerCertificate: { gas: Number(registerReceipt.gasUsed) },
      revokeCertificate: { gas: Number(revokeReceipt.gasUsed) },
      "getCertificate (eth_estimateGas, off-chain call)": { gas: Number(lookupGas) },
    });

    expect(registerReceipt.gasUsed).to.be.lessThan(120000n);
    expect(revokeReceipt.gasUsed).to.be.lessThan(80000n);
  });
});