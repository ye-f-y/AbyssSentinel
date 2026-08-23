# backend/core/agent.py
"""
AI推演核心：调用通义千问 + 国标知识库 + 决策排水

输出规范：
  AI必须按5段结构输出，每段以【段名】开头，段内语句完整连贯。
  后端对AI输出做后处理（_postprocess），确保格式统一、无截断。
"""
import json
import os
import re
import time
from openai import OpenAI


# ==================== 预置国标条款（扫描版PDF的fallback） ====================
# 城镇内涝防治技术规范 GB51174-2017 是扫描版PDF，RAG无法检索，此处预置关键条款
PRESET_REGULATIONS = [
    {
        "source": "GB51174-2017《城镇内涝防治技术规范》第5.2.1条",
        "content": "内涝防治系统应在降雨前启动预排水，降低管网水位，预留调蓄空间。当预报降雨量可能超过设计标准时，应提前开启排涝泵站进行预抽排。",
        "page": 0
    },
    {
        "source": "GB51174-2017《城镇内涝防治技术规范》第4.2.2条",
        "content": "内涝防治系统应具备源头减排、排水管渠、排涝除险三重功能，应在降雨前、降雨中、降雨后分别采取相应措施。",
        "page": 0
    },
    {
        "source": "GB51174-2017《城镇内涝防治技术规范》第3.0.4条",
        "content": "当气象预报发布暴雨预警时，内涝防治系统应立即进入预警响应状态，各排涝设施应做好启动准备。",
        "page": 0
    },
    {
        "source": "GB50330-2013《建筑边坡工程技术规范》第5.3.2条",
        "content": "边坡稳定安全系数Fst应按表5.3.2确定。当边坡稳定性系数小于边坡稳定安全系数时，应对边坡进行处理。永久边坡一级安全等级一般工况Fst=1.35。",
        "page": 26
    },
    {
        "source": "GB50330-2013《建筑边坡工程技术规范》第5.3.1条",
        "content": "边坡稳定性状态应根据边坡稳定性系数Fs按表5.3.1划分：Fs<Fst为不稳定，Fst≤Fs<1.05为欠稳定，1.05≤Fs<Fst为基本稳定，Fs≥1.35为稳定。",
        "page": 26
    },
    {
        "source": "GB50330-2013《建筑边坡工程技术规范》第4.2.2条",
        "content": "边坡工程勘察应包括地下水位、水量、类型及动态变化情况。地下水发育时，应评价其对边坡稳定性的影响。",
        "page": 22
    },
]

# 5段结构定义（顺序固定）
SECTION_KEYS = ["数据解读", "灾害链推演", "国标依据", "风险评级", "决策说明"]


