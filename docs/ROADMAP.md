# SerpentRAG Commercialization Roadmap

## Business Model

**Hybrid:** SaaS (cloud) + Self-Hosted (on-premise license)

**Markets:** RU/CIS + International (parallel launch)

---

## Phase 1: Open Source Foundation (Week 1-2)

- [x] GitHub repository (private)
- [x] CI/CD pipeline (GitHub Actions: lint, test, coverage)
- [x] C4 architecture documentation (PlantUML)
- [x] Professional README with badges
- [x] BSL 1.1 license (source-available, production use requires license)
- [ ] API documentation (OpenAPI/Swagger export)
- [ ] CONTRIBUTING.md + CODE_OF_CONDUCT.md
- [x] Security policy (SECURITY.md)

## Phase 2: Landing Pages (Week 3-4)

**International:**
- [ ] Domain: serpentrag.io (English)
- [ ] Hero section with architecture diagram
- [ ] Feature comparison vs LangChain / LlamaIndex / Haystack
- [ ] Self-hosted vs SaaS pricing toggle
- [ ] Demo request form (Calendly / Cal.com)
- [ ] Blog: "6 RAG Strategies Compared" (SEO)

**RU/CIS:**
- [ ] Domain: serpentrag.ru (Russian)
- [ ] 152-FZ compliance messaging (data stays on your servers)
- [ ] Government / enterprise focus (on-premise)
- [ ] Integration with Russian payment systems

**Tech:** Next.js or Astro static site, Vercel / Cloudflare Pages

## Phase 3: Demo Hosting (Week 5-6)

- [ ] VPS deployment (Hetzner EU + Selectel RU)
- [ ] docker-compose.prod.yml with Traefik (TLS, rate limiting)
- [ ] Pre-loaded demo collection (public datasets)
- [ ] Read-only demo mode (no uploads, rate-limited queries)
- [ ] Interactive demo: query all 6 strategies, view traces, A/B compare
- [ ] Demo video / GIF recordings for landing pages
- [ ] Public Grafana dashboard (read-only)

## Phase 4: Billing Integration (Week 7-10)

**International:**
- [ ] Stripe Checkout + Customer Portal
- [ ] Subscription plans (monthly/annual)
- [ ] Usage-based billing (queries/month, storage GB)
- [ ] Stripe Tax for global compliance

**RU/CIS:**
- [ ] YooKassa / CloudPayments / Tinkoff Acquiring
- [ ] Recurring payments (subscription)
- [ ] Invoice generation for B2B (act + invoice)
- [ ] 54-FZ online cash register integration
- [ ] Payments in RUB

## Phase 5: SaaS Multi-Tenant (Week 11-16)

- [ ] Enable `multi_tenancy_enabled=True`
- [ ] Tenant onboarding flow (signup -> tenant -> API key)
- [ ] Per-tenant resource limits (collections, storage, queries/month)
- [ ] Tenant admin dashboard (usage stats, billing, API keys)
- [ ] Data isolation audit (PostgreSQL RLS, Qdrant collection prefixing)
- [ ] RBAC enforcement (admin / user / readonly roles)
- [ ] Per-user rate limiting (JWT-based throttling)
- [ ] Audit logging (document access, query history, admin actions)
- [ ] Auto-scaling: Kubernetes (Helm chart)
- [ ] CDN for frontend (Cloudflare)
- [ ] Rate limiting per API key

## Phase 6: Enterprise Self-Hosted (Week 17-22)

- [ ] Helm chart for Kubernetes
- [ ] Ansible / Terraform scripts for bare-metal / VM
- [ ] Air-gapped installation (offline Docker images, local Ollama)
- [ ] LDAP / SAML / OIDC SSO integration
- [ ] Audit logging (who queried what, document access log)
- [ ] Enterprise license server (license key validation, expiry)
- [ ] Support portal (Zendesk / Intercom)
- [ ] SLA documentation (99.9% uptime, 4h response time)
- [ ] Encryption at rest (AES-256 field-level for sensitive DB columns)
- [ ] Secret management (HashiCorp Vault / Docker Secrets)
- [ ] Penetration testing (annual, third-party)
- [ ] Security incident response plan
- [ ] Data retention policies (configurable per tenant)
- [ ] Compliance:
  - International: SOC 2 Type II, GDPR
  - RU/CIS: 152-FZ, GOST encryption standards

