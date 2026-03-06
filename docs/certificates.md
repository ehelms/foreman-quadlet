# Certificate Management

This document describes how certificate generation and management works in foremanctl.

## User Guide

### Certificate Sources

foremanctl supports two certificate sources that determine how certificates are obtained:

**Default Source (`certificate_source: default`)**
- Automatically generates self-signed certificates during deployment
- Creates a complete PKI infrastructure with CA, server, and client certificates
- Recommended for development and testing environments

**Installer Source (`certificate_source: installer`)**
- Uses existing certificates from a previous `foreman-installer` deployment
- Useful for migration scenarios where certificates already exist
- Certificate files must be present at expected foreman-installer paths

### Certificate Key Algorithms

foremanctl supports both RSA and Elliptic Curve (EC) cryptographic algorithms for certificate generation:

**RSA (Default)**
- Traditional and widely compatible
- 4096-bit key size provides strong security
- Recommended for maximum compatibility

**Elliptic Curve (EC)**
- Smaller key sizes with equivalent security (P-384 curve, 192-bit security equivalent)
- Better performance for TLS handshakes
- Recommended for modern deployments

### Usage

#### Using Auto-Generated Certificates (Default)

```bash
# Deploy with auto-generated RSA certificates (default)
foremanctl deploy

# Deploy with Elliptic Curve certificates (P-384)
foremanctl deploy --certificates-key-type=ec

# Deploy with custom RSA key size
foremanctl deploy --certificates-rsa-key-size=2048
```

#### Using Existing Installer Certificates

```bash
# Use certificates from previous foreman-installer
foremanctl deploy --certificate-source=installer
```

### Certificate Locations

After deployment, certificates are available at:

**Default Source:**
- CA Certificate: `/root/certificates/certs/ca.crt`
- Server Certificate: `/root/certificates/certs/<hostname>.crt`
- Client Certificate: `/root/certificates/certs/<hostname>-client.crt`

**Installer Source:**
- CA Certificate: `/root/ssl-build/katello-default-ca.crt`
- Server Certificate: `/root/ssl-build/<hostname>/<hostname>-apache.crt`
- Client Certificate: `/root/ssl-build/<hostname>/<hostname>-foreman-client.crt`

### Current Limitations

- Only supports single hostname (no multiple DNS names)
- Cannot provide custom certificate files during deployment
- Fixed 20-year certificate validity period

---

## Internal Design

### Architecture

The certificate system uses a modular Ansible role-based approach with clear separation between generation, validation, and usage phases.

#### Certificate Role Structure

```
src/roles/certificates/
├── tasks/
│   ├── main.yml          # Entry point - orchestrates CA and certificate generation
│   ├── ca.yml            # CA certificate generation
│   ├── issue.yml         # Host certificate issuance
│   └── generate_key.yml  # Reusable key generation (RSA or EC)
├── defaults/main.yml     # Default configuration variables
└── templates/
    ├── openssl.cnf.j2    # OpenSSL configuration template
    └── serial.j2         # Serial number template
```

#### Certificate Generation Workflow

1. **CA Generation** (when `certificates_ca: true`):
   - Install OpenSSL and create directory structure
   - Generate private key (RSA or EC based on `certificates_key_type`)
   - Create self-signed CA certificate (CN: "Foreman Self-signed CA", 20-year validity)

2. **Host Certificate Issuance** (for each hostname in `certificates_hostnames`):
   - Generate private key using `generate_key.yml` task (RSA or EC)
   - Create certificate signing request (CSR)
   - Sign certificate with CA (includes serverAuth/clientAuth extensions)
   - Generate both server and client certificates per hostname

#### Variable System

Certificate paths are defined in source-specific variable files:

**Default Source (`src/vars/default_certificates.yml`):**
```yaml
ca_certificate: "{{ certificates_ca_directory }}/certs/ca.crt"
server_certificate: "{{ certificates_ca_directory }}/certs/{{ ansible_facts['fqdn'] }}.crt"
client_certificate: "{{ certificates_ca_directory }}/certs/{{ ansible_facts['fqdn'] }}-client.crt"
```

**Installer Source (`src/vars/installer_certificates.yml`):**
```yaml
ca_certificate: "/root/ssl-build/katello-default-ca.crt"
server_certificate: "/root/ssl-build/{{ ansible_facts['fqdn'] }}/{{ ansible_facts['fqdn'] }}-apache.crt"
client_certificate: "/root/ssl-build/{{ ansible_facts['fqdn'] }}/{{ ansible_facts['fqdn'] }}-foreman-client.crt"
```

#### Integration with Deployment

In `src/playbooks/deploy/deploy.yaml`:

1. **Variable Loading**: Loads certificate variables based on `certificate_source`
2. **Certificate Generation**: Runs `certificates` role when `certificate_source == 'default'`
3. **Certificate Validation**: Runs `certificate_checks` role for all sources
4. **Service Configuration**: Passes certificate paths to dependent roles

#### Validation System

The `certificate_checks` role uses `foreman-certificate-check` binary to validate:
- Certificate file existence and readability
- PEM format validation
- Private key and certificate pairing
- Certificate chain integrity

### Technical Specifications

**Certificate Properties:**
- Key Algorithms:
  - RSA: 4096-bit (default), configurable
  - EC: P-384 curve (secp384r1)
- Hash Algorithm: SHA256
- Validity Period: 7300 days (20 years)
- Extensions: serverAuth, clientAuth, nsSGC, msSGC
- Key Usage:
  - RSA: digitalSignature, keyEncipherment
  - EC: digitalSignature, keyAgreement

**Directory Structure:**
```
/root/certificates/
├── certs/           # Public certificates
├── private/         # Private keys and passwords
└── requests/        # Certificate signing requests
```

**OpenSSL Configuration:**
- Custom configuration template supports SAN extensions
- Single DNS entry per certificate: `subjectAltName = DNS:{{ certificates_hostname }}`
- Uses OpenSSL's `req` and `ca` commands for generation and signing