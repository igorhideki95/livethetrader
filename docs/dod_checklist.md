# Checklist de Definition of Done (DoD) com evidências

Este checklist operacionaliza o DoD em etapas verificáveis com evidências publicadas pelo pipeline de CI.

## 1) Execução e cobertura de testes

- [ ] Testes executados de forma padronizada com `pytest`.
- [ ] Cobertura publicada em `artifacts/coverage.xml`.
- [ ] Meta mínima para fluxos críticos validada no CI: **>= 70%** (`--cov-fail-under=70`).
- [ ] Resultado dos testes publicado em `artifacts/test.log` e `artifacts/junit.xml`.

## 2) Qualidade estática (lint + tipagem)

- [ ] Lint executado com `ruff check src tests`.
- [ ] Tipagem executada com `mypy src tests`.
- [ ] Pipeline falha em erro crítico de lint ou tipagem.
- [ ] Evidências publicadas em `artifacts/lint.log` e `artifacts/typecheck.log`.

## 3) Evidências de execução

- [ ] Logs de teste, lint e tipagem anexados como artifact da execução de CI.
- [ ] Relatórios estruturados (`coverage.xml` e `junit.xml`) anexados como artifact da execução de CI.
- [ ] Nome do artifact esperado no GitHub Actions: `ci-evidence-<run_id>`.

## 4) Gate para merge

- [ ] Workflow obrigatório para PR na branch `main`: job `quality-gates` em `.github/workflows/ci.yml`.
- [ ] Merge permitido apenas com pipeline verde (status check obrigatório configurado no repositório para `CI / quality-gates`).

> Observação: a exigência de status check obrigatório é aplicada nas configurações de proteção de branch do GitHub.
