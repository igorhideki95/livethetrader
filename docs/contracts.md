# Contratos de Dados (Schema de Integração)

Este documento define os contratos canônicos entre módulos para payloads de mercado, IA, sinais e backtest.

## Regras Gerais

- Todos os payloads **devem** incluir `schema_version` no formato semântico `MAJOR.MINOR.PATCH` (ex.: `1.0.0`).
- Todos os timestamps são obrigatoriamente em **UTC** e em formato ISO-8601 com sufixo `Z`.
- Campos com horário devem usar nomes explícitos (`timestamp_open`, `timestamp_close`, `timestamp_event`, etc.).
- `symbol` deve seguir padrão do provedor (ex.: `EURUSD`, `BTCUSDT`).
- `timeframe` deve usar valores normalizados: `TICK`, `1m`, `5m`, `15m`, `1h`, `1d`.
- Campos monetários e métricas numéricas devem ser serializados como `number` JSON.

## Versionamento (`schema_version`)

- **PATCH** (`1.0.x`): correções sem mudança estrutural; compatível.
- **MINOR** (`1.x.0`): adição de campos opcionais; retrocompatível.
- **MAJOR** (`x.0.0`): mudança incompatível (remoção/renomeação/tipo).
- Consumidores devem rejeitar payload com `MAJOR` não suportada.
- Em migrações, produtores podem emitir versões em paralelo por janela controlada.

---

## 1) Tick

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `schema_version` | `string` | Versão do contrato (SemVer). |
| `symbol` | `string` | Ativo negociado. |
| `timeframe` | `string` | Deve ser `TICK` para eventos de tick. |
| `timestamp_open` | `string (UTC ISO-8601)` | Abertura lógica do evento (igual ao close em tick). |
| `timestamp_close` | `string (UTC ISO-8601)` | Fechamento lógico do evento. |
| `bid` | `number` | Melhor preço de compra. |
| `ask` | `number` | Melhor preço de venda. |
| `last` | `number` | Último preço negociado/referência. |
| `volume` | `number` | Volume no evento (quando disponível). |

### Exemplo JSON

```json
{
  "schema_version": "1.0.0",
  "symbol": "EURUSD",
  "timeframe": "TICK",
  "timestamp_open": "2026-01-15T12:34:56.120Z",
  "timestamp_close": "2026-01-15T12:34:56.120Z",
  "bid": 1.08421,
  "ask": 1.08424,
  "last": 1.08423,
  "volume": 1023
}
```

---

## 2) Candle

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `schema_version` | `string` | Versão do contrato (SemVer). |
| `symbol` | `string` | Ativo negociado. |
| `timeframe` | `string` | Ex.: `1m`, `5m`, `15m`. |
| `timestamp_open` | `string (UTC ISO-8601)` | Início da vela em UTC. |
| `timestamp_close` | `string (UTC ISO-8601)` | Fechamento da vela em UTC. |
| `open` | `number` | Preço de abertura. |
| `high` | `number` | Máxima do período. |
| `low` | `number` | Mínima do período. |
| `close` | `number` | Preço de fechamento. |
| `volume` | `number` | Volume agregado no período. |

### Exemplo JSON

```json
{
  "schema_version": "1.0.0",
  "symbol": "EURUSD",
  "timeframe": "1m",
  "timestamp_open": "2026-01-15T12:34:00Z",
  "timestamp_close": "2026-01-15T12:34:59.999Z",
  "open": 1.0841,
  "high": 1.0845,
  "low": 1.0839,
  "close": 1.0843,
  "volume": 24891
}
```

---

## 3) FeatureVector

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `schema_version` | `string` | Versão do contrato (SemVer). |
| `symbol` | `string` | Ativo de referência. |
| `timeframe` | `string` | Timeframe da janela principal da feature. |
| `timestamp_open` | `string (UTC ISO-8601)` | Início da janela de cálculo. |
| `timestamp_close` | `string (UTC ISO-8601)` | Fim da janela de cálculo. |
| `features` | `object<string, number>` | Dicionário de features numéricas. |
| `feature_set_id` | `string` | Identificador do conjunto de features. |
| `label_horizon` | `string` | Horizonte de previsão (ex.: `5m`). |

### Exemplo JSON

```json
{
  "schema_version": "1.0.0",
  "symbol": "EURUSD",
  "timeframe": "1m",
  "timestamp_open": "2026-01-15T12:30:00Z",
  "timestamp_close": "2026-01-15T12:34:59.999Z",
  "features": {
    "rsi_14": 61.3,
    "ema_9": 1.08418,
    "ema_21": 1.08402,
    "atr_14": 0.00042,
    "returns_1": 0.00011
  },
  "feature_set_id": "core_v1",
  "label_horizon": "5m"
}
```

---

## 4) Signal

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `schema_version` | `string` | Versão do contrato (SemVer). |
| `signal_id` | `string` | Identificador único do sinal. |
| `symbol` | `string` | Ativo do sinal. |
| `timeframe` | `string` | Timeframe operacional da decisão. |
| `timestamp_open` | `string (UTC ISO-8601)` | Instante de abertura/entrada do sinal. |
| `timestamp_close` | `string (UTC ISO-8601)` | Instante de fechamento esperado do sinal. |
| `direction` | `string` | `CALL`, `PUT` ou `NEUTRO`. |
| `confidence` | `number` | Confiança em `[0,1]`. |
| `expiry` | `string` | Duração até expiração (ex.: `5m`). |
| `reason_codes` | `array<string>` | Evidências/filtros usados na decisão. |

