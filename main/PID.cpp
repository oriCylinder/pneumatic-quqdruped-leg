#include "Arduino.h"
#include "math.h"

#include "PID.h"

PID::PID(void) {
  _preTime = micros();
  _prevPosErr = 0.0;
  _prevVelErr = 0.0;
  _clipLimit.enable = false;
  setBaseGain(0.0, 0.0, 0.0);
  setGain(0.0, 0.0, 0.0);
}

void PID::setBaseGain(const float pBaseGain, const float iBaseGain, const float dBaseGain) {
  _gains.pBaseGain = pBaseGain;
  _gains.iBaseGain = iBaseGain;
  _gains.dBaseGain = dBaseGain;
}

void PID::setGain(const uint8_t pGain, const uint8_t iGain, const uint8_t dGain) {
  _gains.pGain = pGain;
  _gains.iGain = iGain;
  _gains.dGain = dGain;
  _gains.pCalcGain = _gains.pBaseGain * float(_gains.pGain);
  _gains.iCalcGain = _gains.iBaseGain * float(_gains.iGain);
  _gains.dCalcGain = _gains.dBaseGain * float(_gains.dGain);
}

const gainStruct& PID::getGain(void) const {
  return _gains;
}

float PID::calcCommand(const uint16_t targetPosition, const uint16_t currentPosition) {
  _nowTime = micros();
  _dt = float(_nowTime - _preTime) / 1000000.0;
  _posErr = float(targetPosition - currentPosition);
  _velErr += (_posErr - _prevPosErr) * _dt;
  _accErr = (_velErr - _prevVelErr) / _dt;
  _prevPosErr = _posErr;
  _prevVelErr = _velErr;
  _command = _command + _gains.pCalcGain * _posErr + _gains.iCalcGain * _velErr + _gains.dCalcGain * _accErr;

  if (_clipLimit.enable) {
    if (_command > _clipLimit.high) {
      _retCommand = _clipLimit.high;
    } else if (_command < _clipLimit.low) {
      _retCommand = _clipLimit.low;
    }
  } else {
    _retCommand = _command;
  }
  return _retCommand;
}

void PID::clipLimitEnable(const bool enable, const float highSideLimit, const float lowSideLimit) {
  _clipLimit.enable = enable;
  _clipLimit.high = highSideLimit;
  _clipLimit.low = lowSideLimit;
}

void PID::clipLimitDisable(const bool enable) {
  _clipLimit.enable = enable;
}

void PID::timeReset(void){
  _preTime = micros();
}