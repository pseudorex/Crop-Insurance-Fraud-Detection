"""
Pure-Python Cryptographic & MSP Generator for Hyperledger Fabric Network
Generates standard X.509 ECDSA (secp256r1) certificates and Fabric MSP folder structures
for 1 Orderer Organization and 6 Insurer Peer Organizations.
"""

import os
import shutil
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRYPTO_DIR = os.path.join(BASE_DIR, "crypto-config")


def create_key():
    return ec.generate_private_key(ec.SECP256R1())


def save_key_pkcs8(key, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )


def save_cert(cert, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def generate_ca(common_name: str, org_name: str, country: str = "US"):
    key = create_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def generate_node_cert(common_name: str, org_name: str, ca_key, ca_cert, san_dns=None, country="US"):
    key = create_key()
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1825))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=True,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    )
    if san_dns:
        names = [x509.DNSName(dns) for dns in san_dns]
        names.append(x509.DNSName("localhost"))
        builder = builder.add_extension(
            x509.SubjectAlternativeName(names), critical=False
        )

    cert = builder.sign(ca_key, hashes.SHA256())
    return key, cert


def build_msp(msp_path, ca_cert, admin_cert, node_key=None, node_cert=None, tls_ca_cert=None):
    os.makedirs(os.path.join(msp_path, "cacerts"), exist_ok=True)
    os.makedirs(os.path.join(msp_path, "admincerts"), exist_ok=True)
    save_cert(ca_cert, os.path.join(msp_path, "cacerts", "ca.crt"))
    save_cert(admin_cert, os.path.join(msp_path, "admincerts", "admin.crt"))

    if tls_ca_cert:
        os.makedirs(os.path.join(msp_path, "tlscacerts"), exist_ok=True)
        save_cert(tls_ca_cert, os.path.join(msp_path, "tlscacerts", "tlsca.crt"))

    if node_key and node_cert:
        os.makedirs(os.path.join(msp_path, "keystore"), exist_ok=True)
        os.makedirs(os.path.join(msp_path, "signcerts"), exist_ok=True)
        save_key_pkcs8(node_key, os.path.join(msp_path, "keystore", "priv_sk"))
        save_cert(node_cert, os.path.join(msp_path, "signcerts", "cert.pem"))


