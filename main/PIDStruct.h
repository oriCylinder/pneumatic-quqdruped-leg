#ifndef PIDSTRUCT_H
#define PIDSTRUCT_H

//PIDゲインに関する構造体
struct gainStruct {
  uint8_t pGain;
  uint8_t iGain;
  uint8_t dGain;

  float pBaseGain;
  float iBaseGain;
  float dBaseGain;

  float pCalcGain;
  float iCalcGain;
  float dCalcGain;
};

//出力のクリップリミットに関する構造体
struct clipLimitStruct {
  bool enable;
  float high;
  float low;
};

#endif