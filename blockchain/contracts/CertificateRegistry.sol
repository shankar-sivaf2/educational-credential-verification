// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title CertificateRegistry
/// @notice Tamper-evident registry of educational-certificate commitments.
/// @dev Stores ONLY a salted SHA-256 commitment per certificate, never names,
///      student IDs, grades or documents. The registry does not prove that a
///      degree was truly earned; it records what an authorised issuer submitted
///      and makes later changes to that record (or to the certificate data) detectable.
contract CertificateRegistry is AccessControl {
    /// @notice Accounts allowed to register certificates (institutions).
    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");

    /// @dev Packed into two storage slots:
    ///      slot 0: commitment (32 bytes)
    ///      slot 1: issuer (20) + issuedAt (5) + revoked (1)
    struct Record {
        bytes32 commitment;
        address issuer;
        uint40 issuedAt;
        bool revoked;
    }

    mapping(bytes32 => Record) private _records;

    error ZeroAdmin();
    error ZeroCommitment();
    error AlreadyRegistered(bytes32 certKey);
    error NotRegistered(bytes32 certKey);
    error AlreadyRevoked(bytes32 certKey);
    error NotAllowedToRevoke(bytes32 certKey, address caller);

    event CertificateRegistered(
        bytes32 indexed certKey,
        bytes32 commitment,
        address indexed issuer,
        uint40 issuedAt
    );
    event CertificateRevoked(bytes32 indexed certKey, address indexed revokedBy, uint40 revokedAt);

    /// @param admin Receives DEFAULT_ADMIN_ROLE (manages issuers) and ISSUER_ROLE.
    constructor(address admin) {
        if (admin == address(0)) revert ZeroAdmin();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ISSUER_ROLE, admin);
    }

    /// @notice Register the commitment for a certificate. Callable by issuers only.
    /// @param certKey    SHA-256 based lookup key of the certificate identifier.
    /// @param commitment Salted SHA-256 commitment of the certificate data.
    function registerCertificate(bytes32 certKey, bytes32 commitment) external onlyRole(ISSUER_ROLE) {
        if (commitment == bytes32(0)) revert ZeroCommitment();
        if (_records[certKey].commitment != bytes32(0)) revert AlreadyRegistered(certKey);

        uint40 issuedAt = uint40(block.timestamp);
        _records[certKey] = Record(commitment, msg.sender, issuedAt, false);
        emit CertificateRegistered(certKey, commitment, msg.sender, issuedAt);
    }

    /// @notice Revoke a certificate. Allowed for the issuer that registered it
    ///         (while it still holds ISSUER_ROLE) or for the contract admin.
    function revokeCertificate(bytes32 certKey) external {
        Record storage rec = _records[certKey];
        if (rec.commitment == bytes32(0)) revert NotRegistered(certKey);
        if (rec.revoked) revert AlreadyRevoked(certKey);

        bool isAdmin = hasRole(DEFAULT_ADMIN_ROLE, msg.sender);
        bool isOriginalIssuer = msg.sender == rec.issuer && hasRole(ISSUER_ROLE, msg.sender);
        if (!isAdmin && !isOriginalIssuer) revert NotAllowedToRevoke(certKey, msg.sender);

        rec.revoked = true;
        emit CertificateRevoked(certKey, msg.sender, uint40(block.timestamp));
    }

    /// @notice Public lookup. For an unknown key, exists is false and the rest are zero.
    function getCertificate(bytes32 certKey)
        external
        view
        returns (bool exists, bytes32 commitment, address issuer, uint40 issuedAt, bool revoked)
    {
        Record storage rec = _records[certKey];
        return (rec.commitment != bytes32(0), rec.commitment, rec.issuer, rec.issuedAt, rec.revoked);
    }

    /// @notice True if the account currently holds ISSUER_ROLE.
    function isAuthorizedIssuer(address account) external view returns (bool) {
        return hasRole(ISSUER_ROLE, account);
    }
}