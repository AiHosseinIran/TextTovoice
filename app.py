from flask import Flask, request, jsonify, Response
import edge_tts
import asyncio
import os

# ==================== تنظیم مسیر HTML ====================
# به Flask می‌گیم HTML رو از همین پوشه بخون، نه از templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=BASE_DIR,   # ← این خط مهمه: به جای templates، همین پوشه
    static_folder=None
)

# ==================== لیست زبان‌ها ====================
TTS_VOICES = {
    'fa': [
        {'value': 'fa-IR-DilaraNeural', 'label': '👩 دیلارا (زن)'},
        {'value': 'fa-IR-FaridNeural', 'label': '👨 فرید (مرد)'},
    ],
    'en': [
        {'value': 'en-US-AriaNeural', 'label': '👩 Aria (Female)'},
        {'value': 'en-US-GuyNeural', 'label': '👨 Guy (Male)'},
    ],
    'ar': [
        {'value': 'ar-EG-SalmaNeural', 'label': '👩 سلمى'},
        {'value': 'ar-EG-ShakirNeural', 'label': '👨 شاكر'},
    ],
    'tr': [
        {'value': 'tr-TR-EmelNeural', 'label': '👩 Emel'},
        {'value': 'tr-TR-AhmetNeural', 'label': '👨 Ahmet'},
    ],
    'fr': [
        {'value': 'fr-FR-DeniseNeural', 'label': '👩 Denise'},
        {'value': 'fr-FR-HenriNeural', 'label': '👨 Henri'},
    ],
    'de': [
        {'value': 'de-DE-KatjaNeural', 'label': '👩 Katja'},
        {'value': 'de-DE-ConradNeural', 'label': '👨 Conrad'},
    ],
    'es': [
        {'value': 'es-ES-ElviraNeural', 'label': '👩 Elvira'},
        {'value': 'es-ES-AlvaroNeural', 'label': '👨 Alvaro'},
    ],
    'it': [
        {'value': 'it-IT-ElsaNeural', 'label': '👩 Elsa'},
        {'value': 'it-IT-DiegoNeural', 'label': '👨 Diego'},
    ],
    'ru': [
        {'value': 'ru-RU-SvetlanaNeural', 'label': '👩 Светлана'},
        {'value': 'ru-RU-DmitryNeural', 'label': '👨 Дмитрий'},
    ],
    'zh-CN': [
        {'value': 'zh-CN-XiaoxiaoNeural', 'label': '👩 晓晓'},
        {'value': 'zh-CN-YunxiNeural', 'label': '👨 云希'},
    ],
    'ja': [
        {'value': 'ja-JP-NanamiNeural', 'label': '👩 Nanami'},
        {'value': 'ja-JP-KeitaNeural', 'label': '👨 Keita'},
    ],
    'hi': [
        {'value': 'hi-IN-SwaraNeural', 'label': '👩 Swara'},
        {'value': 'hi-IN-MadhurNeural', 'label': '👨 Madhur'},
    ],
}

LANG_NAMES = {
    'fa': '🇮🇷 فارسی',
    'en': '🇺🇸 English',
    'ar': '🇸🇦 العربية',
    'tr': '🇹🇷 Türkçe',
    'fr': '🇫🇷 Français',
    'de': '🇩🇪 Deutsch',
    'es': '🇪🇸 Español',
    'it': '🇮🇹 Italiano',
    'ru': '🇷🇺 Русский',
    'zh-CN': '🇨🇳 中文',
    'ja': '🇯🇵 日本語',
    'hi': '🇮🇳 हिन्दी',
}


# ==================== توابع ====================

def run_async(coro):
    """اجرای تابع async در Flask (سازگار با Pydroid)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except Exception:
            pass


# ==================== Routes ====================

@app.route('/')
def index():
    """خوندن HTML از کنار app.py"""
    html_path = os.path.join(BASE_DIR, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # جایگزینی داده‌های JS
    import json
    html = html.replace(
        '__TTS_VOICES__', json.dumps(TTS_VOICES, ensure_ascii=False)
    ).replace(
        '__LANG_NAMES__', json.dumps(LANG_NAMES, ensure_ascii=False)
    )

    return Response(html, mimetype='text/html; charset=utf-8')


@app.route('/tts', methods=['POST'])
def text_to_speech():
    """تبدیل متن به صدا"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'داده‌ای ارسال نشد'}), 400

    text = data.get('text', '').strip()
    voice = data.get('voice', 'fa-IR-DilaraNeural')
    speed = data.get('speed', 'normal')

    if not text:
        return jsonify({'error': 'متن خالی است'}), 400
    if len(text) > 10000:
        return jsonify({'error': 'متن طولانی است (حداکثر ۱۰۰۰۰ کاراکتر)'}), 400

    rate_map = {'slow': '-30%', 'normal': '+0%', 'fast': '+30%'}
    rate = rate_map.get(speed, '+0%')

    async def generate():
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        audio = b''
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio += chunk['data']
        return audio

    try:
        audio_bytes = run_async(generate())
        if not audio_bytes:
            return jsonify({'error': 'خطا در تولید صدا'}), 500

        return Response(
            audio_bytes,
            mimetype='audio/mpeg',
            headers={'Cache-Control': 'no-cache'}
        )
    except Exception as e:
        return jsonify({'error': f'خطا: {str(e)}'}), 500


# ==================== اجرا ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🎙️   سرور تبدیل متن به صدا فعال شد")
    print(f"📂   پوشه پروژه: {BASE_DIR}")
    print("🌐   آدرس: http://localhost:5000")
    print("⏹️   برای توقف: Ctrl+C")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)
