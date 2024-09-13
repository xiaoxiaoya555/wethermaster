import os  
from datetime import date, datetime, timedelta
import random
import requests
from wechatpy import WeChatClient
from wechatpy.client.api import WeChatMessage
import json

# 获取 JSON 字符串
ceshi_json = os.getenv("ceshi")
if ceshi_json:
    # 解析 JSON 字符串
    config = json.loads(ceshi_json)
else:
    config = {}
location = config.CITY
api_key = config.api_key  # 确保你的 .env 文件中有 API_KEY

today = datetime.now()
start_date = config.START_DATE
birthday = config.BIRTHDAY

app_id = config.APP_ID
app_secret = config.APP_SECRET
user_id = config.USER_ID
template_id = config.TEMPLATE_ID
word_key = config.word_key

# 王晨的班次数据，从1号到30号
shifts = config.banci

# 根据当前日期获取今天或明天的班次
def get_shift(day_offset=0):
    # 根据当前日期计算班次的索引
    day_of_month = today.day + day_offset  # 根据偏移获取今天或明天的日期
    shift_index = (day_of_month - 1) % len(shifts)  # 调整为列表索引（从0开始）
    return shifts[shift_index]

# 获取天气数据
def get_weather():
    url = f"https://geoapi.qweather.com/v2/city/lookup?location={location}&key={api_key}"
    response = requests.get(url)
    data = response.json()

    if 'location' in data:
        for location_info in data['location']:
            if location_info['country'] == '中国':
                city_id = location_info['id']
                break
        else:
            raise ValueError("无法获取城市 ID")

        url2 = f'https://devapi.qweather.com/v7/weather/3d?location={city_id}&key={api_key}'
        response2 = requests.get(url2)
        weather_data = response2.json()

        if 'daily' in weather_data:
            today_date = datetime.now().strftime('%Y-%m-%d')
            tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

            today_weather = None
            tomorrow_weather = None

            for day_weather in weather_data['daily']:
                date = day_weather['fxDate']
                if date == today_date:
                    today_weather = {
                        'tempMax': day_weather['tempMax'],
                        'tempMin': day_weather['tempMin'],
                        'textDay': day_weather['textDay'],
                        'textNight': day_weather['textNight']
                    }
                elif date == tomorrow_date:
                    tomorrow_weather = {
                        'tempMax': day_weather['tempMax'],
                        'tempMin': day_weather['tempMin'],
                        'textDay': day_weather['textDay'],
                        'textNight': day_weather['textNight']
                    }
            if today_weather and tomorrow_weather:
                return today_weather, tomorrow_weather
            else:
                raise ValueError("无法获取今天或明天的天气数据")
        else:
            raise ValueError("API 响应中未包含 'daily' 数据")
    else:
        raise ValueError("API 响应中未包含 'location' 数据")

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