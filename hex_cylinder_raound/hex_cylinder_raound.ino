#include <Servo.h>
#include <math.h>

#define kp 0.02    // 比例ゲイン
#define ki 0.005   // 積分ゲイン
#define kd 0.00  // 微分ゲイン

/*---
目標値の波形
0 : 三角波
1 : 矩形波
2 : 正弦波
---*/
#define targetMode 2
//目標値の波形の周波数(Hz)
#define targetFreq 0.5
//シリンダーの個数
#define numCylinders 1

#define PI 3.1415

Servo servos[numCylinders];

uint8_t posSenPinNo[numCylinders] = { A1 };  // ポジションセンサーの繋がっているポート番号
uint8_t valvePinNo[numCylinders] = { 3 };    // バルブの繋がっているポート番号
int16_t valGetPosSen[numCylinders];          // ポジションセンサーの取得値
int16_t targetPos[numCylinders];             // 目標位置
int16_t currentPos[numCylinders];            // 現在位置

float err[numCylinders];         // 現在の偏差
float prevErr[numCylinders];     // 前回の偏差
float errVel[numCylinders];      // 現在の偏差速度
float prevErrVel[numCylinders];  // 前回の偏差速度
float errAcc[numCylinders];      // 現在の偏差加速度

float dt = 0;          // 前回との時間差分
float dtTgt = 0;       //Target位置生成用の時間差分
uint32_t nowTime = 0;  //今の時間(ms)
uint32_t oldTime = 0;  //前回時間(ms)

float dOutput = 0.0;  //出力変化量
float output = 0.0;   //出力(バルブ開度)

uint8_t direction = 1;           // 目標値を変化させる方向を保持する変数
uint16_t simulatedPotValue = 0;  // 目標値を保持する変数

uint8_t i = 0;
uint8_t j = 0;
char buf[255];

//目標値生成用の関数を宣言
void targetGen(void);

void setup() {
  Serial.begin(9600);

  //サーボのピン番号を指定
  for (int i = 0; i < numCylinders; i++) {
    /*---
    各モータにおけるパルス幅
    SG90 : 500-2400(us)
    MG90 : 1000-2000(us)
    ---*/
    servos[i].attach(valvePinNo[i], 1000, 2000);
  }
  //oldTime初期化
  oldTime = micros();
}

void loop() {
  //現在時刻取得(us)
  nowTime = micros();
  //時間差分計算
  dt = float(nowTime - oldTime) / 1000000.0;
  //oldTime初期化
  oldTime = nowTime;

  // Target波形を動的に生成する関数
  targetGen();

  // 各シリンダーごとの処理
  for (i = 0; i < numCylinders; i++) {
    valGetPosSen[i] = analogRead(posSenPinNo[i]);  // ポジションセンサーの値を読み取る

    // エアシリンダーの角度を計算
    targetPos[i] = map(simulatedPotValue, 0, 1023, 0, 1023);  //目標値を10bit値に変換
    currentPos[i] = map(valGetPosSen[i], 1023, 0, 0, 1023);   //ポジションセンサーの値を10bit値に変換

    // 偏差を計算
    err[i] = float(targetPos[i] - currentPos[i]);

    // 偏差速度を計算
    errVel[i] = (err[i] - prevErr[i]) / dt;

    // 偏差加速度を計算
    errAcc[i] = (errVel[i] - prevErrVel[i]) / dt;

    //出力変化量を計算
    dOutput = kp * errVel[i] + ki * err[i] + kd * errAcc[i];

    if (err[i] * prevErr[i] < 0) {
      output = 0;
    }

    //出力を計算
    output += dOutput;

    //outputがサーボの範囲を超えすぎないように制限
    if (output > 90) {
      output = 90;
    } else if (output < -90) {
      output = -90;
    }

    // 制御信号をサーボモーターに出力
    servos[i].write(90.0 + output);

    // 前回の偏差を更新
    prevErr[i] = err[i];
    prevErrVel[i] = errVel[i];

    // シリアルモニタに出力
    sprintf(buf, "targetPos%01d:", (int)i);
    Serial.print(buf);
    Serial.print(targetPos[i]);
    Serial.print(", ");
    sprintf(buf, "currentPos%01d:", (int)i);
    Serial.print(buf);
    Serial.print(currentPos[i]);
    Serial.print(", ");
    Serial.print("output:");
    Serial.print(output * 2);
    // Serial.print(", ");
    // Serial.print("dt:");
    // Serial.print(dt);
    // Serial.print(", ");
    // Serial.print("nowTime:");
    // Serial.print(float(nowTime / 1000000.0));
    Serial.println();
  }
}

void targetGen(void) {
  switch (targetMode) {
    case 0:
      simulatedPotValue += 4 * 1023 * targetFreq * dt * direction;
      if (simulatedPotValue >= 1023 || simulatedPotValue <= 0) {
        direction = direction * -1;  // 値が 0 から 1023 の範囲を超えたら方向を反転させる
      }
      break;
    case 1:
      dtTgt = dtTgt + dt;
      if (2 * targetFreq * dtTgt > 1) {
        dtTgt = 0;
        if (simulatedPotValue == 1023) {
          simulatedPotValue = 0;
        } else {
          simulatedPotValue = 1023;
        }
      }
      break;
    case 2:
      simulatedPotValue = 512 * sin(2 * PI * targetFreq * nowTime / 1000000) + 511;
      break;
  }
}
