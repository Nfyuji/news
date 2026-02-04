# -*- coding: utf-8 -*-
"""
بوت نشر الأخبار الآلي على تليجرام
Telegram Auto News Publisher Bot

يجلب الأخبار من مصادر RSS ويرسلها تلقائياً لقناة تليجرام
"""

import os
import sys
import time
import sqlite3
import asyncio
import feedparser
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# إصلاح مشكلة الترميز في Windows
if sys.platform == 'win32':
    try:
        # محاولة تعيين UTF-8 للـ stdout
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        # إذا فشل، استخدم encoding افتراضي
        pass

# تحميل الإعدادات من ملف .env
load_dotenv()

# استيراد إعدادات المصادر
from config import RSS_FEEDS, MAX_POSTS_PER_CHECK, NEWS_COOLDOWN_HOURS, SOURCE_EMOJIS, DEFAULT_EMOJI

# إعداد متغيرات البيئة
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", 30))

# التحقق من وجود الإعدادات الضرورية
if not BOT_TOKEN or BOT_TOKEN == "ضع_توكن_بوتك_هنا":
    print("❌ خطأ: يجب تعيين TELEGRAM_BOT_TOKEN في ملف .env")
    print("   احصل على التوكن من @BotFather في تليجرام")
    sys.exit(1)

if not CHANNEL_ID or CHANNEL_ID == "@اسم_قناتك_او_رقمها":
    print("❌ خطأ: يجب تعيين TELEGRAM_CHANNEL_ID في ملف .env")
    print("   استخدم @username أو ID القناة")
    sys.exit(1)

# مسار قاعدة البيانات
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news_bot.db')

# دالة طباعة آمنة للتعامل مع مشاكل الترميز في Windows
def safe_print(*args, **kwargs):
    """طباعة آمنة تتعامل مع مشاكل ترميز الإيموجيز في Windows"""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        # إذا فشلت، استبدل الإيموجيز برموز نصية
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # استبدال الإيموجيز الشائعة برموز نصية
                replacements = {
                    '⏰': '[TIME]', '📰': '[NEWS]', '🔍': '[SEARCH]', '✅': '[OK]',
                    '❌': '[ERROR]', '⚠️': '[WARNING]', '🎯': '[TARGET]', '📊': '[STATS]',
                    '📝': '[NOTE]', '🔗': '[LINK]', '📌': '[PIN]', '⏭️': '[SKIP]',
                    '📭': '[EMPTY]', '🗑️': '[DELETE]', '📡': '[SOURCE]', '📥': '[DOWNLOAD]',
                    '🚀': '[START]', '🛑': '[STOP]', '👋': '[BYE]', '🔌': '[CONNECT]',
                    '📋': '[LIST]'
                }
                for emoji, replacement in replacements.items():
                    arg = arg.replace(emoji, replacement)
            safe_args.append(arg)
        try:
            print(*safe_args, **kwargs)
        except:
            # إذا فشل مرة أخرى، اطبع بدون إيموجيز
            plain_args = [str(arg).encode('ascii', 'ignore').decode('ascii') if isinstance(arg, str) else arg for arg in safe_args]
            print(*plain_args, **kwargs)


