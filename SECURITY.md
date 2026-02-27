# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x (current) | Yes |
| < 0.1 | No |

## Reporting Vulnerabilities

We take security seriously. If you discover a vulnerability, please report it responsibly.

**Contact:** [serpentrag@proton.me](mailto:serpentrag@proton.me)

**Process:**
1. Email us with a description of the vulnerability
2. Include steps to reproduce, impact assessment, and any proof of concept
3. Do **not** open a public GitHub issue for security vulnerabilities

**Response SLA:**

| Severity | Acknowledge | Triage | Fix |
|----------|-------------|--------|-----|
| Critical (RCE, auth bypass, data leak) | 24 hours | 48 hours | 7 days |
| High (privilege escalation, injection) | 48 hours | 7 days | 14 days |
| Medium (information disclosure, CSRF) | 48 hours | 14 days | 30 days |
| Low (misconfiguration, best practices) | 7 days | 30 days | Next release |

**Safe Harbor:** We will not pursue legal action against researchers who report vulnerabilities in good faith, follow responsible disclosure, and do not access or modify other users' data.

---

## Security Architecture

### Authentication & Access Control

- **JWT tokens** with HS256 signing, configurable expiration (default 24h)
- **Token claims:** `sub` (user ID), `role`, `exp` (expiry), `jti` (unique token ID for revocation)
- **Multi-tenancy:** optional tenant isolation via `tenant_id` in JWT claims (opt-in)
- **Trusted Host middleware:** validates Host header in production to prevent host header injection
- **CORS:** restrictive policy, only allows configured frontend origin (no wildcards)

### Data Protection

| Layer | Mechanism | Status |
|-------|-----------|--------|
| **In Transit** | TLS 1.2+ via Traefik + Let's Encrypt (auto-renewal) | Implemented |
| **Self-Hosted** | Data never leaves customer infrastructure | By design |
| **SQL Injection** | SQLAlchemy ORM with parameterized queries (no raw SQL) | Implemented |
| **Code Execution** | No `eval()`, `exec()`, `pickle` — safe deserialization only | Implemented |
| **Path Traversal** | UUID-based file storage, filenames stored as metadata only | Implemented |
| **Input Validation** | Pydantic v2 schemas with strict bounds (query length, top_k, temperature) | Implemented |
| **File Uploads** | MIME type whitelist (PDF, DOCX, TXT, CSV, JSON), configurable size limit | Implemented |
| **At Rest** | Field-level encryption for sensitive columns | Planned (Q2 2026) |

### Container Security

All production containers enforce defense-in-depth:

- **Non-root users:** `serpent` (backend), `nginx` (frontend) — no container runs as root
- **Read-only root filesystem:** `read_only: true` prevents runtime file modification
- **Privilege escalation prevention:** `security_opt: no-new-privileges:true`
- **Multi-stage builds:** builder stage discarded, production image contains only runtime
- **Resource limits:** CPU and memory caps on all containers
- **Network isolation:** internal network (databases, worker) separated from public network (frontend, API)
- **Ephemeral temp storage:** `tmpfs: /tmp` for transient data only

### Frontend Security Headers

| Header | Value | Protection |
|--------|-------|------------|
| Content-Security-Policy | Restrictive (self-hosted sources only) | XSS, injection |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | Protocol downgrade |
| X-Frame-Options | DENY | Clickjacking |
| X-Content-Type-Options | nosniff | MIME sniffing |
| X-XSS-Protection | 1; mode=block | Reflected XSS |
| Referrer-Policy | strict-origin-when-cross-origin | Information leakage |
| Permissions-Policy | camera=(), microphone=(), geolocation=() | Feature abuse |

### DevSecOps Pipeline

Automated security scanning runs on every push and pull request:

```
Push/PR → Lint → SAST → Secrets → Dependencies → Tests → Container Scan → Deploy
```

| Tool | Purpose | Stage |
|------|---------|-------|
| **Bandit** | Python SAST (static analysis) | CI |
| **Semgrep** | Multi-language SAST (OWASP Top 10, secrets, Docker) | CI |
| **Gitleaks** | Secret scanning (API keys, passwords, tokens) | CI |
| **pip-audit** | Python dependency CVE scanning | CI |
| **npm audit** | JavaScript dependency CVE scanning | CI |
| **Trivy** | Container image vulnerability scanning (CRITICAL, HIGH) | CI |
| **SBOM** | Software Bill of Materials generation (SPDX format) | CI |
| **pytest** | 175+ tests, 80%+ code coverage | CI |

### Infrastructure Security

- **Rate limiting:** Traefik middleware — 50 req/s (API), 100 req/s (frontend) with burst protection
- **Structured logging:** JSON format via structlog, unique `X-Request-ID` per request
- **Observability:** OpenTelemetry distributed tracing + Prometheus metrics + Grafana dashboards
- **Health monitoring:** real connectivity checks for PostgreSQL, Redis, Qdrant, and Neo4j
- **Dotfile blocking:** nginx returns 404 for `/.env`, `/.git`, etc.
- **Swagger/ReDoc:** disabled in production (no API schema exposure)

---

## Compliance Roadmap

### International
- **GDPR:** self-hosted deployment ensures data residency control; no vendor data processing
- **SOC 2 Type II:** planned (Q4 2026) — audit logging, access controls, encryption at rest

### RU/CIS
- **152-FZ:** self-hosted on customer infrastructure ensures personal data stays in Russia
- **GOST encryption:** planned for enterprise tier (government sector requirements)

### Self-Hosted Advantage
SerpentRAG's self-hosted architecture provides inherent compliance benefits:
- Data never leaves customer infrastructure
- Air-gapped deployment supported (offline Docker images + local Ollama LLM)
- Customer controls all encryption keys
- No third-party data processing agreements required
- Compatible with classified and regulated environments

---

## Security Roadmap

| Feature | Target | Description |
|---------|--------|-------------|
| RBAC enforcement | Q2 2026 | Role-based endpoint access (admin, user, readonly) |
| Encryption at rest | Q2 2026 | AES-256 field-level encryption for sensitive database columns |
| Audit logging | Q2 2026 | Immutable log of document access, queries, admin actions |
| Per-user rate limiting | Q2 2026 | JWT-based throttling to prevent single-user abuse |
| Secret rotation | Q3 2026 | Automated JWT secret and API key rotation workflow |
| Vault integration | Q3 2026 | HashiCorp Vault / Docker Secrets for credential management |
| Penetration testing | Q3 2026 | Annual third-party security assessment |
| SOC 2 Type II | Q4 2026 | Formal compliance certification |
| GOST encryption | Q4 2026 | Russian government encryption standards support |

---

## Dependency Management

- Python dependencies: `requirements.txt` with `pip-audit` scanning in CI
- JavaScript dependencies: `package.json` with `npm audit` scanning in CI
- Container base images: `python:3.12-slim` and `nginx:alpine` (minimal attack surface)
- Automated CVE alerts via GitHub Dependabot (planned)
