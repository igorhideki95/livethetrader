# LiveTheTrader UI (Dashboard desacoplado)

Stack escolhida: **Streamlit + Plotly + Pandas**, com cliente HTTP simples para integrar no endpoint
`/api/v1/dashboard` do backend atual, mantendo o frontend desacoplado.

## Estrutura

- `ui/app.py`: aplicação principal do dashboard.
- `src/livethetrader/ui/dashboard_client.py`: cliente HTTP para consultar snapshot e enviar controles operacionais.
- `src/livethetrader/ui/models.py`: contratos de dados e fallback de métricas (quando backend não fornecer completo).

## Funcionalidades implementadas

1. **Tela principal**
   - Status do sistema.
   - Sinal atual.
   - Confiança do sinal.
   - Horário da última atualização/sinal.

2. **Gráfico de candles + indicadores + sinais**
   - Candlestick via Plotly.
   - Linhas para indicadores recebidos no payload.
   - Marcações visuais para `CALL` e `PUT`.

3. **Histórico com filtros/ordenação**
   - Filtro por símbolo e resultado.
   - Ordenação por horário, PnL ou confiança.

4. **Métricas de performance**
   - Win rate.
   - Profit factor.
   - Drawdown.
   - Número de trades.
   - Expectativa.
   - Curva de capital.

5. **Controles operacionais**
   - Iniciar.
   - Pausar.
   - Reiniciar.
   - Recarregar configuração.

## Contrato esperado do backend

### `GET /api/v1/dashboard`

Exemplo:

```json
{
  "status": "running",
  "updated_at": "2026-01-01T10:00:00Z",
  "current_signal": {
    "direction": "CALL",
    "confidence": 0.73,
    "timestamp": "2026-01-01T09:59:59Z"
  },
  "candles": [
    {
      "time": "2026-01-01T09:59:00Z",
      "open": 1.1023,
      "high": 1.1030,
      "low": 1.1018,
      "close": 1.1027,
      "volume": 241,
      "indicators": {
        "ema_9": 1.1025,
        "ema_21": 1.1020,
        "rsi_14": 58.1
      },
      "signal": "CALL"
    }
  ],
  "history": [
    {
      "time": "2026-01-01T09:30:00Z",
      "symbol": "EURUSD",
      "signal": "PUT",
      "confidence": 0.68,
      "result": "WIN",
      "pnl": 12.5
    }
  ],
  "metrics": {
    "win_rate": 0.62,
    "profit_factor": 1.45,
    "drawdown": 35.0,
    "trades": 120,
    "expectancy": 0.8,
    "equity_curve": [
      {"time": "2026-01-01T09:30:00Z", "equity": 12.5}
    ]
  }
}
```

### Controles

A UI envia `POST` para:

- `/api/v1/dashboard/control/start`
- `/api/v1/dashboard/control/pause`
- `/api/v1/dashboard/control/restart`
- `/api/v1/dashboard/control/reload-config`

## Como executar

```bash
pip install streamlit plotly pandas
streamlit run ui/app.py
```

Opcionalmente, para apontar para outro backend:

```bash
export DASHBOARD_API_URL="http://localhost:9000"
streamlit run ui/app.py
```

> Observação: atualização em baixa latência por websocket é opcional e pode ser adicionada sem alterar o
> layout do dashboard.