def init_database():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول الأخبار المنشورة
    c.execute('''CREATE TABLE IF NOT EXISTS published_news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT UNIQUE,
                  source TEXT,
                  link TEXT,
                  published_at TIMESTAMP,
                  telegram_message_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول المصادر RSS
    c.execute('''CREATE TABLE IF NOT EXISTS rss_feeds
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  url TEXT NOT NULL UNIQUE,
                  is_active BOOLEAN DEFAULT 1,
                  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول التفاعلات (الإعجابات والنجوم)
    c.execute('''CREATE TABLE IF NOT EXISTS reactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  message_id INTEGER NOT NULL,
                  user_id INTEGER NOT NULL,
                  reaction_type TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(message_id, user_id, reaction_type))''')
    
    # نقل المصادر من config.py إلى قاعدة البيانات (إضافة المصادر الجديدة)
    try:
        feeds_count = c.execute("SELECT COUNT(*) FROM rss_feeds").fetchone()[0]
        added_count = 0
        for name, url in RSS_FEEDS.items():
            try:
                # التحقق إذا كان المصدر موجوداً
                existing = c.execute("SELECT id FROM rss_feeds WHERE name = ? OR url = ?", (name, url)).fetchone()
                if not existing:
                    c.execute("INSERT INTO rss_feeds (name, url, is_active) VALUES (?, ?, 1)", (name, url))
                    added_count += 1
            except Exception as e:
                safe_print(f"⚠️ خطأ في إضافة مصدر {name}: {e}")
        
        conn.commit()
        if added_count > 0:
            safe_print(f"📥 تم إضافة {added_count} مصدر جديد إلى قاعدة البيانات")
        if feeds_count == 0:
            safe_print(f"✅ تم نقل {len(RSS_FEEDS)} مصدر إلى قاعدة البيانات")
    except Exception as e:
        safe_print(f"⚠️ تحذير في نقل المصادر: {e}")
    
    conn.commit()
    conn.close()
    safe_print("✅ تم تهيئة قاعدة البيانات")


def is_news_published(title):
    """تحقق إذا كان الخبر منشوراً من قبل"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # تحقق إذا كان الخبر منشوراً خلال فترة الانتظار
    cooldown_time = datetime.now() - timedelta(hours=NEWS_COOLDOWN_HOURS)
    c.execute("""SELECT 1 FROM published_news 
                 WHERE title = ? AND created_at > ?""", (title, cooldown_time))
    result = c.fetchone()
    conn.close()
    return result is not None


def save_published_news(title, source, link, telegram_msg_id):
    """حفظ الخبر في قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO published_news 
                     (title, source, link, published_at, telegram_message_id) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (title, source, link, datetime.now(), telegram_msg_id))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        safe_print(f"❌ خطأ في حفظ الخبر: {e}")


