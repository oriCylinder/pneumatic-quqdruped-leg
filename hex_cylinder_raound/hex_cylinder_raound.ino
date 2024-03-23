#include <Servo.h>

const int numCylinders = 1;
Servo servos[numCylinders];
int val1 = A1; // シリンダー
int ls[numCylinders]; // リニアセンサーの値
float targetAngle[numCylinders]; // 目標角度
float currentAngle[numCylinders]; // 現在の角度
float error[numCylinders]; // 現在の偏差
float prevError[numCylinders] = {0.0}; // 前回の偏差
float integral[numCylinders]; // 積分項
float derivative[numCylinders]; // 微分項
float kp = 1.5; // 比例ゲイン
float ki = 1.6; // 積分ゲイン
float kd = 0.5; // 微分ゲイン
float dt = 0.01; // 固定の周期（例: 0.01秒）
float integralMin = -100.0; // 積分項の下限値
float integralMax = 100.0; // 積分項の上限値
float outputOld=0.0;

char direction[numCylinders] = {1}; // ポテンショメーターの値を模擬的に変化させる方向を保持する変数
int simulatedPotValue = 0; // ポテンショメーターの値を模擬的に保持する変数

void setup() {
  Serial.begin(9600);

  // 各シリンダーのサーボをピンにアタッチ
  // servos[0].attach(2, 500, 2400);
  // servos[1].attach(3, 500, 2400);
  // servos[2].attach(4, 500, 2400);
  // servos[3].attach(5, 500, 2400);
  // servos[4].attach(6, 500, 2400);
  // servos[5].attach(7, 500, 2400);

  for (int i=0; i<numCylinders; i++){
    servos[i].attach(i+2, 500, 2400);
  }
}

void loop() {
  // ポテンショメーターの値を模擬的に変化させる
  simulatedPotValue += 3 * direction[0];
  if (simulatedPotValue >= 1023 || simulatedPotValue <= 0) {
    direction[0] *= -1; // 値が 0 から 1023 の範囲を超えたら方向を反転させる
  }

  // 各シリンダーごとの処理
  for (int i = 0; i < numCylinders; i++) {
    ls[i] = analogRead(val1); // リニアセンサーの値を読み取る

    // エアシリンダーの角度を計算
    targetAngle[i] = map(simulatedPotValue, 0, 1023, 20, 170); // ポテンショメーターの範囲を角度の範囲にマッピング
    currentAngle[i] = map(ls[i], 1023, 400, 20, 170); // リニアセンサーの範囲を角度の範囲にマッピング

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
    float output = kp * error[i] + ki * integral[i] - kd * derivative[i]/dt;
    // float output = kp * error[i] + ki * integral[i] - kd /dt;
    // if ((outputOld-output)>1){
    //   output=output+1;
    // }else if((outputOld-output)<-1){
    //   output=output-1;
    // }
    // outputOld=output;

    // 制御信号をサーボモーターに出力
    if(output>90){
      output=90;
    }else if(output<-90){
      output=-90;
    }
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
  }
  Serial.println();

  // delay(10);

  // 前回の偏差を更新
  for (int i = 0; i < numCylinders; i++) {
    prevError[i] = error[i];
  }
}