### Exemplo JSON

```json
{
  "schema_version": "1.0.0",
  "signal_id": "sig_20260115_123500_eurusd_1m",
  "symbol": "EURUSD",
  "timeframe": "1m",
  "timestamp_open": "2026-01-15T12:35:00Z",
  "timestamp_close": "2026-01-15T12:39:59.999Z",
  "direction": "CALL",
  "confidence": 0.78,
  "expiry": "5m",
  "reason_codes": ["trend_up", "rsi_recovery", "volatility_ok"]
}
```

---

## 5) TradeOutcome

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `schema_version` | `string` | Versão do contrato (SemVer). |
| `trade_id` | `string` | Identificador da execução/ordem. |
| `signal_id` | `string` | Referência do sinal que originou a operação. |
| `symbol` | `string` | Ativo negociado. |
| `timeframe` | `string` | Timeframe da estratégia. |
| `timestamp_open` | `string (UTC ISO-8601)` | Abertura da operação em UTC. |
| `timestamp_close` | `string (UTC ISO-8601)` | Fechamento/liquidação em UTC. |
| `entry_price` | `number` | Preço de entrada. |
| `exit_price` | `number` | Preço de saída/liquidação. |
| `direction` | `string` | `CALL` ou `PUT`. |
| `confidence` | `number` | Confiança original do sinal em `[0,1]`. |
| `expiry` | `string` | Expiração usada na operação (ex.: `5m`). |
| `result` | `string` | `WIN`, `LOSS` ou `DRAW`. |
| `pnl` | `number` | Resultado financeiro líquido. |

### Exemplo JSON

```json
{
  "schema_version": "1.0.0",
  "trade_id": "trd_20260115_123500_001",
  "signal_id": "sig_20260115_123500_eurusd_1m",
  "symbol": "EURUSD",
  "timeframe": "1m",
  "timestamp_open": "2026-01-15T12:35:00Z",
  "timestamp_close": "2026-01-15T12:39:59.999Z",
  "entry_price": 1.0843,
  "exit_price": 1.0846,
  "direction": "CALL",
  "confidence": 0.78,
  "expiry": "5m",
  "result": "WIN",
  "pnl": 85.0
}
```

---

## 6) BacktestReport

### Campos obrigatórios

| Campo | Tipo | Descrição |
|---|---|---|
| `schema_version` | `string` | Versão do contrato (SemVer). |
| `report_id` | `string` | Identificador único do relatório. |
| `symbol` | `string` | Ativo avaliado. |
| `timeframe` | `string` | Timeframe principal avaliado. |
| `timestamp_open` | `string (UTC ISO-8601)` | Início do período analisado em UTC. |
| `timestamp_close` | `string (UTC ISO-8601)` | Fim do período analisado em UTC. |
| `strategy_name` | `string` | Nome/versão da estratégia. |
| `trades_total` | `integer` | Número total de operações. |
| `win_rate` | `number` | Taxa de acerto (`0` a `1`). |
| `net_pnl` | `number` | Resultado líquido consolidado. |
| `max_drawdown` | `number` | Drawdown máximo no período. |
| `sharpe` | `number` | Índice de Sharpe (quando aplicável). |
| `profit_factor` | `number` | Razão lucro bruto / perda bruta. |
| `expectancy` | `number` | Valor esperado por trade. |
| `temporal_windows` | `array` | Resultados por janela temporal (sem leakage). |
| `comparison_by_asset_timeframe` | `object` | Comparativo por ativo/timeframe. |
| `comparison_by_market_regime` | `object` | Comparativo por regime (`bull`, `bear`, `sideways`). |
| `report_version` | `string` | Versão do relatório de backtest. |
| `report_path` | `string` | Caminho do arquivo `reports/backtest_*.json` gerado. |

### Exemplo JSON

```json
{
  "schema_version": "1.0.0",
  "report_id": "bt_20260115_eurusd_1m_v3",
  "symbol": "EURUSD",
  "timeframe": "1m",
  "timestamp_open": "2025-12-01T00:00:00Z",
  "timestamp_close": "2025-12-31T23:59:59.999Z",
  "strategy_name": "mtf_probabilistic_v3",
  "report_version": "1.0.0",
  "trades_total": 428,
  "win_rate": 0.61,
  "net_pnl": 1240.5,
  "max_drawdown": -310.2,
  "sharpe": 1.42,
  "profit_factor": 1.48,
  "expectancy": 2.89,
  "temporal_windows": [
    {"name": "train", "win_rate": 0.63},
    {"name": "validation", "win_rate": 0.59},
    {"name": "oos", "win_rate": 0.57}
  ],
  "comparison_by_asset_timeframe": {"EURUSD:1m": {"win_rate": 0.61}},
  "comparison_by_market_regime": {"bull": {"win_rate": 0.64}, "bear": {"win_rate": 0.56}, "sideways": {"win_rate": 0.53}},
  "report_path": "reports/backtest_20260115_235959_bt_20260115_eurusd_1m_v3.json"
}
```
