import random
import time
import sys
import json
import re
from typing import Dict, Any, Optional

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False32


class GameState:
    def __init__(self):
        self.health = 100
        self.max_health = 100
        self.mana = 50
        self.max_mana = 50
        self.strength = 12
        self.agility = 14
        self.intelligence = 13
        self.gold = 50
        self.inventory = ['生锈的短剑', '皮革护甲', '治疗药水', '火把']
        self.location = '神秘森林的边缘'
        self.environment = '一片古老而神秘的森林，高大的橡树遮天蔽日，地面上铺满了厚厚的落叶。远处传来未知生物的嚎叫声。'
        self.npcs = []
        self.enemies = []
        self.quest = None
        self.turn = 0
        self.last_action = None
        self.story_history = []
        self.character_name = "冒险者"
        self.character_class = "战士"
        self.world_state = {
            "weather": "晴朗",
            "time_of_day": "下午",
            "recent_events": []
        }


class DeepSeekInterface:
    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        """
        初始化DeepSeek API接口

        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 模型名称，默认使用deepseek-chat
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        if not api_key:
            raise ValueError("需要提供DeepSeek API密钥")

        # 设置OpenAI客户端使用DeepSeek的端点
        if OPENAI_AVAILABLE:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        elif REQUESTS_AVAILABLE:
            # 如果没有openai库，使用requests直接调用
            self.client = None
        else:
            raise ImportError("需要安装 openai 或 requests 库: pip install openai 或 pip install requests")

    def generate_response(self, messages: list) -> str:
        """生成DeepSeek响应"""
        try:
            if self.client:  # 使用openai库
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=800,
                    temperature=0.8,
                    top_p=0.95
                )
                return response.choices[0].message.content

            else:  # 使用requests直接调用
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 800,
                    "temperature": 0.8,
                    "top_p": 0.95,
                    "stream": False
                }

                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"API调用失败: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"DeepSeek API调用错误: {e}")
            return "抱歉，AI暂时无法响应，将使用基础逻辑处理你的行动。"


class IntelligentTextAdventureGame:
    def __init__(self, api_key: str = None):
        self.game_state = GameState()
        self.deepseek = None

        # 尝试初始化DeepSeek
        if api_key:
            try:
                self.deepseek = DeepSeekInterface(api_key)
                print("✅ 成功连接到 DeepSeek V3")
            except Exception as e:
                print(f"❌ DeepSeek初始化失败: {e}")
                print("将使用内置逻辑作为后备方案")
        else:
            print("⚠️ 未提供API密钥，将使用内置逻辑")

    def print_colored(self, text, color='white'):
        """打印彩色文本"""
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m'
        }
        print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

    def print_dm_message(self, text):
        """打印DM消息"""
        self.print_colored(f"🧙‍♂️ AI地下城主: {text}", 'purple')
        print()

    def print_system_message(self, text):
        """打印系统消息"""
        self.print_colored(f"⚙️  系统: {text}", 'cyan')
        print()

    def print_player_message(self, text):
        """打印玩家消息"""
        self.print_colored(f"🗡️  {self.game_state.character_name}: {text}", 'yellow')
        print()

    def display_character_sheet(self):
        """显示角色属性"""
        print("\n" + "=" * 60)
        self.print_colored("📊 角色状态", 'green')
        print("=" * 60)
        print(f"姓名: {self.game_state.character_name} ({self.game_state.character_class})")
        print(f"生命值: {self.game_state.health}/{self.game_state.max_health}")
        print(f"法力值: {self.game_state.mana}/{self.game_state.max_mana}")
        print(f"力量: {self.game_state.strength}")
        print(f"敏捷: {self.game_state.agility}")
        print(f"智力: {self.game_state.intelligence}")
        print(f"金币: {self.game_state.gold}")
        print(f"当前位置: {self.game_state.location}")
        print(f"环境: {self.game_state.world_state['weather']}, {self.game_state.world_state['time_of_day']}")
        print(f"回合数: {self.game_state.turn}")
        if self.game_state.enemies:
            print(f"附近敌人: {', '.join(self.game_state.enemies)}")
        print("=" * 60)

    def display_inventory(self):
        """显示背包"""
        if not self.game_state.inventory:
            self.print_system_message("🎒 你的背包是空的。")
        else:
            self.print_system_message(f"🎒 你的背包里有: {', '.join(self.game_state.inventory)}")

    def roll_d20(self):
        """投20面骰子"""
        return random.randint(1, 20)

    def create_dm_prompt(self, player_action: str) -> list:
        """创建给DeepSeek的DM提示"""
        system_prompt = f"""你是一个专业的地下城主(DM)，负责运行一个文字冒险游戏。你的任务是：

