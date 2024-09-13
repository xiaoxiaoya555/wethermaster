import os  
from datetime import date, datetime, timedelta
import random
import requests
from wechatpy import WeChatClient
from wechatpy.client.api import WeChatMessage
import json
import base64

# 从环境变量中获取 base64 编码的配置 JSON 字符串
config_base64 = os.getenv("CONFIG")
if config_base64:
    # 解码 base64 并将 JSON 字符串转换为字典
    config_json = base64.b64decode(config_base64).decode("utf-8")
    config = json.loads(config_json)
else:
    raise ValueError("配置未找到")

# 使用字典中的配置项
CITY = config.get("CITY")
START_DATE = config.get("START_DATE")
BIRTHDAY = config.get("BIRTHDAY")
APP_ID = config.get("APP_ID")
APP_SECRET = config.get("APP_SECRET")
USER_ID = config.get("USER_ID")
TEMPLATE_ID = config.get("TEMPLATE_ID")
API_KEY = config.get("api_key")
WORD_KEY = config.get("word_key")
BANCI = config.get("BANCI", "").split(",")
# 根据当前日期获取今天或明天的班次
def get_shift(day_offset=0):
    # 根据当前日期计算班次的索引
    day_of_month = today.day + day_offset  # 根据偏移获取今天或明天的日期
    shift_index = (day_of_month - 1) % len(shifts)  # 调整为列表索引（从0开始）
    return shifts[shift_index]

# 获取天气数据
def get_weather():
    # 从配置中获取 location (城市) 和 api_key
    config_json = os.getenv("CONFIG")
    if config_json:
        config = json.loads(config_json)
        location = config.get("CITY")  # 获取 CITY
        api_key = config.get("api_key")  # 获取 API 密钥
    else:
        raise ValueError("配置未找到")

    # 确保 location 和 api_key 存在
    if not location or not api_key:
        raise ValueError("未能获取到城市或API密钥")

    url = f"https://geoapi.qweather.com/v2/city/lookup?location={location}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    # 假设此处解析到的结果可以正确提取
    city_id = data['location'][0]['id']  # 获取城市ID
    url_weather = f"https://devapi.qweather.com/v7/weather/now?location={city_id}&key={api_key}"
    weather_response = requests.get(url_weather)
    weather_data = weather_response.json()

    today_weather = weather_data['now']['text']
    tomorrow_weather = "Sample for tomorrow"  # 这里的逻辑需要根据 API 来写

    return today_weather, tomorrow_weather

def send_message():
    today_weather, tomorrow_weather = get_weather()
    print(f"Today's weather: {today_weather}, Tomorrow's weather: {tomorrow_weather}")
# 计算天数
def get_count():
    delta = today - datetime.strptime(start_date, "%Y-%m-%d")
    return delta.days

# 计算生日倒计时
def get_birthday():
    next_birthday = datetime.strptime(str(date.today().year) + "-" + birthday, "%Y-%m-%d")
    if next_birthday < datetime.now():
        next_birthday = next_birthday.replace(year=next_birthday.year + 1)
    return (next_birthday - today).days

# 获取每日一句
def get_words():
    words = requests.get(f"https://apis.tianapi.com/wanan/index?key={word_key}")
    if words.status_code == 200:
        return words.json()['result']['content']
    return "获取每日一句失败"

# 获取黄历信息
def get_huangli():
    huangli_url = f"https://apis.tianapi.com/lunar/index?key={word_key}"
    response = requests.get(huangli_url)

    if response.status_code == 200:
        huangli_data = response.json()

        if huangli_data.get('code') == 200 and huangli_data.get('msg') == 'success':
            result = huangli_data.get('result', {})

            # 提取所需信息
            gregoriandate = result.get('gregoriandate', '未知')
            lunardate = result.get('lunardate', '未知')
            lunar_festival = result.get('lunar_festival', '')  # 农历节日
            festival = result.get('festival', '')  # 公历节日
            fitness = result.get('fitness', '')  # 宜做的事情
            taboo = result.get('taboo', '')  # 忌做的事情

            return {
                "gregorian": gregoriandate,
                "lunar": lunardate,
                "lunar_festival": lunar_festival if lunar_festival else "无农历节日",
                "festival": festival if festival else "无公历节日",
                "fitness": fitness,
                "taboo": taboo
            }
        else:
            return None
    else:
        return None

# 生成随机颜色
def get_random_color():
    return "#%06x" % random.randint(0, 0xFFFFFF)

# 发送微信消息
def send_message():
    today_weather, tomorrow_weather = get_weather()
    huangli_info = get_huangli()  # 获取黄历信息
    client = WeChatClient(app_id, app_secret)
    wm = WeChatMessage(client)

    # 如果获取黄历信息失败，返回默认值
    if not huangli_info:
        huangli_info = {
            "gregorian": "获取公历失败",
            "lunar": "获取农历失败",
            "lunar_festival": "无农历节日",
            "festival": "无公历节日",
            "fitness": "无宜做的事情",
            "taboo": "无忌做的事情"
        }

    # 获取今天和明天的班次
    today_shift = get_shift(day_offset=0)
    tomorrow_shift = get_shift(day_offset=1)

    data = {
        "gregorian": {"value":huangli_info["gregorian"]},
        "lunar": {"value":huangli_info["lunar"]},
        "lunar_festival": {"value":huangli_info["lunar_festival"]},
        "festival": {"value":huangli_info["festival"]},
        "fitness": {"value":huangli_info["fitness"]},
        "taboo": {"value":huangli_info["taboo"]},
        "weather_today": {"value":today_weather['textDay']},
        "temperature_today": {"value":today_weather['tempMax']},
        "weather_tomorrow": {"value":tomorrow_weather['textDay']},
        "temperature_tomorrow": {"value":tomorrow_weather['tempMax']},
        "shift_today": {"value":today_shift},
        "shift_tomorrow": {"value":tomorrow_shift},
        "love_days": {"value": get_count()},
        "birthday_left": {"value": get_birthday()},
        "words": {"value": get_words(), "color": get_random_color()}
    }

    res = wm.send_template(user_id, template_id, data)
    print(res)

if __name__ == "__main__":
    send_message()
