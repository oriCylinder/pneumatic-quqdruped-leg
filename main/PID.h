#ifndef PID_h
#define PID_h

#include "Arduino.h"

#include "PIDStruct.h"

class PID {
public:
  //コンストラクタ
  PID(void);

  //ベースゲインの設定
  void setBaseGain(const float pBaseGain, const float iBaseGain, const float dBaseGain);
  //ゲインの設定
  void setGain(const uint8_t pGain, const uint8_t iGain, const uint8_t dGain);
  //最小ループ秒数の設定
  void setMinDt(const uint16_t dt);
  //ゲインの取得
  const gainStruct& getGain(void) const;
  //コマンドの計算
  float calcCommand(const uint16_t targetPosition, const uint16_t currentPosition);
  //クリップリミットの設定
  void clipLimitEnable(const bool enable, const float highSideLimit, const float lowSideLimit);
  void clipLimitDisable(const bool enable);
  //dtのリセット
  void timeReset(void);

private:
  gainStruct _gains;
  clipLimitStruct _clipLimit;

  uint32_t _nowTime;
  uint32_t _preTime;
  int16_t _err[3];
  uint16_t _minDt;
  double _posErr;
  double _velErr;
  double _accErr;
  double _dt;
  float _command;
  float _retCommand;
};

#endif