1. 根据玩家的行动，生成生动、有创意、符合奇幻世界观的故事情节
2. 决定是否需要进行骰子检定，以及检定的难度(1-20)
3. 根据行动结果，决定对角色属性的影响
4. 推进故事情节，保持游戏的趣味性和挑战性
5. 营造沉浸式的奇幻冒险氛围

当前游戏状态：
- 角色: {self.game_state.character_name} ({self.game_state.character_class})
- 生命值: {self.game_state.health}/{self.game_state.max_health}
- 法力值: {self.game_state.mana}/{self.game_state.max_mana}
- 力量: {self.game_state.strength}, 敏捷: {self.game_state.agility}, 智力: {self.game_state.intelligence}
- 金币: {self.game_state.gold}
- 当前位置: {self.game_state.location}
- 环境描述: {self.game_state.environment}
- 背包物品: {', '.join(self.game_state.inventory) if self.game_state.inventory else '无'}
- 当前敌人: {', '.join(self.game_state.enemies) if self.game_state.enemies else '无'}
- 天气: {self.game_state.world_state['weather']}, 时间: {self.game_state.world_state['time_of_day']}

游戏规则：
- 骰子检定：1-5(大失败), 6-10(失败), 11-15(成功), 16-20(大成功)
- 简单行动难度10-12，一般行动难度13-15，困难行动难度16-18，极难行动难度19-20
- 角色死亡时生命值降到0，但可以复活继续冒险

请严格按照以下JSON格式回复：
{{
    "needs_roll": true/false,
    "difficulty": 数字(1-20, 仅当needs_roll为true时),
    "description": "对玩家行动的生动描述和情境设定",
    "success_outcome": "成功时的结果描述(仅当needs_roll为true时)",
    "failure_outcome": "失败时的结果描述(仅当needs_roll为true时)", 
    "direct_outcome": "直接结果描述(仅当needs_roll为false时)",
    "effects": {{
        "health": 数字变化,
        "mana": 数字变化,
        "gold": 数字变化,
        "strength": 属性变化,
        "agility": 属性变化,
        "intelligence": 属性变化,
        "add_items": ["物品名1", "物品名2"],
        "remove_items": ["物品名1", "物品名2"],
        "location_change": "新地点名称(可选)",
        "environment_change": "新环境描述(可选)",
        "add_enemies": ["敌人名1", "敌人名2"],
        "remove_enemies": ["敌人名1", "敌人名2"]
    }}
}}

