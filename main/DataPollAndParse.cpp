#include "DataPollAndParse.h"

USBPolling::USBPolling()
  : _mySerial(Serial0) {}

void USBPolling::begin(const uint32_t baudRate) {
  _mySerial.begin(baudRate);
}

bool USBPolling::poll() {
  if (_mySerial.available() >= 8) {
    _mySerial.readBytes(reinterpret_cast<char*>(&_getData), sizeof(_getData));
    //---------------------
    // sendData(_getData);
    //---------------------
    if (dataParse()) {
      return true;
    }
    clearSerialBuffer();
  }
  return false;
}

void USBPolling::clearSerialBuffer(void) {
  while (_mySerial.available()) {
    _mySerial.read();
  }
}

bool USBPolling::dataParse(void) {
  _parsedData.format = static_cast<uint8_t>((_getData >> 58) & 0x3F);

  switch (_parsedData.format) {
    case 63:
      return parseFields(1, 1, 1, 1, 12, 12, 12, 12);
      break;
    case 1:
      return parseFields(1, 1, 1, 1, 1, 1, 1, 1);
      break;
    case 50:
      return parseFields(1, 1, 1, 1, 1, 1, 0, 0);
      break;
    case 10:
    case 20:
    case 30:
    case 40:
      return parseFields(8, 8, 8, 0, 0, 0, 0, 0);
      break;
    // case 11:
    // case 21:
    // case 31:
    // case 41:
    //   return parseFields(8, 8, 8, 12, 12, 0, 0, 0);
    //   break;
    // case 5:
    // case 6:
    // case 7:
    // case 8:
    //   return parseFields(12, 12, 12, 0, 0, 0, 0, 0);
    //   break;
    default:
      return parseFields(0, 0, 0, 0, 0, 0, 0, 0);
      break;
  }
  return false;
}

bool USBPolling::parseFields(uint8_t len1, uint8_t len2, uint8_t len3, uint8_t len4, uint8_t len5, uint8_t len6, uint8_t len7, uint8_t len8) {
  uint8_t __shift = 0;

  if (len1 > 0) {
    _parsedData.field1 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len1) - 1));
    __shift += len1;
  } else {
    _parsedData.field1 = 0;
  }
  if (len2 > 0) {
    _parsedData.field2 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len2) - 1));
    __shift += len2;
  } else {
    _parsedData.field2 = 0;
  }
  if (len3 > 0) {
    _parsedData.field3 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len3) - 1));
    __shift += len3;
  } else {
    _parsedData.field3 = 0;
  }
  if (len4 > 0) {
    _parsedData.field4 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len4) - 1));
    __shift += len4;
  } else {
    _parsedData.field4 = 0;
  }
  if (len5 > 0) {
    _parsedData.field5 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len5) - 1));
    __shift += len5;
  } else {
    _parsedData.field5 = 0;
  }
  if (len6 > 0) {
    _parsedData.field6 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len6) - 1));
    __shift += len6;
  } else {
    _parsedData.field6 = 0;
  }
  if (len7 > 0) {
    _parsedData.field7 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len7) - 1));
    __shift += len7;
  } else {
    _parsedData.field7 = 0;
  }
  if (len8 > 0) {
    _parsedData.field8 = static_cast<uint16_t>((_getData >> __shift) & ((1ULL << len8) - 1));
  } else {
    _parsedData.field8 = 0;
  }

  if ((_getData & 0x1F) > 0) {
    return false;
  }

  return true;
}

const ParsedDataStruct& USBPolling::getParsedData() const {
  return _parsedData;
}

void USBPolling::sendData(const uint64_t& data) const {
  for (int __i = sizeof(data) * 8 - 1; __i >= 0; --__i) {
    _mySerial.print(bitRead(data, __i));
  }
  // _mySerial.println();
}

const uint64_t& USBPolling::dataCoupling(const uint8_t format, const uint16_t data1, const uint16_t data2, const uint16_t data3, const uint16_t data4, const uint16_t data5) {
  uint8_t __dataBit[6] = { 6, 0, 0, 0, 0, 0 };
  uint8_t __dataShift[6];
  uint64_t __dataMask[6];

  _sendData = 0;
  switch (format) {
    case 11:
    case 21:
    case 31:
    case 41:
      __dataBit[1] = 8;
      __dataBit[2] = 8;
      __dataBit[3] = 8;
      __dataBit[4] = 12;
      __dataBit[5] = 12;
      __dataShift[0] = 64 - __dataBit[0];
      for (int __i = 1; __i < 6; __i++) {
        __dataShift[__i] = __dataShift[__i - 1] - __dataBit[__i];
      }
      for (int __i = 0; __i < 6; __i++) {
        __dataMask[__i] = (1ULL << __dataShift[__i]) - 1;
      }

      _sendData |= (static_cast<uint64_t>(format) & __dataMask[0]) << __dataShift[0];
      _sendData |= (static_cast<uint64_t>(data1) & __dataMask[1]) << __dataShift[1];
      _sendData |= (static_cast<uint64_t>(data2) & __dataMask[2]) << __dataShift[2];
      _sendData |= (static_cast<uint64_t>(data3) & __dataMask[3]) << __dataShift[3];
      _sendData |= (static_cast<uint64_t>(data4) & __dataMask[4]) << __dataShift[4];
      _sendData |= (static_cast<uint64_t>(data5) & __dataMask[5]) << __dataShift[5];
      break;
    case 5:
    case 6:
    case 7:
    case 8:
      __dataBit[1] = 12;
      __dataBit[2] = 12;
      __dataBit[3] = 12;
      __dataBit[4] = 0;
      __dataBit[5] = 0;
      __dataShift[0] = 64 - __dataBit[0];
      for (int __i = 1; __i < 6; __i++) {
        __dataShift[__i] = __dataShift[__i - 1] - __dataBit[__i];
      }
      for (int __i = 0; __i < 6; __i++) {
        __dataMask[__i] = (1ULL << __dataShift[__i]) - 1;
      }

      _sendData |= (static_cast<uint64_t>(format) & __dataMask[0]) << __dataShift[0];
      _sendData |= (static_cast<uint64_t>(data1) & __dataMask[1]) << __dataShift[1];
      _sendData |= (static_cast<uint64_t>(data2) & __dataMask[2]) << __dataShift[2];
      _sendData |= (static_cast<uint64_t>(data3) & __dataMask[3]) << __dataShift[3];
      _sendData |= (static_cast<uint64_t>(data4) & __dataMask[4]) << __dataShift[4];
      _sendData |= (static_cast<uint64_t>(data5) & __dataMask[5]) << __dataShift[5];
      break;
    default:
      break;
  }
  return _sendData;
}