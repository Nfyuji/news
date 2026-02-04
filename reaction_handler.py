# -*- coding: utf-8 -*-
"""
معالج التفاعلات (الإعجابات والنجوم)
Reaction Handler for Telegram Bot
"""

import os
import sqlite3
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# تحميل الإعدادات
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news_bot.db')


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
        print(f"Error saving reaction: {e}")
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
        print(f"Error handling reaction: {e}")


def main():
    """تشغيل معالج التفاعلات"""
    if not BOT_TOKEN:
        print("❌ خطأ: يجب تعيين TELEGRAM_BOT_TOKEN في ملف .env")
        return
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handler للتفاعلات
    application.add_handler(CallbackQueryHandler(handle_reaction))
    
    print("✅ معالج التفاعلات يعمل الآن...")
    print("   اضغط Ctrl+C للإيقاف")
    
    # تشغيل البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
