#ifndef DATAPOLLANDPARSE_h
#define DATAPOLLANDPARSE_h

#include "Arduino.h"
#include "HardwareSerial.h"

#include "ComDataStruct.h"

class USBPolling {
public:
  //コンストラクタ
  USBPolling(void);

  //通信の初期化関数
  void begin(const uint32_t baudRate);

  //データポーリングとパース
  bool poll(void);

  //シリアルバッファの全クリア
  void clearSerialBuffer(void);

  //パースされた構造体を返す
  const ParsedDataStruct& getParsedData() const;

  //データの送信
  void sendData(const uint64_t& data) const;

  //データの連結
  const uint64_t& dataCoupling(const uint8_t format, const uint16_t data1, const uint16_t data2, const uint16_t data3, const uint16_t data4, const uint16_t data5);
private:
  HardwareSerial& _mySerial;
  ParsedDataStruct _parsedData;
  uint64_t _getData;
  uint64_t _sendData;

  bool dataParse(void);
  bool parseFields(uint8_t len1, uint8_t len2, uint8_t len3, uint8_t len4, uint8_t len5, uint8_t len6, uint8_t len7, uint8_t len8);
};

#endif
