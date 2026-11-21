const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

const key = (s) => ethers.sha256(ethers.toUtf8Bytes("key:" + s));
const commit = (s) => ethers.sha256(ethers.toUtf8Bytes("commit:" + s));

async function deployFixture() {
  const [admin, issuer, otherIssuer, stranger] = await ethers.getSigners();
  const Registry = await ethers.getContractFactory("CertificateRegistry");
  const registry = await Registry.deploy(admin.address);
  await registry.waitForDeployment();

  const ISSUER_ROLE = await registry.ISSUER_ROLE();
  const ADMIN_ROLE = await registry.DEFAULT_ADMIN_ROLE();
  await registry.connect(admin).grantRole(ISSUER_ROLE, issuer.address);
  await registry.connect(admin).grantRole(ISSUER_ROLE, otherIssuer.address);

  return { registry, admin, issuer, otherIssuer, stranger, ISSUER_ROLE, ADMIN_ROLE };
}

describe("CertificateRegistry", () => {
  describe("deployment and roles", () => {
    it("gives the deployer both admin and issuer roles", async () => {
      const { registry, admin, ISSUER_ROLE, ADMIN_ROLE } = await loadFixture(deployFixture);
      expect(await registry.hasRole(ADMIN_ROLE, admin.address)).to.equal(true);
      expect(await registry.hasRole(ISSUER_ROLE, admin.address)).to.equal(true);
    });

    it("does not give roles to strangers", async () => {
      const { registry, stranger } = await loadFixture(deployFixture);
      expect(await registry.isAuthorizedIssuer(stranger.address)).to.equal(false);
    });

    it("rejects a zero admin address", async () => {
      const { registry } = await loadFixture(deployFixture);
      const Factory = await ethers.getContractFactory("CertificateRegistry");
      await expect(Factory.deploy(ethers.ZeroAddress)).to.be.revertedWithCustomError(
        registry,
        "ZeroAdmin"
      );
    });

    it("lets only the admin grant issuer roles", async () => {
      const { registry, stranger, ISSUER_ROLE, ADMIN_ROLE } = await loadFixture(deployFixture);
      await expect(registry.connect(stranger).grantRole(ISSUER_ROLE, stranger.address))
        .to.be.revertedWithCustomError(registry, "AccessControlUnauthorizedAccount")
        .withArgs(stranger.address, ADMIN_ROLE);
    });
  });

  describe("registration", () => {
    it("registers a commitment, emits an event and stores the record", async () => {
      const { registry, issuer } = await loadFixture(deployFixture);
      const k = key("A1");
      const c = commit("A1");

      await expect(registry.connect(issuer).registerCertificate(k, c))
        .to.emit(registry, "CertificateRegistered")
        .withArgs(k, c, issuer.address, anyValue);

      const rec = await registry.getCertificate(k);
      expect(rec.exists).to.equal(true);
      expect(rec.commitment).to.equal(c);
      expect(rec.issuer).to.equal(issuer.address);
      expect(rec.issuedAt).to.be.greaterThan(0n);
      expect(rec.revoked).to.equal(false);
    });

    it("rejects a duplicate registration", async () => {
      const { registry, issuer, otherIssuer } = await loadFixture(deployFixture);
      const k = key("A1");
      await registry.connect(issuer).registerCertificate(k, commit("A1"));
      await expect(registry.connect(issuer).registerCertificate(k, commit("A1")))
        .to.be.revertedWithCustomError(registry, "AlreadyRegistered")
        .withArgs(k);
      // another issuer cannot overwrite it either
      await expect(registry.connect(otherIssuer).registerCertificate(k, commit("evil")))
        .to.be.revertedWithCustomError(registry, "AlreadyRegistered")
        .withArgs(k);
    });

    it("rejects a zero commitment", async () => {
      const { registry, issuer } = await loadFixture(deployFixture);
      await expect(
        registry.connect(issuer).registerCertificate(key("A1"), ethers.ZeroHash)
      ).to.be.revertedWithCustomError(registry, "ZeroCommitment");
    });

    it("rejects registration by a non-issuer", async () => {
      const { registry, stranger, ISSUER_ROLE } = await loadFixture(deployFixture);
      await expect(registry.connect(stranger).registerCertificate(key("A1"), commit("A1")))
        .to.be.revertedWithCustomError(registry, "AccessControlUnauthorizedAccount")
        .withArgs(stranger.address, ISSUER_ROLE);
    });

    it("reports an unknown certificate as not existing", async () => {
      const { registry } = await loadFixture(deployFixture);
      const rec = await registry.getCertificate(key("nope"));
      expect(rec.exists).to.equal(false);
      expect(rec.commitment).to.equal(ethers.ZeroHash);
      expect(rec.revoked).to.equal(false);
    });
  });

  describe("revocation", () => {
    it("lets the issuer revoke its own certificate", async () => {
      const { registry, issuer } = await loadFixture(deployFixture);
      const k = key("A1");
      await registry.connect(issuer).registerCertificate(k, commit("A1"));

      await expect(registry.connect(issuer).revokeCertificate(k))
        .to.emit(registry, "CertificateRevoked")
        .withArgs(k, issuer.address, anyValue);

      const rec = await registry.getCertificate(k);
      expect(rec.exists).to.equal(true); // the record is kept for audit
      expect(rec.revoked).to.equal(true);
      expect(rec.commitment).to.equal(commit("A1"));
    });

    it("rejects revoking twice", async () => {
      const { registry, issuer } = await loadFixture(deployFixture);
      const k = key("A1");
      await registry.connect(issuer).registerCertificate(k, commit("A1"));
      await registry.connect(issuer).revokeCertificate(k);
      await expect(registry.connect(issuer).revokeCertificate(k))
        .to.be.revertedWithCustomError(registry, "AlreadyRevoked")
        .withArgs(k);
    });

    it("rejects revoking an unknown certificate", async () => {
      const { registry, issuer } = await loadFixture(deployFixture);
      await expect(registry.connect(issuer).revokeCertificate(key("nope")))
        .to.be.revertedWithCustomError(registry, "NotRegistered")
        .withArgs(key("nope"));
    });

    it("does not let another issuer or a stranger revoke", async () => {
      const { registry, issuer, otherIssuer, stranger } = await loadFixture(deployFixture);
      const k = key("A1");
      await registry.connect(issuer).registerCertificate(k, commit("A1"));

      await expect(registry.connect(otherIssuer).revokeCertificate(k))
        .to.be.revertedWithCustomError(registry, "NotAllowedToRevoke")
        .withArgs(k, otherIssuer.address);
      await expect(registry.connect(stranger).revokeCertificate(k))
        .to.be.revertedWithCustomError(registry, "NotAllowedToRevoke")
        .withArgs(k, stranger.address);
    });

    it("lets the admin revoke any certificate", async () => {
      const { registry, admin, issuer } = await loadFixture(deployFixture);
      const k = key("A1");
      await registry.connect(issuer).registerCertificate(k, commit("A1"));
      await registry.connect(admin).revokeCertificate(k);
      expect((await registry.getCertificate(k)).revoked).to.equal(true);
    });
  });

  describe("removing an issuer", () => {
    it("makes the account unauthorised and blocks new registrations", async () => {
      const { registry, admin, issuer, ISSUER_ROLE } = await loadFixture(deployFixture);
      const k = key("A1");
      await registry.connect(issuer).registerCertificate(k, commit("A1"));

      await registry.connect(admin).revokeRole(ISSUER_ROLE, issuer.address);
      expect(await registry.isAuthorizedIssuer(issuer.address)).to.equal(false);

      await expect(registry.connect(issuer).registerCertificate(key("A2"), commit("A2")))
        .to.be.revertedWithCustomError(registry, "AccessControlUnauthorizedAccount")
        .withArgs(issuer.address, ISSUER_ROLE);

      // the removed issuer can no longer revoke, but the admin still can
      await expect(registry.connect(issuer).revokeCertificate(k))
        .to.be.revertedWithCustomError(registry, "NotAllowedToRevoke")
        .withArgs(k, issuer.address);
      await registry.connect(admin).revokeCertificate(k);

      // the old record still names its original issuer, so verifiers can see it is now unauthorised
      const rec = await registry.getCertificate(k);
      expect(rec.issuer).to.equal(issuer.address);
    });
  });
});