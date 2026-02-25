# LiveTheTrader

Engine modular de geração de sinais para trading com múltiplos timeframes (1m/5m/15m), com suporte a backtest, interface terminal e dashboard Streamlit.

## Visão geral

O projeto está organizado em módulos independentes para ingestão de ticks, agregação de candles, cálculo de indicadores, estratégia/sinal, risco, backtest, interface e UI.

Principais capacidades:
- Geração de sinal `CALL | PUT | NEUTRO` com confiança e motivo.
- Pipeline de indicadores técnicos (EMA, RSI, MACD, ATR).
- Simulação/backtest com gate de deploy baseado em métricas mínimas.
- Interface terminal para polling de dashboard.
- Dashboard web desacoplado (Streamlit + Plotly).

## Requisitos

- Python **3.11+**
- `pip`

## Instalação

No diretório do projeto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Dependências opcionais:

```bash
# Ferramentas de desenvolvimento (tests/lint/typecheck)
pip install -e .[dev]

# Dashboard Streamlit
pip install -e .[ui]
```

## Estrutura principal

- `src/livethetrader/api/`: fachada de execução de sinal (`TradingSignalService`)
- `src/livethetrader/ingestion/`: fontes de dados (mock e adapter real)
- `src/livethetrader/market_data/`: agregação de ticks em candles multi-timeframe
- `src/livethetrader/indicators/`: cálculo incremental de indicadores
- `src/livethetrader/signal_engine/` e `src/livethetrader/strategy/`: decisão de sinal
- `src/livethetrader/risk/`: política de aprovação/rejeição por risco
- `src/livethetrader/backtest/`: execução de backtest e relatório
- `src/livethetrader/interface/`: cliente de polling + interface terminal
- `src/livethetrader/ui/` e `ui/`: cliente dashboard + app Streamlit
- `docs/`: contratos, configuração e Definition of Done
- `tests/`: testes unitários e de integração local

## Configuração

A configuração padrão está em `src/livethetrader/config/settings.py` e pode ser sobrescrita por arquivo JSON e variáveis de ambiente.

### 1) Arquivo JSON (opcional)

Defina `LTT_CONFIG_FILE` apontando para um JSON:

```bash
export LTT_CONFIG_FILE=/caminho/config.json
```

Exemplo:

```json
{
  "symbols": ["EURUSD"],
  "timeframes": ["1m", "5m", "15m"],
  "poll_interval_seconds": 2.0,
  "limits": {
    "max_ticks_per_run": 54000,
    "interface_history_limit": 20
  },
  "endpoints": {
    "dashboard_base_url": "http://127.0.0.1:8000",
    "provider_endpoint": ""
  },
  "thresholds": {
    "confidence_min": 0.55,
    "risk_rejection_max": 0.45
  },
  "logging": {
    "level": "INFO",
    "service_name": "livethetrader"
  }
}
```

### 2) Variáveis de ambiente suportadas

- `LTT_CONFIG_FILE`
- `LTT_SYMBOLS` (CSV, ex.: `EURUSD,GBPUSD`)
- `LTT_TIMEFRAMES` (CSV, ex.: `1m,5m,15m`)
- `LTT_POLL_INTERVAL_SECONDS`
- `LTT_MAX_TICKS_PER_RUN`
- `LTT_INTERFACE_HISTORY_LIMIT`
- `LTT_DASHBOARD_BASE_URL`
- `LTT_PROVIDER_ENDPOINT`
- `LTT_CONFIDENCE_MIN`
- `LTT_RISK_REJECTION_MAX`
- `LTT_LOG_LEVEL`
- `LTT_LOG_SERVICE_NAME`

## Como usar

### Rodar geração de sinal em código

```python
from livethetrader.api.service import TradingSignalService

service = TradingSignalService(symbol="EURUSD")
payload = service.run_once(tick_count=54000)
print(payload)
```

### Executar interface terminal (com backend local mock)

```bash
python -m livethetrader.interface.console --local-backend --backend-port 8000
```

### Executar interface terminal (consumindo backend existente)

```bash
python -m livethetrader.interface.console --base-url http://127.0.0.1:8000 --poll-interval 2
```

### Rodar dashboard web (Streamlit)

```bash
export DASHBOARD_API_URL="http://127.0.0.1:8000"
streamlit run ui/app.py
```

## Backtest e gate de deploy

O módulo de backtest gera relatório com métricas como:
- `win_rate`
- `profit_factor`
- `expectancy`
- `max_drawdown`

O gate (`StrategyDeploymentGate`) bloqueia deploy quando métricas mínimas não são atendidas.
Consulte:
- `src/livethetrader/backtest/runner.py`
- `src/livethetrader/backtest/deployment_gate.py`
- `docs/dod.md`

## Qualidade e validação

Com dependências de desenvolvimento instaladas:

```bash
pytest
ruff check src tests
mypy src tests
```

Configurações de quality gate estão no `pyproject.toml`:
- cobertura mínima: **70%**
- relatório JUnit: `artifacts/junit.xml`
- cobertura XML: `artifacts/coverage.xml`

## Contratos e documentação

- Contratos de dados: `docs/contracts.md`
- Configuração: `docs/configuration.md`
- Interface/dashboard: `docs/interface.md`
- Definition of Done por papel: `docs/dod.md`
- Checklist DoD/CI: `docs/dod_checklist.md`

## Observações

- O repositório inclui fontes mock e componentes preparados para integração real.
- `ui/README.md` contém detalhes específicos da UI desacoplada.
