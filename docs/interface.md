# Interface MVP (`livethetrader.interface`)

Este módulo adiciona uma interface em terminal para monitoramento do sistema com polling HTTP.

## Funcionalidades

- Tela principal com:
  - ativo (`symbol`)
  - timeframe
  - último sinal
  - confiança
  - status do sistema
- Histórico de sinais (últimos eventos recebidos).
- Métricas básicas:
  - `win_rate`
  - `profit_factor`
  - `drawdown`
  - `trades_total`
- Reconeção automática com backoff exponencial em caso de falha de API.

## Contrato esperado do backend

Endpoint: `GET /api/v1/dashboard`

Exemplo mínimo:

```json
{
  "symbol": "EURUSD",
  "timeframe": "1m",
  "last_signal": "CALL",
  "confidence": 0.74,
  "system_status": "ONLINE",
  "metrics": {
    "win_rate": 0.58,
    "profit_factor": 1.4,
    "drawdown": 0.07,
    "trades_total": 55
  },
  "history": [
    {
      "signal_id": "sig_1",
      "symbol": "EURUSD",
      "timeframe": "1m",
      "direction": "CALL",
      "confidence": 0.74,
      "timestamp_open": "2025-01-01T10:00:00Z"
    }
  ]
}
```

## Execução local

### 1) Rodar interface com backend local embutido (MVP rápido)

```bash
python -m livethetrader.interface.console --local-backend --poll-interval 2
```

### 2) Rodar interface contra backend externo

```bash
python -m livethetrader.interface.console --base-url http://127.0.0.1:8000 --poll-interval 2
```

## Testes da camada de comunicação

```bash
pytest tests/test_interface_communication.py
```