注意：请确保回复是合法的JSON格式，数字不要加引号。故事要生动有趣，富有想象力，符合奇幻冒险的氛围。"""

        recent_history = self.game_state.story_history[-3:] if self.game_state.story_history else []

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 添加最近的故事历史
        for entry in recent_history:
            messages.append({"role": "user", "content": f"玩家行动: {entry['action']}"})
            messages.append({"role": "assistant", "content": entry['response']})

        # 添加当前玩家行动
        messages.append({"role": "user", "content": f"玩家行动: {player_action}"})

        return messages

    def parse_deepseek_response(self, response: str) -> Dict[str, Any]:
        """解析DeepSeek的JSON响应"""
        try:
            # 清理响应文本，移除可能的markdown格式
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]

            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)

                # 验证必要字段
                if "needs_roll" not in parsed:
                    parsed["needs_roll"] = False
                if "effects" not in parsed:
                    parsed["effects"] = {}

                return parsed
            else:
                # 如果没有找到JSON，返回默认结构
                return {
                    "needs_roll": False,
                    "direct_outcome": response,
                    "effects": {}
                }
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            # JSON解析失败，返回默认结构
            return {
                "needs_roll": False,
                "direct_outcome": response,
                "effects": {}
            }

    def apply_effects(self, effects: Dict[str, Any]):
        """应用效果到游戏状态"""
        if not effects:
            return

        # 属性变化
        for attr in ['health', 'mana', 'strength', 'agility', 'intelligence', 'gold']:
            if attr in effects and effects[attr] != 0:
                current_value = getattr(self.game_state, attr)
                change = effects[attr]
                new_value = current_value + change

                # 应用限制
                if attr == 'health':
                    new_value = max(0, min(self.game_state.max_health, new_value))
                    if change != 0:
                        sign = "+" if change > 0 else ""
                        self.print_system_message(
                            f"💗 生命值变化: {sign}{change} (当前: {new_value}/{self.game_state.max_health})")
                elif attr == 'mana':
                    new_value = max(0, min(self.game_state.max_mana, new_value))
                    if change != 0:
                        sign = "+" if change > 0 else ""
                        self.print_system_message(
                            f"✨ 法力值变化: {sign}{change} (当前: {new_value}/{self.game_state.max_mana})")
                elif attr in ['strength', 'agility', 'intelligence']:
                    new_value = max(1, new_value)
                    if change != 0:
                        sign = "+" if change > 0 else ""
                        attr_name = {"strength": "力量", "agility": "敏捷", "intelligence": "智力"}[attr]
                        self.print_system_message(f"📈 {attr_name}变化: {sign}{change} (当前: {new_value})")
                elif attr == 'gold':
                    new_value = max(0, new_value)
                    if change != 0:
                        sign = "+" if change > 0 else ""
                        self.print_system_message(f"💰 金币变化: {sign}{change} (当前: {new_value})")

                setattr(self.game_state, attr, new_value)

        # 物品变化
        if 'add_items' in effects:
            for item in effects['add_items']:
                self.game_state.inventory.append(item)
                self.print_system_message(f"🎒 获得物品: {item}")

        if 'remove_items' in effects:
            for item in effects['remove_items']:
                if item in self.game_state.inventory:
                    self.game_state.inventory.remove(item)
                    self.print_system_message(f"🗑️ 失去物品: {item}")

        # 位置变化
        if 'location_change' in effects:
            old_location = self.game_state.location
            self.game_state.location = effects['location_change']
            self.print_system_message(f"🗺️ 位置变化: {old_location} → {self.game_state.location}")

        if 'environment_change' in effects:
            self.game_state.environment = effects['environment_change']

        # 敌人变化
        if 'add_enemies' in effects:
            for enemy in effects['add_enemies']:
                if enemy not in self.game_state.enemies:
                    self.game_state.enemies.append(enemy)
                    self.print_system_message(f"⚔️ 遭遇敌人: {enemy}")

        if 'remove_enemies' in effects:
            for enemy in effects['remove_enemies']:
                if enemy in self.game_state.enemies:
                    self.game_state.enemies.remove(enemy)
                    self.print_system_message(f"✅ 敌人被击败: {enemy}")

    def process_action_with_deepseek(self, action: str):
        """使用DeepSeek处理玩家行动"""
        if not self.deepseek:
            return self.fallback_process_action(action)

        try:
            # 生成DeepSeek提示
            messages = self.create_dm_prompt(action)

            # 获取DeepSeek响应
            deepseek_response = self.deepseek.generate_response(messages)

            # 解析响应
            parsed_response = self.parse_deepseek_response(deepseek_response)

            # 处理响应
            if parsed_response.get('needs_roll'):
                # 需要骰子检定
                roll = self.roll_d20()
                difficulty = parsed_response.get('difficulty', 15)
                success = roll >= difficulty

                self.print_dm_message(parsed_response.get('description', ''))

                # 显示骰子结果
                if roll <= 5:
                    result_text = f"🎲 大失败! 骰子结果: {roll} (需要: {difficulty})"
                    self.print_colored(result_text, 'red')
                elif roll >= 16:
                    result_text = f"🎲 大成功! 骰子结果: {roll} (需要: {difficulty})"
                    self.print_colored(result_text, 'green')
                else:
                    color = 'green' if success else 'red'
                    result_text = f"🎲 骰子结果: {roll} (需要: {difficulty}) - {'成功' if success else '失败'}"
                    self.print_colored(result_text, color)

                print()

                if success:
                    outcome = parsed_response.get('success_outcome', '你成功了！')
                    self.print_dm_message(outcome)
                    story_outcome = f"成功: {outcome}"
                else:
                    outcome = parsed_response.get('failure_outcome', '你失败了。')
                    self.print_dm_message(outcome)
                    story_outcome = f"失败: {outcome}"

                # 应用效果
                effects = parsed_response.get('effects', {})

                # 大失败时可能有额外惩罚
                if roll <= 5 and effects:
                    for key, value in effects.items():
                        if key in ['health', 'mana'] and value > 0:
                            effects[key] = -abs(value)  # 大失败时好事变坏事

                # 大成功时可能有额外奖励
                elif roll >= 16 and effects:
                    for key, value in effects.items():
                        if key in ['health', 'mana', 'gold'] and value > 0:
                            effects[key] = int(value * 1.5)  # 大成功时效果增强

                self.apply_effects(effects)

                # 记录故事
                story_entry = {
                    "action": action,
                    "response": f"{parsed_response.get('description', '')} [骰子: {roll}/{difficulty}] {story_outcome}"
                }

            else:
                # 不需要骰子检定
                outcome = parsed_response.get('direct_outcome', '你尝试了这个行动。')
                self.print_dm_message(outcome)

                self.apply_effects(parsed_response.get('effects', {}))

                # 记录故事
                story_entry = {
                    "action": action,
                    "response": outcome
                }

            # 添加到故事历史
            self.game_state.story_history.append(story_entry)

            # 保持历史长度在合理范围内
            if len(self.game_state.story_history) > 15:
                self.game_state.story_history = self.game_state.story_history[-15:]

        except Exception as e:
            print(f"DeepSeek处理错误: {e}")
            self.fallback_process_action(action)

    def fallback_process_action(self, action: str):
        """后备处理方案（使用内置逻辑）"""
        action_lower = action.lower()

        # 简单的关键词匹配和响应
        if any(word in action_lower for word in ['攻击', '打', '杀', '战斗']):
            roll = self.roll_d20()
            self.print_dm_message("你发起了攻击！")
            self.print_colored(f"🎲 骰子结果: {roll} (需要: 12)", 'cyan')

            if roll >= 12:
                self.print_dm_message("你的攻击成功命中了目标！")
                self.game_state.gold += 15
                if self.game_state.enemies:
                    enemy = self.game_state.enemies.pop(0)
                    self.print_system_message(f"✅ 击败了 {enemy}")
            else:
                self.print_dm_message("你的攻击失败了，还受到了反击。")
                self.game_state.health = max(0, self.game_state.health - 10)

        elif any(word in action_lower for word in ['搜索', '寻找', '查看']):
            roll = self.roll_d20()
            self.print_dm_message("你仔细搜索周围...")
            self.print_colored(f"🎲 骰子结果: {roll} (需要: 10)", 'cyan')

            if roll >= 10:
                items = ['神秘药水', '古老钥匙', '闪亮宝石', '魔法卷轴']
                found_item = random.choice(items)
                self.print_dm_message(f"你发现了{found_item}！")
                self.game_state.inventory.append(found_item)
            else:
                self.print_dm_message("你没有发现什么有用的东西。")

        elif '治疗药水' in action_lower:
            if '治疗药水' in self.game_state.inventory:
                self.print_dm_message("你喝下了治疗药水，感到身体在恢复。")
                self.game_state.health = min(self.game_state.max_health, self.game_state.health + 30)
                self.game_state.inventory.remove('治疗药水')
                self.print_system_message("💗 生命值恢复 +30")
            else:
                self.print_dm_message("你没有治疗药水。")

        else:
            responses = [
                "你尝试了这个行动，虽然结果不太明显，但你感到有所收获。",
                "你的创意想法产生了一些有趣的效果，周围的环境似乎有所变化。",
                "你的行动引起了一些微妙的反应，也许会在之后产生影响。",
                "你感到这个行动让你学到了一些东西，经验值略有增长。"
            ]
            self.print_dm_message(random.choice(responses))

    def setup_character(self):
        """角色创建"""
        print("\n" + "=" * 60)
        self.print_colored("🏗️  角色创建", 'green')
        print("=" * 60)

        name = input("请输入你的角色姓名 (留空使用'冒险者'): ").strip()
        if name:
            self.game_state.character_name = name

        print("\n可选择的职业:")
        print("1. 战士 - 高生命值和力量，擅长近战")
        print("2. 法师 - 高法力值和智力，擅长魔法")
        print("3. 盗贼 - 高敏捷和金币，擅长潜行")

        choice = input("选择职业 (1-3, 留空选择战士): ").strip()

        if choice == "2":
            self.game_state.character_class = "法师"
            self.game_state.mana = 80
            self.game_state.max_mana = 80
            self.game_state.intelligence = 16
            self.game_state.inventory.append("魔法书")
            self.game_state.inventory.append("魔法护符")
        elif choice == "3":
            self.game_state.character_class = "盗贼"
            self.game_state.agility = 18
            self.game_state.gold = 100
            self.game_state.inventory.append("开锁工具")
            self.game_state.inventory.append("毒匕首")
        else:
            self.game_state.character_class = "战士"
            self.game_state.health = 120
            self.game_state.max_health = 120
            self.game_state.strength = 16
            self.game_state.inventory.append("铁盾")

    def init_game(self):
        """初始化游戏"""
        print("\n" + "=" * 60)
        self.print_colored("🎲 AI地下城主 - DeepSeek V3驱动版 🎲", 'green')
        print("=" * 60)

        # 角色创建
        self.setup_character()

        self.print_system_message("🌟 欢迎来到AI地下城主的世界！")

        if self.deepseek:
            self.print_dm_message(
                "你好！我是你的AI地下城主，由DeepSeek V3强力驱动。我能理解你的任何创意想法并创造出精彩的奇幻冒险故事！")
        else:
            self.print_dm_message("你好！我是你的地下城主。虽然目前使用基础逻辑，但我仍会尽力为你创造有趣的冒险！")

        self.print_dm_message(
            f"欢迎你，{self.game_state.character_name}！作为一名勇敢的{self.game_state.character_class}，你即将踏上一段史诗般的冒险旅程。")
        self.print_dm_message(f"你目前站在{self.game_state.location}。{self.game_state.environment}")
        self.print_dm_message(
            "现在，告诉我你想做什么吧。记住，你的想象力是唯一的限制——你可以尝试任何创意的行动，我会为你编织出相应的传奇故事！")

        self.display_character_sheet()

    def show_help(self):
        """显示帮助信息"""
        help_text = f"""
