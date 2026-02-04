# -*- coding: utf-8 -*-
"""
إعدادات بوت الأخبار الآلي
News Bot Configuration
"""

# مصادر RSS (أضف أو عدل كما تريد)
RSS_FEEDS = {
    # قنوات دولية عربية
    "BBC Arabic": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "CNN Arabic": "https://arabic.cnn.com/rss.xml",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France 24 Arabic": "https://www.france24.com/ar/rss",
    "DW Arabic": "https://rss.dw.com/rdf/rss-ar-all",
    "TRT Arabic": "https://www.trtarabi.com/rss",
    "Sky News Arabia": "https://www.skynewsarabia.com/rss",
    
    # قنوات عربية رئيسية
    "الجزيرة": "https://www.aljazeera.net/xml/rss/all.xml",
    "العربية": "https://www.alarabiya.net/ar/rss.xml",
    "الشرق الأوسط": "https://aawsat.com/rss.xml",
    "النهار": "https://www.annahar.com/ar/rss.xml",
    
    # السعودية
    "الرياض": "https://www.alriyadh.com/rss.xml",
    "الوطن السعودية": "https://www.alwatan.com.sa/rss.xml",
    "عكاظ": "https://www.okaz.com.sa/rss.xml",
    "الشرق": "https://www.alsharq.net.sa/rss.xml",
    
    # الإمارات
    "البيان": "https://www.albayan.ae/rss.xml",
    "الإمارات اليوم": "https://www.emaratalyoum.com/rss.xml",
    "الخليج": "https://www.alkhaleej.ae/rss.xml",
    "الاتحاد": "https://www.alittihad.ae/rss.xml",
    "الراية": "https://www.raya.com/rss.xml",
    
    # مصر
    "المصري اليوم": "https://www.almasryalyoum.com/rss.xml",
    "اليوم السابع": "https://www.youm7.com/rss.xml",
    "الأهرام": "https://www.ahram.org.eg/rss.xml",
    "الوفد": "https://www.alwafd.news/rss.xml",
    "الوطن مصر": "https://www.elwatannews.com/rss.xml",
    "الشروق": "https://www.shorouknews.com/rss.xml",
    "الجمهورية": "https://www.algomhuria.net/rss.xml",
    
    # الكويت
    "الأنباء": "https://www.alanba.com.kw/rss.xml",
    "القبس": "https://www.alqabas.com/rss.xml",
    "الوطن الكويت": "https://www.alwatan.com.kw/rss.xml",
    "الرأي الكويت": "https://www.alraimedia.com/rss.xml",
    
    # البحرين
    "الوسط": "https://www.alwasat.com/rss.xml",
    "الأيام": "https://www.alayam.com/rss.xml",
    "الوطن البحرين": "https://www.alwatan.com.bh/rss.xml",
    
    # الأردن
    "الرأي الأردن": "https://www.alrai.com/rss.xml",
    "الدستور": "https://www.addustour.com/rss.xml",
    "الغد": "https://www.alghad.com/rss.xml",
    "السبيل": "https://www.assabeel.net/rss.xml",
    
    # لبنان
    "النهار لبنان": "https://www.annaharonline.com/rss.xml",
    
    # قنوات إخبارية إضافية
    "Middle East Eye": "https://www.middleeasteye.net/feed",
    "Al Monitor": "https://www.al-monitor.com/feed",
    "Asharq Al-Awsat": "https://www.asharq.com/feed",
}

# إعدادات التنسيق
MAX_POSTS_PER_CHECK = 999  # نشر كل الأخبار الجديدة (بدون حد)
NEWS_COOLDOWN_HOURS = 1  # لا تعيد نشر نفس الخبر قبل ساعة واحدة فقط

# إيموجيز المصادر
SOURCE_EMOJIS = {
    "BBC Arabic": "🇬🇧",
    "CNN Arabic": "🇺🇸",
    "RT Arabic": "🛰️",
    "France 24 Arabic": "🇫🇷",
    "DW Arabic": "🇩🇪",
    "TRT Arabic": "🇹🇷",
    "Sky News Arabia": "📡",
    "الجزيرة": "🌍",
    "العربية": "📰",
    "الشرق الأوسط": "📰",
    "النهار": "📰",
    "الرياض": "🇸🇦",
    "الوطن السعودية": "🇸🇦",
    "عكاظ": "🇸🇦",
    "الشرق": "🇸🇦",
    "البيان": "🇦🇪",
    "الإمارات اليوم": "🇦🇪",
    "الخليج": "🇦🇪",
    "الاتحاد": "🇦🇪",
    "الراية": "🇦🇪",
    "المصري اليوم": "🇪🇬",
    "اليوم السابع": "🇪🇬",
    "الأهرام": "🇪🇬",
    "الوفد": "🇪🇬",
    "الوطن مصر": "🇪🇬",
    "الشروق": "🇪🇬",
    "الجمهورية": "🇪🇬",
    "الأنباء": "🇰🇼",
    "القبس": "🇰🇼",
    "الوطن الكويت": "🇰🇼",
    "الرأي الكويت": "🇰🇼",
    "الوسط": "🇧🇭",
    "الأيام": "🇧🇭",
    "الوطن البحرين": "🇧🇭",
    "الرأي الأردن": "🇯🇴",
    "الدستور": "🇯🇴",
    "الغد": "🇯🇴",
    "السبيل": "🇯🇴",
    "النهار لبنان": "🇱🇧",
    "Middle East Eye": "🌐",
    "Al Monitor": "🌐",
    "Asharq Al-Awsat": "📰",
}

# الإيموجي الافتراضي للمصادر الجديدة
DEFAULT_EMOJI = "📢"