def generate_all_crypto():
    print("=" * 70)
    print("HYPERLEDGER FABRIC CRYPTOGRAPHIC GENERATOR (Python / X.509 ECDSA)")
    print("=" * 70)

    # 1. ORDERER ORG
    print("[1/7] Generating OrdererOrg (orderer.insurance.com)...")
    orderer_base = os.path.join(CRYPTO_DIR, "ordererOrganizations", "insurance.com")
    ca_key, ca_cert = generate_ca("ca.insurance.com", "OrdererMSP")
    tls_key, tls_cert = generate_ca("tlsca.insurance.com", "OrdererMSP")

    # Orderer CA certs
    save_cert(ca_cert, os.path.join(orderer_base, "ca", "ca.insurance.com-cert.pem"))
    save_cert(tls_cert, os.path.join(orderer_base, "tlsca", "tlsca.insurance.com-cert.pem"))

    # Orderer Admin
    admin_key, admin_cert = generate_node_cert("Admin@insurance.com", "OrdererMSP", ca_key, ca_cert)
    admin_msp = os.path.join(orderer_base, "users", "Admin@insurance.com", "msp")
    build_msp(admin_msp, ca_cert, admin_cert, admin_key, admin_cert, tls_cert)

    # Orderer Node
    orderer_key, orderer_cert = generate_node_cert(
        "orderer.insurance.com", "OrdererMSP", ca_key, ca_cert, ["orderer.insurance.com", "orderer"]
    )
    orderer_tls_key, orderer_tls_cert = generate_node_cert(
        "orderer.insurance.com", "OrdererMSP", tls_key, tls_cert, ["orderer.insurance.com", "orderer"]
    )

    orderer_node_msp = os.path.join(orderer_base, "orderers", "orderer.insurance.com", "msp")
    build_msp(orderer_node_msp, ca_cert, admin_cert, orderer_key, orderer_cert, tls_cert)

    orderer_tls_dir = os.path.join(orderer_base, "orderers", "orderer.insurance.com", "tls")
    save_key_pkcs8(orderer_tls_key, os.path.join(orderer_tls_dir, "server.key"))
    save_cert(orderer_tls_cert, os.path.join(orderer_tls_dir, "server.crt"))
    save_cert(tls_cert, os.path.join(orderer_tls_dir, "ca.crt"))

    # Org-level MSP
    build_msp(os.path.join(orderer_base, "msp"), ca_cert, admin_cert, tls_ca_cert=tls_cert)

    # 2. PEER ORGS (InsurerA to InsurerF)
    orgs = [
        ("InsurerA", "insurera.insurance.com", "InsurerAMSP", 7051),
        ("InsurerB", "insurerb.insurance.com", "InsurerBMSP", 8051),
        ("InsurerC", "insurerc.insurance.com", "InsurerCMSP", 9051),
        ("InsurerD", "insurerd.insurance.com", "InsurerDMSP", 10051),
        ("InsurerE", "insurere.insurance.com", "InsurerEMSP", 11051),
        ("InsurerF", "insurerf.insurance.com", "InsurerFMSP", 12051),
    ]

    for idx, (org_name, domain, msp_id, port) in enumerate(orgs, start=2):
        print(f"[{idx}/7] Generating {org_name} ({domain})...")
        peer_base = os.path.join(CRYPTO_DIR, "peerOrganizations", domain)
        p_ca_key, p_ca_cert = generate_ca(f"ca.{domain}", msp_id)
        p_tls_key, p_tls_cert = generate_ca(f"tlsca.{domain}", msp_id)

        # CA certs
        save_cert(p_ca_cert, os.path.join(peer_base, "ca", f"ca.{domain}-cert.pem"))
        save_cert(p_tls_cert, os.path.join(peer_base, "tlsca", f"tlsca.{domain}-cert.pem"))

        # Org Admin
        p_admin_key, p_admin_cert = generate_node_cert(f"Admin@{domain}", msp_id, p_ca_key, p_ca_cert)
        p_admin_msp = os.path.join(peer_base, "users", f"Admin@{domain}", "msp")
        build_msp(p_admin_msp, p_ca_cert, p_admin_cert, p_admin_key, p_admin_cert, p_tls_cert)

        # Peer Node
        peer_hostname = f"peer0.{domain}"
        peer_key, peer_cert = generate_node_cert(peer_hostname, msp_id, p_ca_key, p_ca_cert, [peer_hostname, f"peer0.{org_name.lower()}"])
        peer_tls_key, peer_tls_cert = generate_node_cert(peer_hostname, msp_id, p_tls_key, p_tls_cert, [peer_hostname, f"peer0.{org_name.lower()}"])

        peer_node_msp = os.path.join(peer_base, "peers", peer_hostname, "msp")
        build_msp(peer_node_msp, p_ca_cert, p_admin_cert, peer_key, peer_cert, p_tls_cert)

        peer_tls_dir = os.path.join(peer_base, "peers", peer_hostname, "tls")
        save_key_pkcs8(peer_tls_key, os.path.join(peer_tls_dir, "server.key"))
        save_cert(peer_tls_cert, os.path.join(peer_tls_dir, "server.crt"))
        save_cert(p_tls_cert, os.path.join(peer_tls_dir, "ca.crt"))

        # Org-level MSP
        build_msp(os.path.join(peer_base, "msp"), p_ca_cert, p_admin_cert, tls_ca_cert=p_tls_cert)

    print("\n[SUCCESS] Generated complete X.509 cryptographic MSP structure for all 6 Insurers + Orderer!")
    print(f"Location: {CRYPTO_DIR}")


if __name__ == "__main__":
    generate_all_crypto()