🆘 游戏帮助

{'🧠 DeepSeek V3 AI驱动模式' if self.deepseek else '🔧 基础逻辑模式'}

基本命令:
- 输入任何你想做的事情，AI会理解并响应
- /status - 查看角色状态
- /inventory - 查看背包  
- /roll - 手动投骰子
- /story - 查看最近的冒险历史
- /help - 显示帮助
- /quit - 退出游戏

{'🚀 DeepSeek V3 高级功能:' if self.deepseek else '🎯 基础功能:'}
- 🧠 智能理解复杂的、创造性的行动描述
- 📖 动态生成引人入胜的故事情节
- 🎲 智能骰子检定和难度调整
- 🌍 上下文感知的世界状态管理
- 💫 大成功/大失败的特殊效果
- 📚 故事连贯性和角色发展

创意行动示例:
- "我想用火把点燃地上的落叶，制造烟雾来掩护我的撤退"
- "我尝试模仿鸟叫声来吸引森林中的精灵注意"
- "我用我的剑在地面画一个魔法阵，尝试召唤保护精神"
- "我想爬上那棵大树，从高处观察周围的地形"
- "我尝试和那只受伤的狼建立友谊，而不是战斗"

骰子系统:
🎲 1-5: 大失败 (严重后果)
🎲 6-10: 失败 (轻微后果)
🎲 11-15: 成功 (正常效果)
🎲 16-20: 大成功 (额外奖励)