def cleanup_old_news():
    """حذف الأخبار القديمة (أكبر من 7 أيام)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        week_ago = datetime.now() - timedelta(days=7)
        c.execute("DELETE FROM published_news WHERE created_at < ?", (week_ago,))
        deleted = c.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            safe_print(f"🗑️ تم حذف {deleted} خبر قديم")
    except sqlite3.Error as e:
        safe_print(f"❌ خطأ في تنظيف الأخبار القديمة: {e}")


def get_active_feeds():
    """جلب المصادر النشطة من قاعدة البيانات"""
    feeds = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name, url FROM rss_feeds WHERE is_active = 1")
        rows = c.fetchall()
        conn.close()
        for row in rows:
            feeds[row[0]] = row[1]
    except Exception as e:
        safe_print(f"❌ خطأ في جلب المصادر من قاعدة البيانات: {e}")
        # Fallback if DB fails
        from config import RSS_FEEDS as FALLBACK_FEEDS
        return FALLBACK_FEEDS
    return feeds

def fetch_latest_news():
    """جلب أحدث الأخبار من جميع المصادر"""
    all_news = []
    
    # استخدام المصادر من قاعدة البيانات بدلاً من الملف الثابت
    active_feeds = get_active_feeds()
    
    if not active_feeds:
        safe_print("⚠️ لا توجد مصادر نشطة في قاعدة البيانات")
        return []

    for source_name, rss_url in active_feeds.items():
        try:
            safe_print(f"🔍 جلب الأخبار من: {source_name}")
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                safe_print(f"⚠️ تحذير: مشكلة في قراءة RSS من {source_name}")
                continue
            
            entries = feed.entries[:10]  # آخر 10 أخبار من كل مصدر
            safe_print(f"   📰 وجدت {len(entries)} خبر")
            
            for entry in entries:
                if hasattr(entry, 'title') and entry.title:
                    title = entry.title.strip()
                    link = entry.link if hasattr(entry, 'link') else ''
                    
                    # الحصول على الوصف
                    description = ""
                    if hasattr(entry, 'summary'):
                        description = entry.summary
                    elif hasattr(entry, 'description'):
                        description = entry.description
                    
                    # تنظيف الوصف من HTML
                    import re
                    description = re.sub('<[^<]+?>', '', description)
                    description = description.strip()[:200]  # أول 200 حرف
                    
                    # الحصول على تاريخ النشر
                    published = ""
                    if hasattr(entry, 'published'):
                        published = entry.published
                    elif hasattr(entry, 'updated'):
                        published = entry.updated
                    else:
                        published = datetime.now().isoformat()
                    
                    # تنسيق الرسالة
                    message = format_news_message(title, description, link, source_name)
                    
                    all_news.append({
                        'title': title,
                        'message': message,
                        'source': source_name,
                        'link': link,
                        'published': published
                    })
                    
        except Exception as e:
            safe_print(f"❌ خطأ في جلب أخبار {source_name}: {e}")
    
    safe_print(f"📊 إجمالي الأخبار المجلوبة: {len(all_news)}")
    return all_news


def escape_markdown(text):
    """تهريب رموز Markdown الخاصة لتجنب أخطاء التنسيق"""
    if not text:
        return ""
    import re
    # تهريب الرموز الخاصة في Markdown
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_news_message(title, description, link, source_name):
    """تنسيق الخبر بشكل جميل للإرسال في تليجرام"""
    
    # تنظيف العنوان والوصف من HTML والرموز الخاصة
    import re
    if title:
        # إزالة HTML
        title = re.sub('<[^<]+?>', '', title)
        # إزالة رموز Markdown من العنوان (نستخدم نص عادي)
        title = title.replace('*', '').replace('_', '').replace('[', '').replace(']', '')
        title = title.strip()
    
    if description:
        # إزالة HTML
        description = re.sub('<[^<]+?>', '', description)
        description = description.strip()[:200]  # أول 200 حرف
        # تنظيف الوصف من الرموز الخاصة
        description = description.replace('*', '').replace('_', '').replace('[', '').replace(']', '')
    
    # اختيار الإيموجي حسب المصدر
    emoji = SOURCE_EMOJIS.get(source_name, DEFAULT_EMOJI)
    
    # بناء الرسالة بشكل احترافي وجميل
    message = f"{emoji} {source_name}\n"
    message += f"━━━━━━━━━━━━━━━━━━\n"
    message += f"📌 {title}\n"
    
    if description:
        message += f"\n📝 {description}...\n"
    
    # إزالة الروابط من الرسالة (لإخفاء preview)
    # if link:
    #     message += f"\n🔗 {link}"
    
    # إضافة الهاشتاجات (تنظيف الاسم)
    safe_source = source_name.replace(' ', '_').replace('-', '_')
    # إزالة أي رموز خاصة من الهاشتاج
    safe_source = re.sub(r'[^a-zA-Z0-9_أ-ي]', '', safe_source)
    message += f"\n\n#{safe_source} #أخبار #عاجل #أخبار_عربية"
    
    return message


async def post_to_telegram_async(bot, news_item, channel_error_shown=False):
    """إرسال الخبر إلى قناة التليجرام (غير متزامن)"""
    try:
        # تحقق إذا كان الخبر منشوراً من قبل
        if is_news_published(news_item['title']):
            safe_print(f"⏭️ تم نشر هذا الخبر مسبقاً: {news_item['title'][:50]}...")
            return None
        
        # إرسال الرسالة كنص عادي (بدون تنسيق) لتجنب جميع مشاكل Markdown/HTML
        import re
        clean_message = news_item['message']
        
        # إزالة أي تنسيقات HTML/Markdown قد تسبب مشاكل
        clean_message = re.sub('<[^<]+?>', '', clean_message)  # إزالة HTML tags
        
        # محاولة الإرسال مع معالجة Flood control
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # إنشاء أزرار التفاعل (إعجاب ونجوم)
                # سنستخدم معرف مؤقت ثم نحدثه بعد الحصول على message_id
                temp_message_id = int(time.time() * 1000)  # معرف مؤقت
                keyboard = [
                    [
                        InlineKeyboardButton("👍 إعجاب (0)", callback_data=f"like_{temp_message_id}"),
                        InlineKeyboardButton("⭐ نجوم (0)", callback_data=f"star_{temp_message_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=clean_message,
                    parse_mode=None,  # نص عادي بدون تنسيق
                    disable_web_page_preview=True,  # إخفاء preview الروابط
                    reply_markup=reply_markup  # إضافة أزرار التفاعل
                )
                
                # تحديث الأزرار بمعرف الرسالة الحقيقي
                try:
                    real_keyboard = [
                        [
                            InlineKeyboardButton("👍 إعجاب (0)", callback_data=f"like_{message.message_id}"),
                            InlineKeyboardButton("⭐ نجوم (0)", callback_data=f"star_{message.message_id}")
                        ]
                    ]
                    real_reply_markup = InlineKeyboardMarkup(real_keyboard)
                    await bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=message.message_id,
                        reply_markup=real_reply_markup
                    )
                except:
                    pass  # تجاهل الأخطاء في تحديث الأزرار
                
                break  # نجح الإرسال، اخرج من الحلقة
            except TelegramError as e:
                error_msg = str(e).lower()
                
                # معالجة Flood control - انتظر الوقت المطلوب ثم أعد المحاولة
                if "flood control" in error_msg or "retry in" in error_msg:
                    # استخراج وقت الانتظار من رسالة الخطأ
                    import re
                    retry_match = re.search(r'retry in (\d+)', error_msg, re.IGNORECASE)
                    if retry_match:
                        wait_time = int(retry_match.group(1)) + 2  # أضف ثانيتين إضافيتين للأمان
                        safe_print(f"⏳ Flood control: انتظر {wait_time} ثانية قبل إعادة المحاولة...")
                        await asyncio.sleep(wait_time)
                        retry_count += 1
                        continue
                    else:
                        # إذا لم نجد وقت محدد، انتظر 35 ثانية (الحد الأقصى عادة)
                        safe_print(f"⏳ Flood control: انتظر 35 ثانية...")
                        await asyncio.sleep(35)
                        retry_count += 1
                        continue
                
                # إذا كان الخطأ متعلقاً بعدم وجود البوت في القناة
                elif "not a member" in error_msg or "forbidden" in error_msg or "chat not found" in error_msg:
                    if not channel_error_shown:
                        safe_print(f"\n{'='*60}")
                        safe_print(f"⚠️ تحذير: البوت ليس عضو في القناة!")
                        safe_print(f"{'='*60}")
                        safe_print(f"📋 الخطوات المطلوبة:")
                        safe_print(f"   1) افتح قناة @ArabNewsAi في تليجرام")
                        safe_print(f"   2) اضغط على Settings (الإعدادات)")
                        safe_print(f"   3) اختر Administrators (المدراء)")
                        safe_print(f"   4) اضغط Add Administrator (إضافة مدير)")
                        safe_print(f"   5) ابحث عن @News2027bot وأضفه")
                        safe_print(f"   6) فعّل صلاحية 'Post Messages' (مهم جداً!)")
                        safe_print(f"   7) احفظ التغييرات")
                        safe_print(f"{'='*60}\n")
                    return None
                else:
                    safe_print(f"❌ خطأ في إرسال الرسالة: {e}")
                    return None
        
        # إذا فشلت جميع المحاولات
        if retry_count >= max_retries:
            safe_print(f"❌ فشل إرسال الرسالة بعد {max_retries} محاولات")
            return None
        
        # حفظ في قاعدة البيانات
        save_published_news(
            news_item['title'], 
            news_item['source'], 
            news_item['link'],
            message.message_id
        )
        
        safe_print(f"✅ تم النشر: {news_item['title'][:50]}...")
        return message.message_id
        
    except TelegramError as e:
        error_msg = str(e).lower()
        if ("not a member" in error_msg or "forbidden" in error_msg) and not channel_error_shown:
            safe_print(f"\n⚠️ تحذير: البوت ليس عضو في القناة. أضف @News2027bot كمدير في القناة @ArabNewsAi")
        elif "not a member" not in error_msg and "forbidden" not in error_msg:
            safe_print(f"❌ خطأ في إرسال الرسالة: {e}")
        return None
    except Exception as e:
        safe_print(f"❌ خطأ غير متوقع: {e}")
        return None


async def check_and_post_news_async():
    """المهمة الرئيسية: جلب ونشر الأخبار (غير متزامن)"""
    safe_print(f"\n{'='*50}")
    safe_print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - بدء جلب الأخبار...")
    safe_print(f"{'='*50}")
    
    # إنشاء البوت
    bot = Bot(token=BOT_TOKEN)
    
    # جلب الأخبار
    news_items = fetch_latest_news()
    
    if not news_items:
        safe_print("📭 لا توجد أخبار جديدة")
        return
    
    # نشر كل الأخبار الجديدة (بدون حد)
    posted_count = 0
    skipped_count = 0
    channel_error_shown = False  # لتتبع ما إذا تم عرض تحذير القناة
    
    safe_print(f"📊 جاهز لنشر {len(news_items)} خبر...")
    
    for news in news_items:
        success = await post_to_telegram_async(bot, news, channel_error_shown)
        if success:
            posted_count += 1
            await asyncio.sleep(3)  # انتظر 3 ثوان بين كل خبر لتجنب Flood control
        elif success is None:
            skipped_count += 1
            if not channel_error_shown:
                # تم عرض تحذير القناة
                channel_error_shown = True
    
    # تنظيف الأخبار القديمة
    cleanup_old_news()
    
    if posted_count == 0 and channel_error_shown:
        safe_print(f"\n⚠️ لم يتم نشر أي أخبار - تأكد من إضافة البوت كمدير في القناة")
    else:
        safe_print(f"\n🎯 تم نشر {posted_count} خبر جديد")
        if skipped_count > 0:
            safe_print(f"⏭️ تم تخطي {skipped_count} خبر (منشور مسبقاً)")
    safe_print(f"⏰ الفحص القادم بعد {INTERVAL} دقيقة")


def check_and_post_news():
    """غلاف متزامن للدالة غير المتزامنة"""
    asyncio.run(check_and_post_news_async())


def get_reaction_counts(message_id):
    """جلب عدد التفاعلات لكل رسالة"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # عدد الإعجابات
        likes = c.execute("SELECT COUNT(*) FROM reactions WHERE message_id = ? AND reaction_type = 'like'", 
                         (message_id,)).fetchone()[0]
        
        # عدد النجوم
        stars = c.execute("SELECT COUNT(*) FROM reactions WHERE message_id = ? AND reaction_type = 'star'", 
                         (message_id,)).fetchone()[0]
        
        conn.close()
        return likes, stars
    except:
        return 0, 0


