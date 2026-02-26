# Configuração e Observabilidade

O projeto agora possui um núcleo central de configuração e logging estruturado em JSON para execução local e CI.

## Carregamento de configuração

O carregamento ocorre pelo módulo `livethetrader.config`:

1. Defaults em código (`AppConfig`).
2. Arquivo JSON opcional (`LTT_CONFIG_FILE`).
3. Variáveis de ambiente (sobrescrevem arquivo/default).

## Variáveis de ambiente e defaults

| Chave | Default | Descrição |
|---|---:|---|
| `LTT_CONFIG_FILE` | _vazio_ | Caminho de arquivo JSON com configuração base. |
| `LTT_SYMBOLS` | `EURUSD` | Lista CSV de símbolos monitorados. |
| `LTT_TIMEFRAMES` | `1m,5m,15m` | Lista CSV de timeframes ativos. |
| `LTT_POLL_INTERVAL_SECONDS` | `2.0` | Intervalo de polling da interface. |
| `LTT_MAX_TICKS_PER_RUN` | `54000` | Limite de ticks por execução da API local. |
| `LTT_INTERFACE_HISTORY_LIMIT` | `20` | Quantidade máxima de histórico em memória da interface. |
| `LTT_DASHBOARD_BASE_URL` | `http://127.0.0.1:8000` | Endpoint base para coleta do dashboard. |
| `LTT_PROVIDER_ENDPOINT` | _vazio_ | Endpoint do provedor de mercado (REST/WS). |
| `LTT_CONFIDENCE_MIN` | `0.55` | Threshold mínimo de confiança para aprovação de risco (`RiskManager`). |
| `LTT_RISK_REJECTION_MAX` | `0.45` | Limite de rejeição dura do risco: sinais com confiança `<=` esse valor são bloqueados. |
| `LTT_LOG_LEVEL` | `INFO` | Nível global de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `LTT_LOG_SERVICE_NAME` | `livethetrader` | Nome de serviço incluído no JSON de log. |

## Estrutura de log JSON

Todos os logs padronizados têm os campos-base:

- `timestamp`
- `level`
- `service`
- `logger`
- `event`

Campos adicionais por evento são agregados no mesmo objeto JSON.

Exemplo:

```json
{
  "timestamp": "2026-02-25T12:34:56.123456+00:00",
  "level": "INFO",
  "service": "livethetrader",
  "logger": "livethetrader.api.service",
  "event": "api_run_once_completed",
  "symbol": "EURUSD",
  "direction": "CALL",
  "confidence": 0.71
}
```

## Consistência operacional (local/CI)

- `tests/conftest.py` aplica `configure_logging(...)` no início da sessão de testes.
- Os módulos `api`, `interface`, `ingestion`, `signal_engine` e `backtest` emitem eventos via logger central (`log_event`).

## Semântica dos thresholds de risco

No `RiskManager`, os thresholds são aplicados em duas faixas:

- `confidence <= risk_rejection_max`: bloqueio imediato com motivo `confidence_below_rejection_threshold`.
- `risk_rejection_max < confidence < confidence_min`: bloqueio com motivo `confidence_below_threshold`.
- `confidence >= confidence_min`: risco aprovado (`risk_ok`).
