//+------------------------------------------------------------------+
//| TW_JsonParser.mqh — Lightweight JSON string extractor            |
//| Handles flat JSON objects (no nesting needed for TW signals)     |
//+------------------------------------------------------------------+
#ifndef TW_JSONPARSER_MQH
#define TW_JSONPARSER_MQH

//--- Extract a string value: {"key":"value"}
string JsonGetString(const string &json, const string key) {
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if (pos < 0) return "";
   pos += StringLen(search);
   // skip whitespace and colon
   while (pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' ||
          StringGetCharacter(json, pos) == ':'))
      pos++;
   if (pos >= StringLen(json)) return "";
   bool quoted = (StringGetCharacter(json, pos) == '"');
   if (quoted) pos++;
   string result = "";
   for (int i = pos; i < StringLen(json); i++) {
      ushort ch = StringGetCharacter(json, i);
      if (quoted && ch == '"')  break;
      if (!quoted && (ch == ',' || ch == '}' || ch == '\n' || ch == '\r')) break;
      result += ShortToString(ch);
   }
   return StringTrimRight(StringTrimLeft(result));
}

//--- Extract a numeric value: {"key":1.234}
double JsonGetDouble(const string &json, const string key) {
   string val = JsonGetString(json, key);
   if (val == "") return 0.0;
   return StringToDouble(val);
}

//--- Extract an integer value
long JsonGetLong(const string &json, const string key) {
   string val = JsonGetString(json, key);
   if (val == "") return 0;
   return StringToInteger(val);
}

//--- Parse a TWSignal from JSON body
bool JsonParseSignal(const string &json, TWSignal &sig) {
   sig.action      = JsonGetString(json, "action");
   sig.symbol      = JsonGetString(json, "symbol");
   sig.direction   = JsonGetString(json, "direction");
   sig.order_type  = JsonGetString(json, "order_type");
   sig.entry_price = JsonGetDouble(json, "entry_price");
   sig.stop_loss   = JsonGetDouble(json, "stop_loss");
   sig.take_profit = JsonGetDouble(json, "take_profit");
   sig.lot_size    = JsonGetDouble(json, "lot_size");
   sig.comment     = JsonGetString(json, "comment");
   sig.ticket      = JsonGetString(json, "ticket");
   sig.new_sl      = JsonGetDouble(json, "new_sl");
   sig.percent     = JsonGetDouble(json, "percent");
   return (sig.action != "");
}

#endif // TW_JSONPARSER_MQH