class SentinelAgent:

    def __init__(self, api_key: str, knowledge_base=None):
        self.kb = knowledge_base
        self.api_key = api_key

        # LLM端点与模型可配置（大赛环境用aiping，本地开发可切回dashscope）
        base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = os.getenv("LLM_MODEL", "qwen-plus")

        if api_key:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            print(f"AI推演模型: {self.model} @ {base_url}")
        else:
            self.client = None
            print("警告: API Key未配置，AI推演不可用")

        self._last_pump_time = 0
        self._pump_cooldown = 60

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "activate_pump",
                    "description": "启动虚拟泵站进行预排水，触发物理继电器",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "duration": {
                                "type": "integer",
                                "description": "排水持续时间（秒），范围30-180"
                            },
                            "reason": {
                                "type": "string",
                                "description": "排水原因，必须引用国标条款"
                            }
                        },
                        "required": ["duration", "reason"]
                    }
                }
            }
        ]

        self._system_prompt = """你是深渊哨兵防灾AI，专职分析城市内涝和边坡灾害风险。

【工作规则】
1. 基于传感器数据进行灾害链推演（暴雨→土壤饱和→滑坡→内涝）
2. 每个判断必须引用具体国标条款（含标准编号和条文号）
3. 输出必须严格按以下5段结构，每段以【段名】开头，段内语句必须完整、连贯，不得截断
4. 只有风险等级为WARNING或CRITICAL时才调用排水工具
5. 引用的国标条款必须来自下方"相关国标条款"部分，不得编造

【输出格式】（严格遵循，不得增减段落，不得改变顺序）
【数据解读】用2-4句完整语句说明各传感器数值的含义及异常程度。
【灾害链推演】用3-5句完整语句逐步推演可能的灾害发展路径，每步用序号标注。
【国标依据】引用相关规范条款，每条引用单独一行，格式为"依据《标准名》第X.X.X条：条款内容摘要"。
【风险评级】输出一个词：NORMAL或WATCH或WARNING或CRITICAL，后接一句话说明理由。
【决策说明】用1-3句完整语句说明是否排水及原因。若排水，须注明持续时间。"""

    async def analyze(self, sensor_data: dict, rule_result: dict) -> dict:
        weather = sensor_data.get("weather", {})
        soil = sensor_data.get("soil", {})

        # ---- 检索国标规范（RAG + 预置fallback） ----
        regulations = []
        reg_text = ""

        # 1. RAG检索
        if self.kb:
            try:
                keywords = []
                p = weather.get("pressure", 1013)
                sm = soil.get("soil_moisture", 0)
                if p < 100.0:
                    keywords.extend(["暴雨", "内涝防治", "预排水"])
                if sm > 75:
                    keywords.extend(["边坡稳定", "土壤饱和", "边坡处理"])
                if not keywords:
                    keywords = ["城市内涝", "边坡工程"]
                rag_results = self.kb.search(" ".join(keywords), top_k=5)
                if rag_results:
                    regulations.extend(rag_results)
            except Exception as e:
                print(f"知识库检索失败: {e}")

        # 2. 预置条款补充（扫描版PDF的fallback）
        # 检查是否已有内涝规范条款，若无则补充预置
        has_flood_reg = any("51174" in r.get("source", "") for r in regulations)
        has_slope_reg = any("50330" in r.get("source", "") for r in regulations)

        for preset in PRESET_REGULATIONS:
            if "51174" in preset["source"] and not has_flood_reg:
                regulations.append(preset)
            elif "50330" in preset["source"] and not has_slope_reg:
                regulations.append(preset)

        # 3. 去重（按source）
        seen_sources = set()
        unique_regs = []
        for r in regulations:
            src = r.get("source", "")
            if src not in seen_sources:
                seen_sources.add(src)
                unique_regs.append(r)
        regulations = unique_regs[:6]  # 最多6条

        # 4. 格式化规范文本给AI
        if regulations:
            reg_lines = []
            for r in regulations:
                src = r.get("source", "国标规范")
                content = r.get("content", "").strip()
                reg_lines.append(f"【{src}】{content}")
            reg_text = "\n".join(reg_lines)
        else:
            reg_text = "未检索到相关条款"

        # ---- 构造提示词 ----
        prompt = f"""## 实时传感器数据

气象数据：
- 大气压：{weather.get('pressure', 'N/A')} kPa
- 空气湿度：{weather.get('air_humidity', 'N/A')} %
- 风速：{weather.get('wind_speed', 'N/A')} m/s
- 风向：{weather.get('wind_dir', 'N/A')}°
- 气温：{weather.get('air_temp', 'N/A')} ℃
- 光照：{weather.get('light', 'N/A')} Lux

土壤数据：
- 土壤湿度：{soil.get('soil_moisture', 'N/A')} %
- 土壤温度：{soil.get('soil_temp', 'N/A')} ℃
- 电导率：{soil.get('soil_ec', 'N/A')} μS/cm
- pH值：{soil.get('soil_ph', 'N/A')}

## 规则引擎初步判断
风险等级：{rule_result['level']}
触发原因：{'; '.join(rule_result.get('reasons', []))}

## 相关国标条款（必须引用这些条款，不得编造）
{reg_text}

## 请进行灾害链推演分析（严格按5段结构输出）"""

        # AI调用出错时的兜底
        if not self.client:
            return self._fallback(rule_result, regulations)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt}
                ],
                tools=self.tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=2000,
                timeout=40
            )
        except Exception as e:
            print(f"AI调用失败: {e}")
            return self._fallback(rule_result, regulations)

        choice = response.choices[0]
        raw_text = choice.message.content or ""
        action = None

        # 检查AI是否决定排水
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                if tc.function.name == "activate_pump":
                    try:
                        args = json.loads(tc.function.arguments)
                        action = self._do_pump(args)
                    except Exception as e:
                        print(f"排水指令解析失败: {e}")

        # 后处理：确保5段结构完整
        analysis_text = self._postprocess(raw_text, rule_result, regulations)

        # 提取引用的规范来源列表
        cited_sources = [r.get("source", "") for r in regulations if r.get("source")]

        return {
            "analysis": analysis_text,
            "risk_level": rule_result["level"],
            "regulations_cited": cited_sources,
            "action": action,
            "timestamp": int(time.time())
        }

    def _postprocess(self, raw_text: str, rule_result: dict, regulations: list) -> str:
        """
        后处理AI输出，确保5段结构完整、语句连贯。
        若AI输出缺少某段，用规则引擎数据补充。
        """
        text = raw_text.strip()

        # 提取已存在的段落
        sections = {}
        # 匹配 【段名】后到下一个【或文末
        pattern = r'【(数据解读|灾害链推演|国标依据|风险评级|决策说明)】\s*([\s\S]*?)(?=【(?:数据解读|灾害链推演|国标依据|风险评级|决策说明)】|$)'
        for m in re.finditer(pattern, text):
            key = m.group(1)
            content = m.group(2).strip()
            if content:
                sections[key] = content

        # 补全缺失段落
        if "数据解读" not in sections:
            w = rule_result.get("weather", {})
            s = rule_result.get("soil", {})
            sections["数据解读"] = (
                f"当前气压{w.get('pressure','N/A')}kPa，"
                f"空气湿度{w.get('air_humidity','N/A')}%，"
                f"风速{w.get('wind_speed','N/A')}m/s，"
                f"土壤湿度{s.get('soil_moisture','N/A')}%。"
                f"规则引擎判定触发原因：{'; '.join(rule_result.get('reasons', []))}。"
            )

        if "灾害链推演" not in sections:
            level = rule_result["level"]
            if level in ("WARNING", "CRITICAL"):
                sections["灾害链推演"] = (
                    "1.气压骤降预示强对流天气形成，暴雨即将来临。"
                    "2.持续降雨使土壤含水率快速上升，接近饱和。"
                    "3.边坡土壤抗剪强度降低，存在滑坡风险。"
                    "4.路面积水上涨，内涝风险加剧。"
                )
            else:
                sections["灾害链推演"] = "当前各项指标处于正常范围，未检测到明显灾害链发展迹象。将持续监测气压和土壤湿度变化趋势。"

        if "国标依据" not in sections:
            # 用检索到的规范补充
            if regulations:
                lines = []
                for r in regulations[:3]:
                    lines.append(f"依据{r.get('source', '国标')}：{r.get('content', '')[:60]}")
                sections["国标依据"] = "\n".join(lines)
            else:
                sections["国标依据"] = "未检索到直接相关条款。"

        if "风险评级" not in sections:
            sections["风险评级"] = f"{rule_result['level']} —— {'；'.join(rule_result.get('reasons', []))}"

        if "决策说明" not in sections:
            level = rule_result["level"]
            if level in ("WARNING", "CRITICAL"):
                sections["决策说明"] = "风险等级较高，建议立即启动预排水系统，持续抽排路面积水，降低内涝风险。"
            else:
                sections["决策说明"] = "当前风险等级较低，无需启动排水。系统持续监测中。"

        # 按固定顺序拼接
        result_parts = []
        for key in SECTION_KEYS:
            content = sections.get(key, "").strip()
            # 确保语句以句号结尾
            if content and not content.endswith(("。", "！", "？", ".", "!", "?")):
                content += "。"
            result_parts.append(f"【{key}】{content}")

        return "\n\n".join(result_parts)

    def _do_pump(self, args: dict) -> dict:
        now = time.time()
        if now - self._last_pump_time < self._pump_cooldown:
            remaining = self._pump_cooldown - (now - self._last_pump_time)
            return {
                "status": "COOLDOWN",
                "message": f"距上次排水还需{remaining:.0f}秒"
            }
        duration = max(30, min(180, args.get("duration", 60)))
        reason = args.get("reason", "")
        self._last_pump_time = now
        return {
            "status": "EXECUTED",
            "action": "pump_on",
            "duration": duration,
            "reason": reason
        }

    def _fallback(self, rule_result: dict, regulations: list = None) -> dict:
        """AI调用失败时的兜底响应（仍保持5段结构）"""
        regs = regulations or []
        reasons = "；".join(rule_result.get("reasons", []))
        level = rule_result["level"]

        # 构建规范引用
        if regs:
            reg_lines = "\n".join(f"依据{r.get('source','国标')}：{r.get('content','')[:60]}" for r in regs[:3])
        else:
            reg_lines = "未检索到相关条款。"

        # 根据风险等级构建灾害链
        if level in ("WARNING", "CRITICAL"):
            chain = ("1.气压骤降预示强对流天气形成，暴雨即将来临。"
                     "2.持续降雨使土壤含水率快速上升，接近饱和。"
                     "3.边坡土壤抗剪强度降低，存在滑坡风险。"
                     "4.路面积水上涨，内涝风险加剧。")
            decision = "风险等级较高，建议立即启动预排水系统，持续抽排路面积水。"
        else:
            chain = "当前各项指标处于正常范围，未检测到明显灾害链发展迹象。"
            decision = "当前风险等级较低，无需启动排水。系统持续监测中。"

        analysis = (
            f"【数据解读】规则引擎判定风险等级为{level}，触发原因：{reasons}。"
            f"AI服务暂时不可用，以下为规则引擎兜底分析。\n\n"
            f"【灾害链推演】{chain}\n\n"
            f"【国标依据】{reg_lines}\n\n"
            f"【风险评级】{level} —— {reasons}\n\n"
            f"【决策说明】{decision}"
        )

        cited = [r.get("source", "") for r in regs if r.get("source")]

        return {
            "analysis": analysis,
            "risk_level": level,
            "regulations_cited": cited,
            "action": None,
            "timestamp": int(time.time()),
            "fallback": True
        }
