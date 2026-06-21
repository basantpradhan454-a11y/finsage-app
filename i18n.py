"""
FinSage i18n - Multi-language translation system
Supports: en, hi, te, ta, bn, mr, pa, gu, es, fr
Language is set during onboarding (before sign-up) and applied to entire platform.
"""
import streamlit as st

# ════════════════════════════════════════════════════════════════════════════
# TRANSLATION DICTIONARY
# ════════════════════════════════════════════════════════════════════════════
TRANSLATIONS = {
    # ── English (Default) ──
    "en": {
        # Navbar
        "tagline": "STOCK · CRYPTO · MEME COIN ANALYSIS",
        "menu": "MENU",
        "logout": "Logout",
        "back_dashboard": "Dashboard",

        # Nav groups
        "nav_charts": "CHARTS & ANALYSIS",
        "nav_ai_tools": "AI TOOLS",
        "nav_learn": "LEARN & EARN",
        "nav_tools": "TOOLS",

        # Nav descriptions
        "desc_sage": "AI Analysis + Voice + Drawing",
        "desc_tv": "Live candlestick charts",
        "desc_pro": "10 deep analysis modules",
        "desc_adv_intel": "Sentiment, Whale, On-chain",
        "desc_strat_bot": "Describe strategy -> AI backtests + voice",
        "desc_ai_assist": "Ask any trading question",
        "desc_chart_analyzer": "Upload & analyze screenshots",
        "desc_adv_analyzer": "10 indicators + Groq AI signals",
        "desc_risk": "Capital protection",
        "desc_academy": "AI Trading School",
        "desc_learn": "Course: Beginner to Advanced",
        "desc_marketplace": "Ebooks, Courses - 0% commission",
        "desc_screener": "Filter NSE + Crypto by signals",
        "desc_backtester": "Test RSI/MACD/EMA on history",
        "desc_options": "Delta Gamma Theta Vega",
        "desc_community": "Rate & share real trades",

        # Main tabs
        "tab_stocks": "Global Stocks",
        "tab_crypto": "Cryptocurrency",
        "tab_meme": "Meme Coins",

        # Stock tab
        "stock_title": "Global Stock Analysis",
        "stock_sub": "Real-time data from NSE India, US, UK, Germany, Japan & more.",
        "stock_input": "Enter Stock Ticker Symbol",
        "stock_placeholder": "e.g. AAPL, RELIANCE.NS, TCS.NS, TSLA",
        "quick_pick": "Quick Pick:",
        "analyze_stock": "Analyze Stock",
        "enter_ticker": "Enter a ticker symbol above and click Analyze Stock.",

        # Crypto tab
        "crypto_title": "Cryptocurrency Analysis",
        "crypto_sub": "Real-time data from CoinGecko - 100+ coins supported.",
        "crypto_input": "Enter Crypto Symbol",
        "crypto_placeholder": "e.g. BTC, ETH, SOL, BNB, ADA, XRP",
        "analyze_crypto": "Analyze Crypto",
        "enter_crypto": "Enter a crypto symbol and click Analyze Crypto.",

        # Meme tab
        "meme_title": "Meme Coin Analysis",
        "meme_warning": "HIGH RISK: Meme coins are purely speculative. Prices can crash 80-90% overnight. Only use money you can afford to lose completely.",
        "meme_input": "Enter Meme Coin Symbol",
        "meme_placeholder": "e.g. DOGE, SHIB, PEPE, FLOKI, BONK",
        "analyze_meme": "Analyze Meme Coin",
        "enter_meme": "Enter a meme coin symbol and click Analyze Meme Coin.",

        # Results
        "price": "Price",
        "change_24h": "24H",
        "mkt_cap": "Mkt Cap",
        "volatility": "Volatility",
        "risk": "Risk",
        "key_metrics": "Key Metrics",
        "full_report": "Full Analysis Report",
        "download_report": "Download Report (.md)",
        "price_chart": "30-Day Price Chart",

        # Common
        "fetching": "Fetching data for",
        "please_enter": "Please enter or select a symbol.",
        "disclaimer": "Disclaimer: Data from Yahoo Finance (yfinance). For educational purposes only. Not SEBI-registered investment advice.",
        "disclaimer_crypto": "Disclaimer: Data from CoinGecko. Crypto is highly volatile & unregulated by SEBI. Educational purposes only.",
        "disclaimer_meme": "Disclaimer: Meme coins are unregulated & highly speculative. Not SEBI advice. Never invest borrowed money in meme coins.",

        # Footer
        "footer_left": "FinSage - Global Financial Intelligence Platform",
        "footer_right": "Data: Yahoo Finance · CoinGecko  |  For educational purposes only",

        # Onboarding
        "ob_lang_title": "Choose Language",
        "ob_lang_sub": "Select the language for the entire platform",
        "ob_type_title": "Who are you?",
        "ob_type_sub": "We'll personalise your experience",
        "ob_signup_title": "Create your account",
        "ob_signup_sub": "Save progress, history & preferences",
        "ob_skip": "Enter as Guest (no account needed)",
        "ob_back": "Back",

        # Timeframe
        "timeframe": "Timeframe",
        "chart_type": "Type",
        "volume": "Volume",
    },

    # ── Hindi ──
    "hi": {
        "tagline": "स्टॉक · क्रिप्टो · मीम कॉइन विश्लेषण",
        "menu": "मेन्यू",
        "logout": "लॉग आउट",
        "back_dashboard": "डैशबोर्ड",

        "nav_charts": "चार्ट और विश्लेषण",
        "nav_ai_tools": "एआई टूल्स",
        "nav_learn": "सीखें और कमाएं",
        "nav_tools": "टूल्स",

        "desc_sage": "एआई विश्लेषण + वॉइस + ड्राइंग",
        "desc_tv": "लाइव कैंडलस्टिक चार्ट",
        "desc_pro": "10 गहन विश्लेषण मॉड्यूल",
        "desc_adv_intel": "सेंटीमेंट, व्हेल, ऑन-चेन",
        "desc_strat_bot": "रणनीति बताएं -> एआई बैकटेस्ट + वॉइस",
        "desc_ai_assist": "कोई भी ट्रेडिंग प्रश्न पूछें",
        "desc_chart_analyzer": "स्क्रीनशॉट अपलोड और विश्लेषण",
        "desc_adv_analyzer": "10 इंडिकेटर + Groq एआई सिग्नल",
        "desc_risk": "पूंजी सुरक्षा",
        "desc_academy": "एआई ट्रेडिंग स्कूल",
        "desc_learn": "कोर्स: शुरुआती से उन्नत",
        "desc_marketplace": "ईबुक, कोर्स - 0% कमीशन",
        "desc_screener": "एनएसई + क्रिप्टो सिग्नल फिल्टर",
        "desc_backtester": "आरएसआई/एमएसीडी/ईएमए टेस्ट",
        "desc_options": "डेल्टा गामा थीटा वेगा",
        "desc_community": "रेट और शेयर रियल ट्रेड्स",

        "tab_stocks": "वैश्विक स्टॉक",
        "tab_crypto": "क्रिप्टोकरेंसी",
        "tab_meme": "मीम कॉइन",

        "stock_title": "वैश्विक स्टॉक विश्लेषण",
        "stock_sub": "एनएसई इंडिया, यूएस, यूके, जर्मनी, जापान से रियल-टाइम डेटा।",
        "stock_input": "स्टॉक टिकर सिंबल दर्ज करें",
        "stock_placeholder": "जैसे AAPL, RELIANCE.NS, TCS.NS, TSLA",
        "quick_pick": "त्वरित चयन:",
        "analyze_stock": "स्टॉक विश्लेषण करें",
        "enter_ticker": "ऊपर टिकर सिंबल दर्ज करें और स्टॉक विश्लेषण करें पर क्लिक करें।",

        "crypto_title": "क्रिप्टोकरेंसी विश्लेषण",
        "crypto_sub": "CoinGecko से रियल-टाइम डेटा - 100+ कॉइन समर्थित।",
        "crypto_input": "क्रिप्टो सिंबल दर्ज करें",
        "crypto_placeholder": "जैसे BTC, ETH, SOL, BNB, ADA, XRP",
        "analyze_crypto": "क्रिप्टो विश्लेषण करें",
        "enter_crypto": "क्रिप्टो सिंबल दर्ज करें और क्रिप्टो विश्लेषण करें पर क्लिक करें।",

        "meme_title": "मीम कॉइन विश्लेषण",
        "meme_warning": "उच्च जोखिम: मीम कॉइन पूरी तरह से सट्टे के लिए हैं। कीमतें रातों-रात 80-90% गिर सकती हैं। केवल वही पैसा उपयोग करें जिसे आप पूरी तरह खोने का जोखिम उठा सकते हैं।",
        "meme_input": "मीम कॉइन सिंबल दर्ज करें",
        "meme_placeholder": "जैसे DOGE, SHIB, PEPE, FLOKI, BONK",
        "analyze_meme": "मीम कॉइन विश्लेषण करें",
        "enter_meme": "मीम कॉइन सिंबल दर्ज करें और विश्लेषण करें पर क्लिक करें।",

        "price": "कीमत",
        "change_24h": "24 घंटे",
        "mkt_cap": "मार्केट कैप",
        "volatility": "अस्थिरता",
        "risk": "जोखिम",
        "key_metrics": "प्रमुख मेट्रिक्स",
        "full_report": "पूर्ण विश्लेषण रिपोर्ट",
        "download_report": "रिपोर्ट डाउनलोड करें (.md)",
        "price_chart": "30-दिन मूल्य चार्ट",

        "fetching": "डेटा प्राप्त हो रहा है",
        "please_enter": "कृपया एक सिंबल दर्ज करें या चुनें।",
        "disclaimer": "अस्वीकरण: Yahoo Finance से डेटा। केवल शैक्षणिक उद्देश्य। SEBI पंजीकृत निवेश सलाह नहीं।",
        "disclaimer_crypto": "अस्वीकरण: CoinGecko से डेटा। क्रिप्टो अत्यधिक अस्थिर है। केवल शैक्षणिक उद्देश्य।",
        "disclaimer_meme": "अस्वीकरण: मीम कॉइन अनियंत्रित और अत्यधिक सट्टे के लिए हैं। SEBI सलाह नहीं।",

        "footer_left": "FinSage - वैश्विक वित्तीय खुफिया प्लेटफ़ॉर्म",
        "footer_right": "डेटा: Yahoo Finance · CoinGecko  |  केवल शैक्षणिक उद्देश्य",

        "ob_lang_title": "भाषा चुनें",
        "ob_lang_sub": "पूरे प्लेटफ़ॉर्म के लिए भाषा चुनें",
        "ob_type_title": "आप कौन हैं?",
        "ob_type_sub": "हम आपका अनुभव बेहतर बनाएंगे",
        "ob_signup_title": "अपना खाता बनाएं",
        "ob_signup_sub": "प्रगति व इतिहास सुरक्षित रखें",
        "ob_skip": "अभी Guest के रूप में जारी रखें",
        "ob_back": "वापस",

        "timeframe": "समय सीमा",
        "chart_type": "प्रकार",
        "volume": "वॉल्यूम",
    },

    # ── Telugu ──
    "te": {
        "tagline": "స్టాక్ · క్రిప్టో · మీమ్ కాయిన్ విశ్లేషణ",
        "menu": "మెనూ",
        "logout": "లాగ్ అవుట్",
        "back_dashboard": "డాష్‌బోర్డ్",

        "nav_charts": "చార్ట్‌లు & విశ్లేషణ",
        "nav_ai_tools": "AI టూల్స్",
        "nav_learn": "నేర్చుకోండి & సంపాదించండి",
        "nav_tools": "టూల్స్",

        "desc_sage": "AI విశ్లేషణ + వాయిస్ + డ్రాయింగ్",
        "desc_tv": "లైవ్ క్యాండిల్‌స్టిక్ చార్ట్‌లు",
        "desc_strat_bot": "వ్యూహం చెప్పండి -> AI బ్యాక్‌టెస్ట్ + వాయిస్",
        "desc_risk": "మూలధన రక్షణ",

        "tab_stocks": "గ్లోబల్ స్టాక్‌లు",
        "tab_crypto": "క్రిప్టోకరెన్సీ",
        "tab_meme": "మీమ్ కాయిన్‌లు",

        "stock_title": "గ్లోబల్ స్టాక్ విశ్లేషణ",
        "stock_sub": "NSE ఇండియా, US, UK, జర్మనీ, జపాన్ నుండి రియల్-టైమ్ డేటా.",
        "stock_input": "స్టాక్ టికర్ సింబల్ నమోదు చేయండి",
        "stock_placeholder": "ఉదా. AAPL, RELIANCE.NS, TCS.NS, TSLA",
        "quick_pick": "త్వరిత ఎంపిక:",
        "analyze_stock": "స్టాక్ విశ్లేషణ",
        "enter_ticker": "పైన టికర్ సింబల్ నమోదు చేసి విశ్లేషణ క్లిక్ చేయండి.",

        "crypto_title": "క్రిప్టోకరెన్సీ విశ్లేషణ",
        "crypto_sub": "CoinGecko నుండి రియల్-టైమ్ డేటా - 100+ కాయిన్‌లు.",
        "crypto_input": "క్రిప్టో సింబల్ నమోదు చేయండి",
        "crypto_placeholder": "ఉదా. BTC, ETH, SOL, BNB, ADA, XRP",
        "analyze_crypto": "క్రిప్టో విశ్లేషణ",
        "enter_crypto": "క్రిప్టో సింబల్ నమోదు చేసి విశ్లేషణ క్లిక్ చేయండి.",

        "meme_title": "మీమ్ కాయిన్ విశ్లేషణ",
        "meme_input": "మీమ్ కాయిన్ సింబల్ నమోదు చేయండి",
        "meme_placeholder": "ఉదా. DOGE, SHIB, PEPE, FLOKI, BONK",
        "analyze_meme": "మీమ్ కాయిన్ విశ్లేషణ",

        "price": "ధర",
        "change_24h": "24గం",
        "mkt_cap": "మార్కెట్ క్యాప్",
        "volatility": "అస్థిరత",
        "risk": "ప్రమాదం",
        "key_metrics": "ముఖ్యమైన మెట్రిక్స్",
        "full_report": "పూర్తి విశ్లేషణ నివేదిక",
        "download_report": "నివేదిక డౌన్‌లోడ్ (.md)",
        "price_chart": "30-రోజుల ధర చార్ట్",

        "fetching": "డేటా పొందుతోంది",
        "please_enter": "దయచేసి ఒక సింబల్ నమోదు చేయండి లేదా ఎంచుకోండి.",

        "footer_left": "FinSage - గ్లోబల్ ఫైనాన్షియల్ ఇంటెలిజెన్స్ ప్లాట్‌ఫారమ్",
        "footer_right": "డేటా: Yahoo Finance · CoinGecko  |  విద్యా ప్రయోజనాల కోసం మాత్రమే",

        "ob_lang_title": "భాష ఎంచుకోండి",
        "ob_lang_sub": "మొత్తం ప్లాట్‌ఫారమ్‌కు భాష ఎంచుకోండి",
        "ob_type_title": "మీరు ఎవరు?",
        "ob_type_sub": "మీ అనుభవాన్ని మెరుగుపరుస్తాము",
        "ob_signup_title": "ఖాతా సృష్టించండి",
        "ob_signup_sub": "మీ పురోగతి సేవ్ చేయబడుతుంది",
        "ob_back": "వెనక్కి",

        "timeframe": "సమయ వ్యవధి",
        "chart_type": "రకం",
        "volume": "వాల్యూమ్",
    },

    # ── Tamil ──
    "ta": {
        "tagline": "பங்கு · கிரிப்டோ · மீம் காயின் பகுப்பாய்வு",
        "menu": "மெனு",
        "logout": "வெளியேறு",
        "back_dashboard": "டாஷ்போர்டு",

        "nav_charts": "வரைபடங்கள் & பகுப்பாய்வு",
        "nav_ai_tools": "AI கருவிகள்",
        "nav_learn": "கற்று & சம்பாதி",
        "nav_tools": "கருவிகள்",

        "desc_sage": "AI பகுப்பாய்வு + குரல் + வரைதல்",
        "desc_tv": "நேரடி கேண்டில்ஸ்டிக் வரைபடங்கள்",
        "desc_strat_bot": "உத்தி சொல்லுங்கள் -> AI பேக்டெஸ்ட் + குரல்",
        "desc_risk": "மூலதன பாதுகாப்பு",

        "tab_stocks": "உலகளாவிய பங்குகள்",
        "tab_crypto": "கிரிப்டோகரன்ஸி",
        "tab_meme": "மீம் காயின்கள்",

        "stock_title": "உலகளாவிய பங்கு பகுப்பாய்வு",
        "stock_sub": "NSE இந்தியா, US, UK, ஜெர்மனி, ஜப்பான் இருந்து நேரடி தரவு.",
        "stock_input": "பங்கு டிக்கர் சின்பல் உள்ளிடவும்",
        "stock_placeholder": "உதா. AAPL, RELIANCE.NS, TCS.NS, TSLA",
        "quick_pick": "விரைவு தேர்வு:",
        "analyze_stock": "பங்கு பகுப்பாய்வு",
        "enter_ticker": "மேலே டிக்கர் உள்ளிட்டு பகுப்பாய்வு கிளிக் செய்யவும்.",

        "crypto_title": "கிரிப்டோகரன்ஸி பகுப்பாய்வு",
        "crypto_sub": "CoinGecko இருந்து நேரடி தரவு - 100+ காயின்கள்.",
        "crypto_input": "கிரிப்டோ சின்பல் உள்ளிடவும்",
        "crypto_placeholder": "உதா. BTC, ETH, SOL, BNB, ADA, XRP",
        "analyze_crypto": "கிரிப்டோ பகுப்பாய்வு",
        "enter_crypto": "கிரிப்டோ சின்பல் உள்ளிட்டு பகுப்பாய்வு கிளிக் செய்யவும்.",

        "meme_title": "மீம் காயின் பகுப்பாய்வு",
        "meme_input": "மீம் காயின் சின்பல் உள்ளிடவும்",
        "meme_placeholder": "உதா. DOGE, SHIB, PEPE, FLOKI, BONK",
        "analyze_meme": "மீம் காயின் பகுப்பாய்வு",

        "price": "விலை",
        "change_24h": "24ம",
        "mkt_cap": "சந்தை மூலதனம்",
        "volatility": "மாறுபாடு",
        "risk": "ஆபத்து",
        "key_metrics": "முக்கிய அளவீடுகள்",
        "full_report": "முழு பகுப்பாய்வு அறிக்கை",
        "download_report": "அறிக்கை பதிவிறக்கம் (.md)",
        "price_chart": "30-நாள் விலை வரைபடம்",

        "fetching": "தரவு பெறப்படுகிறது",
        "please_enter": "தயவுசெய்து ஒரு சின்பல் உள்ளிடவும்.",

        "footer_left": "FinSage - உலகளாவிய நிதி நுண்ணறிவு தளம்",
        "footer_right": "தரவு: Yahoo Finance · CoinGecko  |  கல்வி நோக்கங்களுக்காக மட்டுமே",

        "ob_lang_title": "மொழி தேர்ந்தெடுக்கவும்",
        "ob_lang_sub": "முழு தளத்திற்கும் மொழி தேர்ந்தெடுக்கவும்",
        "ob_type_title": "நீங்கள் யார்?",
        "ob_type_sub": "உங்கள் அனுபவத்தை மேம்படுத்துவோம்",
        "ob_signup_title": "கணக்கு உருவாக்கவும்",
        "ob_signup_sub": "உங்கள் முன்னேற்றம் சேமிக்கப்படும்",
        "ob_back": "பின்",

        "timeframe": "கால அளவு",
        "chart_type": "வகை",
        "volume": "தொகுதி",
    },

    # ── Bengali ──
    "bn": {
        "tagline": "স্টক · ক্রিপ্টো · মিম কয়েন বিশ্লেষণ",
        "menu": "মেনু",
        "logout": "লগ আউট",
        "back_dashboard": "ড্যাশবোর্ড",
        "nav_charts": "চার্ট ও বিশ্লেষণ",
        "nav_ai_tools": "AI টুলস",
        "nav_learn": "শিখুন ও উপার্জন করুন",
        "nav_tools": "টুলস",
        "tab_stocks": "বৈশ্বিক স্টক",
        "tab_crypto": "ক্রিপ্টোকারেন্সি",
        "tab_meme": "মিম কয়েন",
        "stock_title": "বৈশ্বিক স্টক বিশ্লেষণ",
        "stock_input": "স্টক টিকার সিম্বল লিখুন",
        "analyze_stock": "স্টক বিশ্লেষণ করুন",
        "crypto_title": "ক্রিপ্টোকারেন্সি বিশ্লেষণ",
        "crypto_input": "ক্রিপ্টো সিম্বল লিখুন",
        "analyze_crypto": "ক্রিপ্টো বিশ্লেষণ করুন",
        "meme_title": "মিম কয়েন বিশ্লেষণ",
        "meme_input": "মিম কয়েন সিম্বল লিখুন",
        "analyze_meme": "মিম কয়েন বিশ্লেষণ",
        "price": "মূল্য", "change_24h": "২৪ঘ", "mkt_cap": "মার্কেট ক্যাপ",
        "volatility": "অস্থিরতা", "risk": "ঝুঁকি",
        "key_metrics": "মূল মেট্রিক্স", "full_report": "সম্পূর্ণ বিশ্লেষণ রিপোর্ট",
        "download_report": "রিপোর্ট ডাউনলোড (.md)", "price_chart": "৩০-দিন মূল্য চার্ট",
        "fetching": "তথ্য আনা হচ্ছে", "please_enter": "একটি সিম্বল লিখুন।",
        "footer_left": "FinSage - বৈশ্বিক আর্থিক বুদ্ধিমত্তা প্ল্যাটফর্ম",
        "footer_right": "তথ্য: Yahoo Finance · CoinGecko  |  শিক্ষামূলক উদ্দেশ্যে",
        "ob_lang_title": "ভাষা নির্বাচন করুন", "ob_lang_sub": "পুরো প্ল্যাটফর্মের জন্য ভাষা নির্বাচন করুন",
        "ob_type_title": "আপনি কে?", "ob_signup_title": "অ্যাকাউন্ট তৈরি করুন",
        "ob_back": "পিছনে", "timeframe": "সময়সীমা", "chart_type": "ধরন", "volume": "ভলিউম",
    },

    # ── Marathi ──
    "mr": {
        "tagline": "स्टॉक · क्रिप्टो · मीम कॉइन विश्लेषण",
        "menu": "मेनू", "logout": "लॉग आउट", "back_dashboard": "डॅशबोर्ड",
        "nav_charts": "चार्ट आणि विश्लेषण", "nav_ai_tools": "AI साधने",
        "nav_learn": "शिका आणि कमवा", "nav_tools": "साधने",
        "tab_stocks": "जागतिक स्टॉक", "tab_crypto": "क्रिप्टोकरन्सी", "tab_meme": "मीम कॉइन",
        "stock_title": "जागतिक स्टॉक विश्लेषण", "stock_input": "स्टॉक टिकर सिंबल टाका",
        "analyze_stock": "स्टॉक विश्लेषण", "crypto_title": "क्रिप्टोकरन्सी विश्लेषण",
        "crypto_input": "क्रिप्टो सिंबल टाका", "analyze_crypto": "क्रिप्टो विश्लेषण",
        "meme_title": "मीम कॉइन विश्लेषण", "meme_input": "मीम कॉइन सिंबल टाका",
        "analyze_meme": "मीम कॉइन विश्लेषण",
        "price": "किंमत", "change_24h": "२४ता", "mkt_cap": "मार्केट कॅप",
        "volatility": "अस्थिरता", "risk": "जोखीम", "key_metrics": "मुख्य मेट्रिक्स",
        "full_report": "संपूर्ण विश्लेषण अहवाल", "download_report": "अहवाल डाउनलोड (.md)",
        "price_chart": "३०-दिवस किंमत चार्ट", "fetching": "डेटा मिळत आहे",
        "please_enter": "कृपया एक सिंबल टाका.",
        "footer_left": "FinSage - जागतिक आर्थिक बुद्धिमत्ता प्लॅटफॉर्म",
        "footer_right": "डेटा: Yahoo Finance · CoinGecko  |  शैक्षणिक हेतूंसाठी",
        "ob_lang_title": "भाषा निवडा", "ob_lang_sub": "संपूर्ण प्लॅटफॉर्मसाठी भाषा निवडा",
        "ob_type_title": "तुम्ही कोण आहात?", "ob_signup_title": "खाते तयार करा",
        "ob_back": "मागे", "timeframe": "वेळ अवधी", "chart_type": "प्रकार", "volume": "खंड",
    },

    # ── Punjabi ──
    "pa": {
        "tagline": "ਸਟਾਕ · ਕ੍ਰਿਪਟੋ · ਮੀਮ ਕੋਇਨ ਵਿਸ਼ਲੇਸ਼ਣ",
        "menu": "ਮੀਨੂ", "logout": "ਲਾਗ ਆਉਟ", "back_dashboard": "ਡੈਸ਼ਬੋਰਡ",
        "nav_charts": "ਚਾਰਟ ਅਤੇ ਵਿਸ਼ਲੇਸ਼ਣ", "nav_ai_tools": "AI ਟੂਲ",
        "nav_learn": "ਸਿੱਖੋ ਅਤੇ ਕਮਾਓ", "nav_tools": "ਟੂਲ",
        "tab_stocks": "ਵਿਸ਼ਵ ਸਟਾਕ", "tab_crypto": "ਕ੍ਰਿਪਟੋਕਰੰਸੀ", "tab_meme": "ਮੀਮ ਕੋਇਨ",
        "stock_title": "ਵਿਸ਼ਵ ਸਟਾਕ ਵਿਸ਼ਲੇਸ਼ਣ", "stock_input": "ਸਟਾਕ ਟਿਕਰ ਸਿੰਬਲ ਦਰਜ ਕਰੋ",
        "analyze_stock": "ਸਟਾਕ ਵਿਸ਼ਲੇਸ਼ਣ", "crypto_title": "ਕ੍ਰਿਪਟੋਕਰੰਸੀ ਵਿਸ਼ਲੇਸ਼ਣ",
        "crypto_input": "ਕ੍ਰਿਪਟੋ ਸਿੰਬਲ ਦਰਜ ਕਰੋ", "analyze_crypto": "ਕ੍ਰਿਪਟੋ ਵਿਸ਼ਲੇਸ਼ਣ",
        "meme_title": "ਮੀਮ ਕੋਇਨ ਵਿਸ਼ਲੇਸ਼ਣ", "meme_input": "ਮੀਮ ਕੋਇਨ ਸਿੰਬਲ ਦਰਜ ਕਰੋ",
        "analyze_meme": "ਮੀਮ ਕੋਇਨ ਵਿਸ਼ਲੇਸ਼ਣ",
        "price": "ਕੀਮਤ", "change_24h": "੨੪ਘੰ", "mkt_cap": "ਮਾਰਕੀਟ ਕੈਪ",
        "volatility": "ਅਸਥਿਰਤਾ", "risk": "ਜੋਖਮ", "key_metrics": "ਮੁੱਖ ਮੈਟ੍ਰਿਕਸ",
        "full_report": "ਪੂਰਾ ਵਿਸ਼ਲੇਸ਼ਣ ਰਿਪੋਰਟ", "download_report": "ਰਿਪੋਰਟ ਡਾਊਨਲੋਡ (.md)",
        "price_chart": "੩੦-ਦਿਨ ਕੀਮਤ ਚਾਰਟ", "fetching": "ਡੇਟਾ ਮਿਲ ਰਿਹਾ ਹੈ",
        "please_enter": "ਕਿਰਪਾ ਕਰਕੇ ਇੱਕ ਸਿੰਬਲ ਦਰਜ ਕਰੋ।",
        "footer_left": "FinSage - ਵਿਸ਼ਵ ਵਿੱਤੀ ਬੁੱਧੀ ਪਲੇਟਫਾਰਮ",
        "footer_right": "ਡੇਟਾ: Yahoo Finance · CoinGecko  |  ਵਿਦਿਅਕ ਉਦੇਸ਼ਾਂ ਲਈ",
        "ob_lang_title": "ਭਾਸ਼ਾ ਚੁਣੋ", "ob_lang_sub": "ਪੂਰੇ ਪਲੇਟਫਾਰਮ ਲਈ ਭਾਸ਼ਾ ਚੁਣੋ",
        "ob_type_title": "ਤੁਸੀਂ ਕੌਣ ਹੋ?", "ob_signup_title": "ਖਾਤਾ ਬਣਾਓ",
        "ob_back": "ਪਿੱਛੇ", "timeframe": "ਸਮਾਂ ਸੀਮਾ", "chart_type": "ਕਿਸਮ", "volume": "ਵਾਲੀਅਮ",
    },

    # ── Gujarati ──
    "gu": {
        "tagline": "સ્ટોક · ક્રિપ્ટો · મીમ કોઇન વિશ્લેષણ",
        "menu": "મેનુ", "logout": "લોગ આઉટ", "back_dashboard": "ડેશબોર્ડ",
        "nav_charts": "ચાર્ટ અને વિશ્લેષણ", "nav_ai_tools": "AI સાધનો",
        "nav_learn": "શીખો અને કમાઓ", "nav_tools": "સાધનો",
        "tab_stocks": "વૈશ્વિક સ્ટોક", "tab_crypto": "ક્રિપ્ટોકરન્સી", "tab_meme": "મીમ કોઇન",
        "stock_title": "વૈશ્વિક સ્ટોક વિશ્લેષણ", "stock_input": "સ્ટોક ટિકર સિમ્બોલ દાખલ કરો",
        "analyze_stock": "સ્ટોક વિશ્લેષણ", "crypto_title": "ક્રિપ્ટોકરન્સી વિશ્લેષણ",
        "crypto_input": "ક્રિપ્ટો સિમ્બોલ દાખલ કરો", "analyze_crypto": "ક્રિપ્ટો વિશ્લેષણ",
        "meme_title": "મીમ કોઇન વિશ્લેષણ", "meme_input": "મીમ કોઇન સિમ્બોલ દાખલ કરો",
        "analyze_meme": "મીમ કોઇન વિશ્લેષણ",
        "price": "કિંમત", "change_24h": "૨૪ક", "mkt_cap": "માર્કેટ કેપ",
        "volatility": "અસ્થિરતા", "risk": "જોખમ", "key_metrics": "મુખ્ય મેટ્રિક્સ",
        "full_report": "સંપૂર્ણ વિશ્લેષણ રિપોર્ટ", "download_report": "રિપોર્ટ ડાઉનલોડ (.md)",
        "price_chart": "૩૦-દિવસ કિંમત ચાર્ટ", "fetching": "ડેટા મળી રહ્યું છે",
        "please_enter": "કૃપા કરીને એક સિમ્બોલ દાખલ કરો.",
        "footer_left": "FinSage - વૈશ્વિક નાણાકીય બુદ્ધિ પ્લેટફોર્મ",
        "footer_right": "ડેટા: Yahoo Finance · CoinGecko  |  શૈક્ષણિક હેતુ માટે",
        "ob_lang_title": "ભાષા પસંદ કરો", "ob_lang_sub": "સંપૂર્ણ પ્લેટફોર્મ માટે ભાષા પસંદ કરો",
        "ob_type_title": "તમે કોણ છો?", "ob_signup_title": "ખાતું બનાવો",
        "ob_back": "પાછળ", "timeframe": "સમય મર્યાદા", "chart_type": "પ્રકાર", "volume": "વોલ્યુમ",
    },

    # ── Spanish ──
    "es": {
        "tagline": "ACCIONES · CRIPTO · ANÁLISIS DE MEME COINS",
        "menu": "MENÚ", "logout": "Cerrar sesión", "back_dashboard": "Panel",
        "nav_charts": "GRÁFICOS Y ANÁLISIS", "nav_ai_tools": "HERRAMIENTAS IA",
        "nav_learn": "APRENDER Y GANAR", "nav_tools": "HERRAMIENTAS",
        "tab_stocks": "Acciones Globales", "tab_crypto": "Criptomoneda", "tab_meme": "Meme Coins",
        "stock_title": "Análisis de Acciones Globales",
        "stock_input": "Ingrese Símbolo de Acción", "analyze_stock": "Analizar Acción",
        "crypto_title": "Análisis de Criptomonedas",
        "crypto_input": "Ingrese Símbolo Cripto", "analyze_crypto": "Analizar Cripto",
        "meme_title": "Análisis de Meme Coins",
        "meme_input": "Ingrese Símbolo Meme Coin", "analyze_meme": "Analizar Meme Coin",
        "price": "Precio", "change_24h": "24H", "mkt_cap": "Cap. Mercado",
        "volatility": "Volatilidad", "risk": "Riesgo", "key_metrics": "Métricas Clave",
        "full_report": "Informe Completo", "download_report": "Descargar Informe (.md)",
        "price_chart": "Gráfico de 30 Días", "fetching": "Obteniendo datos",
        "please_enter": "Por favor ingrese un símbolo.",
        "footer_left": "FinSage - Plataforma de Inteligencia Financiera Global",
        "footer_right": "Datos: Yahoo Finance · CoinGecko  |  Solo fines educativos",
        "ob_lang_title": "Elegir Idioma", "ob_lang_sub": "Seleccione el idioma para toda la plataforma",
        "ob_type_title": "¿Quién eres?", "ob_signup_title": "Crear cuenta",
        "ob_back": "Atrás", "timeframe": "Periodo", "chart_type": "Tipo", "volume": "Volumen",
    },

    # ── French ──
    "fr": {
        "tagline": "ACTIONS · CRYPTO · ANALYSE MEME COINS",
        "menu": "MENU", "logout": "Déconnexion", "back_dashboard": "Tableau de bord",
        "nav_charts": "GRAPHIQUES ET ANALYSE", "nav_ai_tools": "OUTILS IA",
        "nav_learn": "APPRENDRE ET GAGNER", "nav_tools": "OUTILS",
        "tab_stocks": "Actions Mondiales", "tab_crypto": "Cryptomonnaie", "tab_meme": "Meme Coins",
        "stock_title": "Analyse d'Actions Mondiales",
        "stock_input": "Entrer Symbole d'Action", "analyze_stock": "Analyser Action",
        "crypto_title": "Analyse de Cryptomonnaies",
        "crypto_input": "Entrer Symbole Crypto", "analyze_crypto": "Analyser Crypto",
        "meme_title": "Analyse de Meme Coins",
        "meme_input": "Entrer Symbole Meme Coin", "analyze_meme": "Analyser Meme Coin",
        "price": "Prix", "change_24h": "24H", "mkt_cap": "Cap. Marché",
        "volatility": "Volatilité", "risk": "Risque", "key_metrics": "Métriques Clés",
        "full_report": "Rapport Complet", "download_report": "Télécharger Rapport (.md)",
        "price_chart": "Graphique 30 Jours", "fetching": "Récupération des données",
        "please_enter": "Veuillez entrer un symbole.",
        "footer_left": "FinSage - Plateforme d'Intelligence Financière Mondiale",
        "footer_right": "Données: Yahoo Finance · CoinGecko  |  Fins éducatifs uniquement",
        "ob_lang_title": "Choisir Langue", "ob_lang_sub": "Sélectionnez la langue pour toute la plateforme",
        "ob_type_title": "Qui êtes-vous?", "ob_signup_title": "Créer un compte",
        "ob_back": "Retour", "timeframe": "Période", "chart_type": "Type", "volume": "Volume",
    },
}


def get_lang():
    """Get current language from session state."""
    return st.session_state.get("user_lang", "en")


def t(key):
    """Translate a key to the current language. Falls back to English."""
    lang = get_lang()
    d = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return d.get(key, TRANSLATIONS["en"].get(key, key))


def set_lang(code):
    """Set the language and persist it."""
    st.session_state.user_lang = code


# Language map for onboarding display
LANG_NAMES = {
    "en": "English", "hi": "हिंदी", "te": "తెలుగు", "ta": "தமிழ்",
    "bn": "বাংলা", "mr": "मराठी", "pa": "ਪੰਜਾਬੀ", "gu": "ગુજરાતી",
    "es": "Español", "fr": "Français",
}