---

## Security Architecture

> Full details: [SECURITY.md](../SECURITY.md)

| Security Layer | Status | Details |
|----------------|--------|---------|
| Authentication (JWT) | Implemented | HS256, 24h expiry, jti, role claims |
| CORS | Implemented | Restrictive (frontend origin only, no wildcards) |
| TLS / HTTPS | Implemented | Traefik + Let's Encrypt, auto-renewal |
| Container Hardening | Implemented | Non-root, read-only FS, no-new-privileges |
| Security Headers | Implemented | CSP, HSTS, X-Frame-Options, Permissions-Policy |
| Input Validation | Implemented | Pydantic v2, strict bounds, MIME whitelist |
| Network Isolation | Implemented | Internal/public Docker networks |
| DevSecOps CI/CD | Implemented | Bandit, Semgrep, Gitleaks, Trivy, pip-audit, SBOM |
| Rate Limiting (global) | Implemented | Traefik: 50 req/s API, 100 req/s frontend |
| Structured Logging | Implemented | structlog + request_id + OpenTelemetry |
| Multi-Tenancy | Implemented | Optional tenant isolation via JWT claims |
| RBAC | Planned (Q2) | Role-based endpoint authorization |
| Encryption at Rest | Planned (Q2) | AES-256 field-level encryption |
| Audit Logging | Planned (Q2) | Immutable action log (who, what, when) |
| Per-User Rate Limiting | Planned (Q2) | JWT-based throttling |
| Vault Integration | Planned (Q3) | HashiCorp Vault / Docker Secrets |
| Penetration Testing | Planned (Q3) | Annual third-party assessment |
| SOC 2 Type II | Planned (Q4) | Formal compliance certification |
| GOST Encryption | Planned (Q4) | Russian government standards |

### Key Security Differentiators

- **Data Sovereignty:** self-hosted deployment = data never leaves customer infrastructure
- **Air-Gapped Support:** offline Docker images + local Ollama LLM for classified environments
- **No Vendor Lock-In:** bring your own LLM provider (OpenAI, Anthropic, Ollama, any OpenAI-compatible)
- **152-FZ / GDPR:** inherent compliance through self-hosted architecture
- **Defense in Depth:** 11 security layers implemented before first customer

---

## Pricing (Draft)

| Tier | Price | Target | Includes |
|------|-------|--------|----------|
| **Community** | Free | Developers, researchers | Self-hosted, MIT after Change Date, community support |
| **Pro** | $49-99/mo | SMB, startups | SaaS, 3 strategies, 10K queries/mo, email support |
| **Business** | $199-399/mo | Mid-market | SaaS, all 6 strategies, 50K queries/mo, priority support |
| **Enterprise** | $499+/mo | Large orgs | Dedicated instance, SSO, SLA, phone support |
| **Self-Hosted License** | $2,000-5,000/yr | On-premise | All features, air-gapped support, custom SLA |

**RU/CIS pricing:** 30-40% discount from international prices, payment in RUB.

---

## Revenue Targets

| Quarter | Target | Focus |
|---------|--------|-------|
| Q1 2026 | 5 beta users | Demo + feedback loop |
| Q2 2026 | $5K MRR | First paying SaaS customers |
| Q3 2026 | $20K MRR | Enterprise pilots (2-3 companies) |
| Q4 2026 | $50K MRR | Scale SaaS + first enterprise licenses |

---

## Key Metrics to Track

- **MRR** (Monthly Recurring Revenue)
- **CAC** (Customer Acquisition Cost)
- **Churn rate** (monthly)
- **NPS** (Net Promoter Score)
- **Time to first query** (onboarding friction)
- **Queries per user per day** (engagement)
- **Strategy distribution** (which strategies are most popular)
