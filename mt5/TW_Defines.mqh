//+------------------------------------------------------------------+
//| TW_Defines.mqh — TradeWizard shared constants & structures       |
//| Requires MT5 Build 2361+ (socket API)                            |
//+------------------------------------------------------------------+
#ifndef TW_DEFINES_MQH
#define TW_DEFINES_MQH

//--- Server settings
#define TW_SERVER_PORT       5000
#define TW_MAX_CONNECTIONS   8
#define TW_RECV_TIMEOUT_MS   3000
#define TW_BUFFER_SIZE       8192

//--- HMAC secret (must match .env MT5_WEBHOOK_SECRET)
#define TW_DEFAULT_SECRET    "tradewizard_secret"

//--- Action identifiers
#define TW_ACTION_OPEN           "OPEN"
#define TW_ACTION_MODIFY_SL      "MODIFY_SL"
#define TW_ACTION_CLOSE_PARTIAL  "CLOSE_PARTIAL"
#define TW_ACTION_CLOSE          "CLOSE"

//--- Trade result codes
#define TW_OK       0
#define TW_ERR_JSON 1
#define TW_ERR_SIGN 2
#define TW_ERR_EXEC 3

//--- Incoming signal structure
struct TWSignal {
   string action;
   string symbol;
   string direction;   // BUY / SELL
   string order_type;  // LIMIT / STOP / MARKET
   double entry_price;
   double stop_loss;
   double take_profit;
   double lot_size;
   string comment;
   string ticket;      // for modify / close actions
   double new_sl;
   double percent;     // for partial close
};

//--- Simple response builder
string TW_ResponseOK(string ticket, string message) {
   return "{\"success\":true,\"ticket\":\"" + ticket +
          "\",\"message\":\"" + message + "\"}";
}

string TW_ResponseError(string message) {
   return "{\"success\":false,\"error\":\"" + message + "\"}";
}

#endif // TW_DEFINES_MQH
