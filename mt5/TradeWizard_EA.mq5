//+------------------------------------------------------------------+
//| TradeWizard_EA.mq5                                               |
//| Expert Advisor — receives TradeWizard signals via HTTP webhook   |
//|                                                                  |
//| Requirements:                                                    |
//|   - MetaTrader 5 Build 2361+  (socket API)                       |
//|   - Tools > Options > Expert Advisors > Allow WebRequest         |
//|     (not needed — we are the SERVER, not the client)             |
//|   - Attach to any chart; the EA runs in background               |
//|                                                                  |
//| TradeWizard sends to:  http://<mt5-pc-ip>:5000/webhook           |
//+------------------------------------------------------------------+
#property copyright "TradeWizard"
#property version   "1.00"
#property strict

#include "TW_Defines.mqh"
#include "TW_JsonParser.mqh"
#include "TW_HMAC.mqh"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//--- Inputs
input int    InpPort       = TW_SERVER_PORT;     // Webhook listen port
input string InpSecret     = TW_DEFAULT_SECRET;  // HMAC secret (match .env)
input bool   InpVerifyHMAC = true;               // Verify HMAC signature
input double InpMaxLot     = 1.0;                // Maximum lot size safety cap
input int    InpSlippage   = 10;                 // Max slippage (points)
input bool   InpVerbose    = true;               // Verbose logging

//--- Globals
int      g_server_socket = INVALID_HANDLE;
CTrade   g_trade;
bool     g_running = false;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit() {
   g_trade.SetDeviationInPoints(InpSlippage);
   g_trade.SetAsyncMode(false);

   if (!StartServer()) {
      Alert("TradeWizard EA: Failed to start HTTP server on port ", InpPort);
      return INIT_FAILED;
   }

   EventSetMillisecondTimer(100); // poll every 100ms
   g_running = true;
   Print("TradeWizard EA started — listening on port ", InpPort);
   Comment("TradeWizard EA\nPort: ", InpPort, "\nStatus: RUNNING");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   g_running = false;
   EventKillTimer();
   if (g_server_socket != INVALID_HANDLE) {
      SocketClose(g_server_socket);
      g_server_socket = INVALID_HANDLE;
   }
   Print("TradeWizard EA stopped");
   Comment("");
}

//+------------------------------------------------------------------+
//| Timer — poll for incoming connections                            |
//+------------------------------------------------------------------+
void OnTimer() {
   if (!g_running || g_server_socket == INVALID_HANDLE) return;
   AcceptConnections();
}

void OnTick() {} // required by MQL5