{'✨ 在DeepSeek V3模式下，你的想象力就是唯一的限制！' if self.deepseek else ''}
        """
        self.print_colored(help_text, 'cyan')

    def show_story_history(self):
        """显示最近的冒险历史"""
        if not self.game_state.story_history:
            self.print_system_message("📖 还没有冒险历史。")
            return

        print("\n" + "=" * 60)
        self.print_colored("📖 最近的冒险历史", 'cyan')
        print("=" * 60)

        recent_stories = self.game_state.story_history[-5:]  # 显示最近5条
        for i, entry in enumerate(recent_stories, 1):
            print(f"\n{i}. 行动: {entry['action']}")
            print(f"   结果: {entry['response']}")

        print("=" * 60)

    def random_world_event(self):
        """随机世界事件"""
        if random.random() < 0.15:  # 15%概率触发
            events = [
                {
                    'description': '天空中突然出现了一道绚丽的彩虹，你感到精神振奋。',
                    'effects': {'mana': 10}
                },
                {
                    'description': '一阵神秘的风吹过，带来了远方的消息和一些金币。',
                    'effects': {'gold': 12}
                },
                {
                    'description': '你听到远处传来神秘的钟声，感到内心更加坚定。',
                    'effects': {'health': 8}
                },
                {
                    'description': '一只美丽的蝴蝶落在你的肩膀上，然后飞向未知的方向。',
                    'effects': {'intelligence': 1}
                },
                {
                    'description': '地面上出现了一个小小的魔法光圈，你从中获得了一些力量。',
                    'effects': {'strength': 1}
                }
            ]

            event = random.choice(events)
            time.sleep(1)
            self.print_system_message(f"🌟 世界事件: {event['description']}")
            self.apply_effects(event['effects'])

    def run(self):
        """运行游戏主循环"""
        self.init_game()

        while True:
            try:
                print("\n" + "-" * 60)
                action = input(f"🗡️  {self.game_state.character_name}想做什么？> ").strip()

                if not action:
                    continue

                # 处理特殊命令
                if action.lower() == '/quit':
                    self.print_colored("🌟 感谢游玩！愿你的冒险传说永远流传！", 'green')
                    break
                elif action.lower() == '/help':
                    self.show_help()
                    continue
                elif action.lower() == '/status':
                    self.display_character_sheet()
                    continue
                elif action.lower() == '/inventory':
                    self.display_inventory()
                    continue
                elif action.lower() == '/story':
                    self.show_story_history()
                    continue
                elif action.lower() == '/roll':
                    roll = self.roll_d20()
                    if roll <= 5:
                        self.print_colored(f"🎲 大失败！你投出了: {roll}", 'red')
                    elif roll >= 16:
                        self.print_colored(f"🎲 大成功！你投出了: {roll}", 'green')
                    else:
                        self.print_system_message(f"🎲 你投出了: {roll}")
                    continue

                # 显示玩家行动
                self.print_player_message(action)

                # 更新游戏状态
                self.game_state.turn += 1
                self.game_state.last_action = action

                # AI思考
                if self.deepseek:
                    thinking_messages = [
                        "🧠 DeepSeek V3正在分析情况...",
                        "🧠 AI地下城主正在编织故事...",
                        "🧠 正在计算行动后果...",
                        "🧠 创造中，请稍候..."
                    ]
                    self.print_colored(random.choice(thinking_messages), 'blue')
                else:
                    self.print_colored("🎲 地下城主正在思考...", 'blue')

                time.sleep(1.8)  # 增加悬念

                # 处理行动
                self.process_action_with_deepseek(action)

                # 检查游戏结束条件
                if self.game_state.health <= 0:
                    self.print_colored("💀 你的生命力耗尽了...但死亡并非终点，而是新冒险的开始！", 'red')
                    print("\n英雄永不真正死亡，他们只是在等待下一次的复活与冒险...")
                    restart = input("\n是否重新开始你的传奇？(y/n): ").strip().lower()
                    if restart == 'y':
                        print("\n🔄 重新编织命运之线...")
                        time.sleep(2)
                        self.game_state = GameState()
                        self.init_game()
                    else:
                        break

                # 随机世界事件
                self.random_world_event()

                # 随机更新世界状态
                if random.random() < 0.12:
                    weather_options = ["晴朗", "多云", "小雨", "起雾", "微风", "星空闪烁"]
                    time_options = ["黎明", "上午", "正午", "下午", "黄昏", "夜晚", "深夜"]

                    old_weather = self.game_state.world_state["weather"]
                    new_weather = random.choice(weather_options)
                    if new_weather != old_weather:
                        self.game_state.world_state["weather"] = new_weather
                        self.print_system_message(f"🌤️ 天气变化: {old_weather} → {new_weather}")

                    if random.random() < 0.4:
                        old_time = self.game_state.world_state["time_of_day"]
                        new_time = random.choice(time_options)
                        if new_time != old_time:
                            self.game_state.world_state["time_of_day"] = new_time
                            self.print_system_message(f"⏰ 时间流逝: {old_time} → {new_time}")

            except KeyboardInterrupt:
                self.print_colored("\n\n🌟 感谢游玩！愿你的冒险传说永远流传在这个魔法世界中！", 'green')
                break
            except Exception as e:
                self.print_colored(f"❌ 发生错误: {e}", 'red')
                print("游戏将继续运行...")


def get_deepseek_api_key():
    """获取DeepSeek API密钥"""
    print("🔑 DeepSeek API设置")
    print("=" * 40)
    print("请访问 https://platform.deepseek.com/ 获取API密钥")
    print("注册账号后，在控制台创建API密钥")
    print()

    api_key = input("请输入你的DeepSeek API密钥 (或输入 'skip' 跳过): ").strip()

    if api_key.lower() == 'skip' or not api_key:
        return None

    return api_key


if __name__ == "__main__":
    print("🎲 AI地下城主 - DeepSeek V3驱动版")
    print("=" * 40)
    print("一个由先进AI驱动的奇幻文字冒险游戏")
    print("你的想象力是唯一的限制！")
    print()

    # 获取API密钥
    api_key = get_deepseek_api_key()

    try:
        # 创建游戏实例
        print("\n🚀 正在启动游戏...")
        game = IntelligentTextAdventureGame(api_key)

        # 运行游戏
        game.run()

    except KeyboardInterrupt:
        print("\n🌟 感谢游玩！")
    except Exception as e:
        print(f"❌ 游戏启动失败: {e}")
        print("请检查API密钥设置或网络连接")
        print("\n如果问题持续，请:")
        print("1. 确认API密钥正确")
        print("2. 检查网络连接")
        print("3. 尝试重新运行程序")