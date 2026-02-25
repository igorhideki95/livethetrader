# Definition of Done (DoD) por papel

Este documento define os critérios mínimos de conclusão para cada papel (`AI_*.md`).

## Regras gerais de transição

- Cada papel só pode iniciar quando o papel anterior tiver o DoD aprovado.
- **Regra mandatória:** não avançar de etapa sem cumprir integralmente o DoD anterior.
- Toda aprovação deve incluir evidências objetivas (logs, relatórios e resultados de testes/backtests quando aplicável).

---

## 1) AI_Architect (Arquitetura)

**Artefatos esperados**
- Documento arquitetural completo com fluxo de dados e responsabilidades por módulo.
- Estrutura de diretórios proposta e contratos/interfaces principais.
- Base inicial funcional mínima (bootstrap do projeto, config e logging).

**Métricas mínimas de qualidade**
- Arquitetura modular com separação explícita de responsabilidades.
- Inicialização do projeto sem erro crítico.
- Rastreabilidade de decisões técnicas (justificativas registradas).

**Evidências obrigatórias**
- Logs de inicialização do sistema.
- Relatório de arquitetura (`docs/` ou equivalente).
- Checklist de módulos e contratos definidos.

---

## 2) AI_Developer (Implementação)

**Artefatos esperados**
- Implementação funcional dos módulos definidos na arquitetura.
- Integração entre ingestão, processamento, estratégia/sinal e configuração.
- Testes automatizados mínimos para fluxos críticos.

**Métricas mínimas de qualidade**
- Build/execução local sem falhas bloqueantes.
- Cobertura mínima de testes dos fluxos críticos: **>= 70%**.
- Zero erro crítico de lint/tipagem (quando aplicável).

**Evidências obrigatórias**
- Saída de execução de testes automatizados.
- Relatório de lint/tipagem.
- Logs de execução ponta a ponta (pipeline principal).

---

## 3) AI_Revisor (QA/Correção)

**Artefatos esperados**
- Relatório de diagnóstico inicial e correções aplicadas.
- Refatorações de confiabilidade e consistência arquitetural.
- Plano de riscos residuais e recomendações.

**Métricas mínimas de qualidade**
- Nenhum bug crítico conhecido aberto.
- Taxa de testes passando: **100% dos testes obrigatórios**.
- Regressão: zero quebra nos fluxos principais validados.

**Evidências obrigatórias**
- Relatório antes/depois com bugs corrigidos.
- Logs de testes (unitários/integrados) e validação de execução.
- Evidências de performance/estabilidade quando houver otimização.

---

## 4) AI_Strategy (Estratégia de sinais)

**Artefatos esperados**
- Estratégia revisada com regras de entrada/saída/filtro documentadas.
- Backtest comparativo (baseline vs estratégia proposta).
- Relatório com limitações, cenários favoráveis e riscos.

**Métricas mínimas de qualidade**
- Melhoria estatística vs baseline em métrica principal definida (ex.: expectativa, acurácia ajustada, PF).
- **Validação temporal obrigatória (out-of-sample):**
  - Split temporal sem vazamento (treino/validação/teste por ordem cronológica).
  - Resultado OOS não pode degradar mais que **20%** da métrica principal versus validação interna.
- **Limites de overfitting:**
  - Gap absoluto entre desempenho in-sample e out-of-sample <= **15 p.p.** na taxa de acerto (ou métrica equivalente normalizada).
  - Estratégias com performance excepcional apenas in-sample devem ser rejeitadas.
- **Baseline mínimo obrigatório para deploy de estratégia (gate):**
  - `win_rate >= 0.52`
  - `profit_factor >= 1.20`
  - `expectancy >= 0.00`
  - `max_drawdown >= -0.02`
  - Qualquer violação bloqueia deploy até nova rodada de backtest.

**Evidências obrigatórias**
- Relatório de backtest com janelas temporais e parâmetros.
- Logs de execução do backtest e configuração usada.
- Tabela comparativa baseline vs nova estratégia (IS/OOS).

---

## 5) AI_MACHINE_LEARNING (IA/ML)

**Artefatos esperados**
- Pipeline de treinamento, validação temporal e inferência.
- Modelo versionado com configuração e features utilizadas.
- Relatório técnico de desempenho, calibração e monitoramento.

**Métricas mínimas de qualidade**
- **Validação temporal obrigatória (out-of-sample):**
  - Walk-forward ou split temporal equivalente, sem leakage.
  - Resultado OOS com queda máxima de **20%** na métrica principal versus validação.
- **Limites de overfitting:**
  - Diferença entre score de treino e OOS <= **10% relativo** (ou <= **15 p.p.** em métricas percentuais).
  - Treinos que violem esse limite exigem reengenharia de features/modelo.
- Inferência dentro da meta de latência definida para produção/simulação.

**Evidências obrigatórias**
- Relatório de treino com hiperparâmetros, seed e versão do dataset.
- Curvas/métricas de treino, validação e teste OOS.
- Logs de inferência e teste de integração com o motor de sinais.

---

## 6) AI_Interface (UI/Dashboard)

**Artefatos esperados**
- Interface funcional para monitoramento em tempo real.
- Telas de sinais, métricas de performance e status operacional.
- Integração com backend e tratamento básico de erros de exibição.

**Métricas mínimas de qualidade**
- Atualização em tempo real sem travamento perceptível no fluxo principal.
- Erros de UI críticos = 0 em fluxo principal.
- Layout legível e consistente em resolução alvo definida.

**Evidências obrigatórias**
- Capturas de tela/registro visual das telas principais.
- Logs de frontend/backend durante uso do dashboard.
- Checklist de cenários críticos validados (dados, erro, reconexão).

## Checklist operacional

- Consulte `docs/dod_checklist.md` para o checklist de execução com evidências de CI por etapa.
