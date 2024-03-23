#include <Servo.h>
#include <math.h>

#define PI 3.1415
#define targetMode 2
/*---
ターゲット位置の波形
0 : 三角波
1 : 矩形波
2 : 正弦波
---*/
#define targetFreq 0.5
//ターゲット位置の波形の周波数(Hz)

const int numCylinders = 1;
Servo servos[numCylinders];
int val1 = A1;                            // シリンダー
int ls[numCylinders];                     // リニアセンサーの値
float targetAngle[numCylinders];          // 目標角度
float currentAngle[numCylinders];         // 現在の角度
float error[numCylinders];                // 現在の偏差
float prevError[numCylinders] = { 0.0 };  // 前回の偏差
float integral[numCylinders];             // 積分項
float derivative[numCylinders];           // 微分項
float kp = 0.8;                           // 比例ゲイン
float ki = 1.2;                           // 積分ゲイン
float kd = 0.5;                           // 微分ゲイン
float dt = 0;                             // 前回との時間差分
float dtTgt = 0;                          //Target位置生成用の時間差分
uint32_t nowTime = 0;                     //今の時間(ms)
uint32_t oldTime = 0;                     //前回時間(ms)
float integralMin = -100.0;               // 積分項の下限値
float integralMax = 100.0;                // 積分項の上限値
float outputOld = 0.0;

char direction = 1;         // ポテンショメーターの値を模擬的に変化させる方向を保持する変数
int simulatedPotValue = 0;  // ポテンショメーターの値を模擬的に保持する変数

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
    servos[i].attach(i + 2, 1000, 2000);
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
  for (int i = 0; i < numCylinders; i++) {
    ls[i] = analogRead(val1);  // リニアセンサーの値を読み取る

    // エアシリンダーの角度を計算
    targetAngle[i] = map(simulatedPotValue, 0, 1023, 20, 170);  // ポテンショメーターの範囲を角度の範囲にマッピング
    currentAngle[i] = map(ls[i], 1023, 0, 20, 170);             // リニアセンサーの範囲を角度の範囲にマッピング

    // 偏差を計算
    error[i] = targetAngle[i] - currentAngle[i];

    // PID制御計算
    integral[i] += error[i] * dt;
    // 積分項の制限
    // if (integral[i] < integralMin) {
    //   integral[i] = integralMin;
    // } else if (integral[i] > integralMax) {
    //   integral[i] = integralMax;
    // }
    derivative[i] = error[i] - prevError[i];
    float output = kp * error[i] + ki * integral[i] + kd * derivative[i] / dt;
    // if ((outputOld-output)>1){
    //   output=output+1;
    // }else if((outputOld-output)<-1){
    //   output=output-1;
    // }
    // outputOld=output;

    //outputがサーボの範囲を超えすぎないように制限
    if (output > 90) {
      output = 90;
    } else if (output < -90) {
      output = -90;
    }
    // 制御信号をサーボモーターに出力
    servos[i].write(90.0 + output);

    // シリアルモニタに出力
    Serial.print("targetAngle:");
    Serial.print(targetAngle[i]);
    Serial.print(", ");
    Serial.print("currentAngle:");
    Serial.print(currentAngle[i]);
    Serial.print(", ");
    Serial.print("i:");
    Serial.print(i + 1);
    Serial.print(", ");
    Serial.print("output:");
    Serial.print(output);
    // Serial.print(", ");
    // Serial.print("dt:");
    // Serial.print(dt);
    // Serial.print(", ");
    // Serial.print("nowTime:");
    // Serial.print(float(nowTime / 1000000.0));
  }
  Serial.println();

  // 前回の偏差を更新
  for (int i = 0; i < numCylinders; i++) {
    prevError[i] = error[i];
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