def save_reaction(message_id, user_id, reaction_type):
    """حفظ تفاعل المستخدم"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # حذف التفاعل السابق للمستخدم على هذه الرسالة (إذا كان)
        c.execute("DELETE FROM reactions WHERE message_id = ? AND user_id = ?", 
                 (message_id, user_id))
        
        # إضافة التفاعل الجديد
        c.execute("INSERT INTO reactions (message_id, user_id, reaction_type) VALUES (?, ?, ?)",
                 (message_id, user_id, reaction_type))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        safe_print(f"Error saving reaction: {e}")
        return False


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تفاعلات المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    message_id = query.message.message_id
    data = query.data
    
    # استخراج message_id من callback_data
    try:
        if data.startswith("like_"):
            msg_id = int(data.split("_")[1])
            reaction_type = "like"
        elif data.startswith("star_"):
            msg_id = int(data.split("_")[1])
            reaction_type = "star"
        else:
            return
        
        # حفظ التفاعل
        save_reaction(msg_id, user_id, reaction_type)
        
        # جلب عدد التفاعلات المحدث
        likes, stars = get_reaction_counts(msg_id)
        
        # تحديث الأزرار بالأرقام المحدثة
        keyboard = [
            [
                InlineKeyboardButton(f"👍 إعجاب ({likes})", callback_data=f"like_{msg_id}"),
                InlineKeyboardButton(f"⭐ نجوم ({stars})", callback_data=f"star_{msg_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تحديث الرسالة
        try:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except:
            pass  # تجاهل الأخطاء في التحديث
    except Exception as e:
        safe_print(f"Error handling reaction: {e}")


async def test_bot_connection():
    """اختبار اتصال البوت"""
    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        safe_print(f"✅ تم الاتصال بالبوت: @{me.username}")
        return True
    except Exception as e:
        safe_print(f"❌ فشل الاتصال بالبوت: {e}")
        return False


def run_scheduler():
    """تشغيل الجدولة في thread منفصل"""
    while True:
        schedule.run_pending()
        time.sleep(30)  # فحص الجدول كل 30 ثانية


def main():
    """الدالة الرئيسية"""
    safe_print("=" * 60)
    safe_print("🚀 بوت نشر الأخبار الآلي على تليجرام")
    safe_print("=" * 60)
    safe_print(f"📡 المصادر المفعلة: {len(RSS_FEEDS)}")
    for name in RSS_FEEDS.keys():
        safe_print(f"   • {name}")
    safe_print(f"⏱️  الفحص كل: {INTERVAL} دقيقة")
    if MAX_POSTS_PER_CHECK >= 999:
        safe_print(f"📊 وضع النشر: كل الأخبار الجديدة (بدون حد)")
    else:
        safe_print(f"📊 الحد الأقصى للنشر: {MAX_POSTS_PER_CHECK} أخبار في كل مرة")
    safe_print(f"🔄 عدم تكرار الخبر قبل: {NEWS_COOLDOWN_HOURS} ساعة/ساعات")
    safe_print("=" * 60)
    
    # اختبار الاتصال
    safe_print("\n🔌 اختبار الاتصال بتليجرام...")
    if not asyncio.run(test_bot_connection()):
        safe_print("❌ فشل الاتصال. تحقق من التوكن وحاول مرة أخرى.")
        sys.exit(1)
    
    # تهيئة قاعدة البيانات
    init_database()
    
    # إنشاء Application لمعالجة التفاعلات
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handler للتفاعلات
    application.add_handler(CallbackQueryHandler(handle_reaction))
    
    # نشر أول مجموعة أخبار عند التشغيل
    safe_print("\n📰 جلب الأخبار الأولى...")
    check_and_post_news()
    
    # جدولة المهام
    schedule.every(INTERVAL).minutes.do(check_and_post_news)
    
    # تشغيل الجدولة في thread منفصل
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    safe_print("\n" + "=" * 60)
    safe_print("✅ البوت يعمل الآن مع معالج التفاعلات...")
    safe_print("   اضغط Ctrl+C للإيقاف")
    safe_print("=" * 60 + "\n")
    
    # تشغيل معالج التفاعلات (polling)
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        safe_print("\n\n🛑 تم إيقاف البوت بنجاح")
        safe_print("👋 إلى اللقاء!")


if __name__ == "__main__":
    main()
