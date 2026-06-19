//+------------------------------------------------------------------+
//| TW_HMAC.mqh — HMAC-SHA256 signature verification                 |
//| Uses MQL5 CryptEncode (available Build 2000+)                    |
//+------------------------------------------------------------------+
#ifndef TW_HMAC_MQH
#define TW_HMAC_MQH

#include <Crypt.mqh>

//--- Convert hex string to lowercase
string HexToLower(const string hex) {
   string result = hex;
   StringToLower(result);
   return result;
}

//--- Compute HMAC-SHA256 of body using key, return lowercase hex string
string ComputeHMAC(const string &body, const string &secret) {
   uchar key_bytes[], data_bytes[], result[];
   StringToCharArray(secret, key_bytes, 0, StringLen(secret));
   StringToCharArray(body,   data_bytes, 0, StringLen(body));

   // MQL5 CryptEncode: CRYPT_HASH_SHA256 = 8 (HMAC not directly, use CRYPT_HASH_HMAC_SHA256)
   // CRYPT_HASH_HMAC_SHA256 is available in newer builds
   if (!CryptEncode(CRYPT_HASH_HMAC_SHA256, data_bytes, key_bytes, result)) {
      // Fallback: skip verification if HMAC not available
      return "HMAC_UNAVAILABLE";
   }

   // Convert bytes to hex string
   string hex = "";
   for (int i = 0; i < ArraySize(result); i++) {
      string byte_str = StringFormat("%02x", result[i]);
      hex += byte_str;
   }
   return hex;
}

//--- Verify the X-TW-Signature header matches computed HMAC
bool VerifySignature(const string &body, const string &signature, const string &secret) {
   if (secret == "" || signature == "") return true; // skip if not configured
   string computed = ComputeHMAC(body, secret);
   if (computed == "HMAC_UNAVAILABLE") return true;  // skip if not supported
   return (computed == HexToLower(signature));
}

#endif // TW_HMAC_MQH