//+------------------------------------------------------------------+
//| Start TCP server                                                 |
//+------------------------------------------------------------------+
bool StartServer() {
   g_server_socket = SocketCreate(SOCKET_DEFAULT);
   if (g_server_socket == INVALID_HANDLE) {
      Print("SocketCreate failed: ", GetLastError());
      return false;
   }
   if (!SocketBind(g_server_socket, "0.0.0.0", InpPort)) {
      Print("SocketBind failed on port ", InpPort, ": ", GetLastError());
      SocketClose(g_server_socket);
      g_server_socket = INVALID_HANDLE;
      return false;
   }
   if (!SocketListen(g_server_socket, TW_MAX_CONNECTIONS)) {
      Print("SocketListen failed: ", GetLastError());
      SocketClose(g_server_socket);
      g_server_socket = INVALID_HANDLE;
      return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Accept and handle incoming connections                           |
//+------------------------------------------------------------------+
void AcceptConnections() {
   string client_ip;
   int client = SocketAccept(g_server_socket, client_ip);
   if (client == INVALID_HANDLE) return;

   if (InpVerbose) Print("Connection from ", client_ip);

   string request = ReceiveRequest(client);
   if (request == "") {
      SocketClose(client);
      return;
   }

   string response_body = HandleRequest(request);
   SendResponse(client, response_body);
   SocketClose(client);
}

//+------------------------------------------------------------------+
//| Receive full HTTP request                                        |
//+------------------------------------------------------------------+
string ReceiveRequest(int client) {
   uchar buf[];
   ArrayResize(buf, TW_BUFFER_SIZE);
   string raw = "";
   int    total = 0;

   uint deadline = GetTickCount() + TW_RECV_TIMEOUT_MS;
   while (GetTickCount() < deadline) {
      int bytes = SocketRead(client, buf, TW_BUFFER_SIZE, 50);
      if (bytes > 0) {
         for (int i = 0; i < bytes; i++)
            raw += ShortToString(buf[i]);
         total += bytes;
         // Check if we have the full request (headers + body)
         if (StringFind(raw, "\r\n\r\n") >= 0) {
            // Read Content-Length to see if body is complete
            int cl = ExtractContentLength(raw);
            int header_end = StringFind(raw, "\r\n\r\n") + 4;
            int body_len   = StringLen(raw) - header_end;
            if (cl <= 0 || body_len >= cl) break;
         }
      }
   }
   return raw;
}

//--- Extract Content-Length from raw HTTP headers
int ExtractContentLength(const string &raw) {
   string needle = "Content-Length:";
   int pos = StringFind(raw, needle);
   if (pos < 0) {
      needle = "content-length:";
      pos = StringFind(raw, needle);
   }
   if (pos < 0) return 0;
   pos += StringLen(needle);
   // skip space
   while (pos < StringLen(raw) && StringGetCharacter(raw, pos) == ' ') pos++;
   string num = "";
   for (int i = pos; i < StringLen(raw); i++) {
      ushort ch = StringGetCharacter(raw, i);
      if (ch >= '0' && ch <= '9') num += ShortToString(ch);
      else break;
   }
   return (int)StringToInteger(num);
}

//--- Extract a header value from raw HTTP request
string ExtractHeader(const string &raw, const string header_name) {
   string needle = header_name + ":";
   int pos = StringFind(raw, needle);
   if (pos < 0) return "";
   pos += StringLen(needle);
   while (pos < StringLen(raw) && StringGetCharacter(raw, pos) == ' ') pos++;
   string val = "";
   for (int i = pos; i < StringLen(raw); i++) {
      ushort ch = StringGetCharacter(raw, i);
      if (ch == '\r' || ch == '\n') break;
      val += ShortToString(ch);
   }
   return StringTrimRight(val);
}

//--- Extract HTTP body (after \r\n\r\n)
string ExtractBody(const string &raw) {
   int pos = StringFind(raw, "\r\n\r\n");
   if (pos < 0) return "";
   return StringSubstr(raw, pos + 4);
}

//+------------------------------------------------------------------+
//| Main request dispatcher                                          |
//+------------------------------------------------------------------+
string HandleRequest(const string &raw) {
   // Only handle POST /webhook
   if (StringFind(raw, "POST") != 0 && StringFind(raw, "POST") < 0)
      return TW_ResponseError("Only POST /webhook is supported");

   string body      = ExtractBody(raw);
   string signature = ExtractHeader(raw, "X-TW-Signature");

   if (InpVerbose) Print("Request body: ", StringSubstr(body, 0, 200));

   // Verify HMAC signature
   if (InpVerifyHMAC && !VerifySignature(body, signature, InpSecret)) {
      Print("HMAC verification failed! Ignoring request.");
      return TW_ResponseError("Invalid signature");
   }

   // Parse signal
   TWSignal sig;
   if (!JsonParseSignal(body, sig)) {
      Print("JSON parse failed for body: ", StringSubstr(body, 0, 100));
      return TW_ResponseError("Invalid JSON");
   }

   if (InpVerbose)
      Print("Signal: action=", sig.action, " symbol=", sig.symbol,
            " dir=", sig.direction, " entry=", sig.entry_price);

   // Dispatch
   if      (sig.action == TW_ACTION_OPEN)          return ExecuteOpen(sig);
   else if (sig.action == TW_ACTION_MODIFY_SL)     return ExecuteModifySL(sig);
   else if (sig.action == TW_ACTION_CLOSE_PARTIAL) return ExecuteClosePartial(sig);
   else if (sig.action == TW_ACTION_CLOSE)         return ExecuteClose(sig);
   else return TW_ResponseError("Unknown action: " + sig.action);
}

//+------------------------------------------------------------------+
//| Send HTTP/1.1 response                                           |
//+------------------------------------------------------------------+
void SendResponse(int client, const string &body) {
   string http = "HTTP/1.1 200 OK\r\n"
                 "Content-Type: application/json\r\n"
                 "Content-Length: " + IntegerToString(StringLen(body)) + "\r\n"
                 "Connection: close\r\n"
                 "\r\n" + body;
   uchar data[];
   StringToCharArray(http, data, 0, StringLen(http));
   SocketSend(client, data, ArraySize(data));
}

//+------------------------------------------------------------------+
//| OPEN — place a new order                                         |
//+------------------------------------------------------------------+
string ExecuteOpen(const TWSignal &sig) {
   if (sig.symbol == "")      return TW_ResponseError("Missing symbol");
   if (sig.lot_size <= 0)     return TW_ResponseError("Invalid lot size");
   if (sig.lot_size > InpMaxLot) return TW_ResponseError("Lot size exceeds safety cap");

   // Normalise symbol (add suffix if needed, e.g. "EURUSDm")
   string symbol = NormaliseSymbol(sig.symbol);
   if (symbol == "")          return TW_ResponseError("Symbol not found: " + sig.symbol);

   double entry  = sig.entry_price;
   double sl     = sig.stop_loss;
   double tp     = sig.take_profit;
   double lots   = NormaliseLots(symbol, sig.lot_size);
   string cmt    = sig.comment != "" ? sig.comment : "TW-ICT";

   ENUM_ORDER_TYPE  order_type;
   ENUM_ORDER_TYPE_FILLING fill = GetFillMode(symbol);

   bool is_buy = (sig.direction == "BUY");

   if (sig.order_type == "MARKET") {
      order_type = is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      bool ok = is_buy
         ? g_trade.Buy (lots, symbol, 0, sl, tp, cmt)
         : g_trade.Sell(lots, symbol, 0, sl, tp, cmt);
      if (!ok) return TW_ResponseError("OrderSend failed: " + IntegerToString(g_trade.ResultRetcode()));
      string ticket = IntegerToString(g_trade.ResultOrder());
      Print("OPEN MARKET OK ticket=", ticket);
      return TW_ResponseOK(ticket, "Market order placed");
   }

   if (sig.order_type == "LIMIT") {
      order_type = is_buy ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   } else { // STOP
      order_type = is_buy ? ORDER_TYPE_BUY_STOP  : ORDER_TYPE_SELL_STOP;
   }

   bool ok = g_trade.OrderOpen(symbol, order_type, lots, 0, entry, sl, tp,
                                ORDER_TIME_GTC, 0, cmt);
   if (!ok) return TW_ResponseError("OrderOpen failed: " + IntegerToString(g_trade.ResultRetcode()));
   string ticket = IntegerToString(g_trade.ResultOrder());
   Print("OPEN PENDING OK ticket=", ticket, " type=", EnumToString(order_type));
   return TW_ResponseOK(ticket, "Pending order placed");
}

//+------------------------------------------------------------------+
//| MODIFY_SL — move stop loss of an open position                   |
//+------------------------------------------------------------------+
string ExecuteModifySL(const TWSignal &sig) {
   if (sig.ticket == "") return TW_ResponseError("Missing ticket");
   ulong ticket = (ulong)StringToInteger(sig.ticket);

   if (!PositionSelectByTicket(ticket))
      return TW_ResponseError("Position not found: " + sig.ticket);

   double new_sl = sig.new_sl;
   double tp     = PositionGetDouble(POSITION_TP);

   if (!g_trade.PositionModify(ticket, new_sl, tp))
      return TW_ResponseError("PositionModify failed: " +
                              IntegerToString(g_trade.ResultRetcode()));

   Print("MODIFY_SL OK ticket=", ticket, " new_sl=", new_sl);
   return TW_ResponseOK(sig.ticket, "Stop loss modified to " + DoubleToString(new_sl, 5));
}

//+------------------------------------------------------------------+
//| CLOSE_PARTIAL — close a percentage of the position              |
//+------------------------------------------------------------------+
string ExecuteClosePartial(const TWSignal &sig) {
   if (sig.ticket == "") return TW_ResponseError("Missing ticket");
   ulong  ticket  = (ulong)StringToInteger(sig.ticket);
   double percent = sig.percent > 0 ? sig.percent : 50.0;

   if (!PositionSelectByTicket(ticket))
      return TW_ResponseError("Position not found: " + sig.ticket);

   string symbol  = PositionGetString(POSITION_SYMBOL);
   double vol     = PositionGetDouble(POSITION_VOLUME);
   double close_vol = NormaliseLots(symbol, vol * percent / 100.0);
   if (close_vol <= 0) return TW_ResponseError("Close volume too small");

   if (!g_trade.PositionClosePartial(ticket, close_vol))
      return TW_ResponseError("PositionClosePartial failed: " +
                              IntegerToString(g_trade.ResultRetcode()));

   Print("CLOSE_PARTIAL OK ticket=", ticket, " percent=", percent, " vol=", close_vol);
   return TW_ResponseOK(sig.ticket, "Closed " + DoubleToString(percent, 0) + "%");
}

//+------------------------------------------------------------------+
//| CLOSE — fully close a position                                   |
//+------------------------------------------------------------------+
string ExecuteClose(const TWSignal &sig) {
   if (sig.ticket == "") {
      // Close by symbol if no ticket given
      if (sig.symbol == "") return TW_ResponseError("Missing ticket or symbol");
      return CloseBySymbol(sig.symbol);
   }

   ulong ticket = (ulong)StringToInteger(sig.ticket);
   if (!PositionSelectByTicket(ticket))
      return TW_ResponseError("Position not found: " + sig.ticket);

   if (!g_trade.PositionClose(ticket))
      return TW_ResponseError("PositionClose failed: " +
                              IntegerToString(g_trade.ResultRetcode()));

   double close_price = g_trade.ResultPrice();
   Print("CLOSE OK ticket=", ticket, " price=", close_price);
   return "{\"success\":true,\"ticket\":\"" + sig.ticket +
          "\",\"close_price\":" + DoubleToString(close_price, 5) +
          ",\"message\":\"Position closed\"}";
}

//--- Close all positions for a symbol
string CloseBySymbol(const string symbol) {
   string norm = NormaliseSymbol(symbol);
   int closed = 0;
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      if (PositionGetSymbol(i) == norm) {
         ulong ticket = PositionGetInteger(POSITION_TICKET);
         if (g_trade.PositionClose(ticket)) closed++;
      }
   }
   return TW_ResponseOK("ALL", "Closed " + IntegerToString(closed) + " positions for " + symbol);
}

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
string NormaliseSymbol(const string raw) {
   // Try exact match first
   if (SymbolSelect(raw, false)) return raw;
   // Try with common suffixes (.z, m, +, pro)
   string suffixes[] = {".z", "m", "+", "pro", ".r", ".stp"};
   for (int i = 0; i < ArraySize(suffixes); i++) {
      string test = raw + suffixes[i];
      if (SymbolSelect(test, false)) return test;
   }
   // Try selecting in Market Watch
   if (SymbolSelect(raw, true)) return raw;
   return "";
}

double NormaliseLots(const string symbol, double lots) {
   double min_lot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double max_lot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if (lot_step <= 0) lot_step = 0.01;
   lots = MathRound(lots / lot_step) * lot_step;
   lots = MathMax(lots, min_lot);
   lots = MathMin(lots, max_lot);
   return NormalizeDouble(lots, 2);
}

ENUM_ORDER_TYPE_FILLING GetFillMode(const string symbol) {
   int filling = (int)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if ((filling & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if ((filling & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}
