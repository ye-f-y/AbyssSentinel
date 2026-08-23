# backend/core/rule_engine.py
"""
规则引擎：毫秒级快速风险判断
不调用AI，纯逻辑判断
"""

# 风险等级定义
NORMAL = "NORMAL"      # 正常
WATCH = "WATCH"        # 关注
WARNING = "WARNING"    # 警告
CRITICAL = "CRITICAL"  # 紧急


class RuleEngine:

    def evaluate(self, data: dict) -> dict:
        """
        输入传感器数据 -> 输出风险评估结果
        """
        weather = data.get("weather", {})
        soil = data.get("soil", {})

        pressure = weather.get("pressure", 1013)
        air_humidity = weather.get("air_humidity", 50)
        wind_speed = weather.get("wind_speed", 0)
        soil_moisture = soil.get("soil_moisture", 0)

        reasons = []
        risk_score = 0  # 0-100

        # ---- 内涝风险指标（气压单位: kPa） ----
        if pressure < 99.0:
            reasons.append(f"气压{pressure}kPa，低于99.0kPa，强对流天气风险")
            risk_score += 40
        elif pressure < 100.0:
            reasons.append(f"气压{pressure}kPa，低于100.0kPa，可能强降雨")
            risk_score += 20

        if air_humidity > 85:
            reasons.append(f"空气湿度{air_humidity}%，高于85%，高湿环境")
            risk_score += 15

        if wind_speed > 10.8:
            reasons.append(f"风速{wind_speed}m/s，6级以上强风")
            risk_score += 15

        # ---- 边坡滑坡指标 ----
        if soil_moisture > 85:
            reasons.append(f"土壤湿度{soil_moisture}%，接近饱和，高度危险")
            risk_score += 40
        elif soil_moisture > 75:
            reasons.append(f"土壤湿度{soil_moisture}%，接近饱和，需关注")
            risk_score += 25

        # ---- 复合灾害指标 ----
        if pressure < 99.5 and soil_moisture > 80:
            reasons.append(f"气压{pressure}kPa且土壤湿度{soil_moisture}%，暴雨+饱和土壤，立即处理")
            risk_score += 50

        # ---- 确定风险等级 ----
        if risk_score >= 60:
            level = CRITICAL
        elif risk_score >= 35:
            level = WARNING
        elif risk_score >= 15:
            level = WATCH
        else:
            level = NORMAL

        need_ai = level in (WARNING, CRITICAL)

        return {
            "level": level,
            "score": risk_score,
            "reasons": reasons if reasons else ["所有指标正常"],
            "need_ai": need_ai,
        }
