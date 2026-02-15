# 🛡️ FlakyGuard

**Flaky test detection, quarantine & cost attribution engine.**

Stop burning CI money on meaningless re-runs. FlakyGuard uses statistical flip-rate analysis to find every non-deterministic test, classifies root causes, and shows exactly how much each flaky test costs in dollars.

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Ingest JUnit XML results from multiple CI runs
python flakyguard.py ingest results-run1.xml --run-id ci-1234
python flakyguard.py ingest results-run2.xml --run-id ci-1235
python flakyguard.py ingest results-run3.xml --run-id ci-1236

# Detect flaky tests with cost report
python flakyguard.py detect

# Generate quarantine conftest.py
python flakyguard.py quarantine > conftest_quarantine.py

# Export JSON for CI pipelines
python flakyguard.py detect --output json

# View ingestion stats
python flakyguard.py stats
```

## ✨ Features

- **Statistical Detection** — Flip-rate analysis across historical runs identifies non-deterministic tests
- **7 Root Cause Categories** — timing / ordering / shared state / race condition / resource leak / timezone / float precision
- **Cost Attribution** — Dollar amount per flaky test based on your CI spend rate
- **Quarantine Generation** — Auto-generate `conftest.py` to skip flaky tests without blocking PRs
- **JSON Output** — Pipe into dashboards, Slack bots, JIRA automation
- **Zero Config** — Just feed it JUnit XML, works with pytest/JUnit/Go/Rust test output

## 💰 Pricing

| Feature | Free | Pro $79/mo | Enterprise $499/mo |
|---|---|---|---|
| Flaky detection | ✅ 1 repo | ✅ Unlimited | ✅ Unlimited |
| Root cause analysis | Basic (7 categories) | ✅ Advanced + AI suggestions | ✅ Advanced + auto-fix PRs |
| Cost attribution | ✅ | ✅ | ✅ |
| Quarantine generation | ✅ | ✅ | ✅ |
| CI integrations | Manual XML ingest | GitHub Actions + GitLab CI | All CI + custom webhooks |
| Slack / JIRA alerts | ❌ | ✅ | ✅ |
| Trend dashboard | ❌ | ✅ Web UI | ✅ + PDF executive reports |
| PR gate comments | ❌ | ✅ | ✅ |
| SSO / SAML | ❌ | ❌ | ✅ |
| Multi-repo support | ❌ | Up to 10 repos | Unlimited |
| Support | Community | Email (24h SLA) | Dedicated Slack channel |
| Audit trail / SOC2 | ❌ | ❌ | ✅ |

## 📊 Why Pay?

**The average team wastes $2,000–15,000/month on CI re-runs from flaky tests.**

FlakyGuard Pro pays for itself in week one:

- 🔥 Find the 5% of tests causing 80% of re-runs
- 💰 Show engineering leadership the real dollar burn rate
- 🚀 Quarantine without blocking developer velocity
- 📈 Track flaky trends — prove things are improving (or not)

> *"We cut CI costs by 34% in the first month."* — Series B SaaS, 40 engineers

## 🔧 GitHub Actions Integration

```yaml
- name: Run tests
  run: pytest --junitxml=results.xml || true
- name: FlakyGuard
  run: |
    pip install click rich
    python flakyguard.py ingest results.xml --run-id ${{ github.run_id }}
    python flakyguard.py detect --output json > flaky-report.json
```

## Competitors

BuildPulse ($100+/mo), Trunk Flaky Tests ($150+/mo), Launchable ($300+/mo).
FlakyGuard: open-core CLI, runs locally, no vendor lock-in.

## License

MIT (Free tier) | Commercial license required for Pro/Enterprise features.
