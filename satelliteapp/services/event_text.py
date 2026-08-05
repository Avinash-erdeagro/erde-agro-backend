"""Localized copy for satellite alerts and notifications.

The alert/notification *type* (e.g. ``CRITICAL_WATER_STRESS``) is the stable key;
this module owns the human-readable ``title`` / ``body`` in every supported
language. Both surfaces resolve text here so the copy stays in one place:

* push notifications  -> localized by the recipient's ``preferred_language``
* the events API      -> localized by ``request.language_code``

Templates may reference keys from the row's ``details_json`` using ``str.format``
syntax (e.g. ``{soil_moisture:.0f}``). Missing/invalid values degrade gracefully.

Languages: en, hi, mr, gu, pa, bn, kn, te, ta. A language missing entirely for a
type falls back to ``en`` at resolve time.
"""

import re

from satelliteapp.models import AlertType, NotificationType

_GENERIC_TITLE = "Farm Satellite Update"
_PLACEHOLDER_RE = re.compile(r"\{[^}]*\}")

SUPPORTED_LANGUAGES = ["en", "hi", "mr", "gu", "pa", "bn", "kn", "te", "ta"]


# type -> { language_code -> {"title": ..., "body": ...} }
# English (``en``) is the source of truth and the fallback for every language.
EVENT_TEXT = {
    # --- Notifications ---
    NotificationType.YOUR_FIELD_IS_DRYING: {
        "en": {"title": "Your field is drying", "body": "Soil moisture has dropped to {soil_moisture:.0f}%. Plan to irrigate soon."},
        "hi": {"title": "आपका खेत सूख रहा है", "body": "मिट्टी की नमी घटकर {soil_moisture:.0f}% रह गई है। जल्द सिंचाई की योजना बनाएं।"},
        "mr": {"title": "तुमचे शेत कोरडे होत आहे", "body": "जमिनीतील ओलावा {soil_moisture:.0f}% पर्यंत घसरला आहे. लवकरच पाणी देण्याची योजना करा."},
        "gu": {"title": "તમારું ખેતર સુકાઈ રહ્યું છે", "body": "જમીનની ભેજ ઘટીને {soil_moisture:.0f}% થઈ ગઈ છે. જલદી સિંચાઈની યોજના બનાવો."},
        "pa": {"title": "ਤੁਹਾਡਾ ਖੇਤ ਸੁੱਕ ਰਿਹਾ ਹੈ", "body": "ਮਿੱਟੀ ਦੀ ਨਮੀ ਘਟ ਕੇ {soil_moisture:.0f}% ਰਹਿ ਗਈ ਹੈ। ਜਲਦੀ ਸਿੰਚਾਈ ਦੀ ਯੋਜਨਾ ਬਣਾਓ।"},
        "bn": {"title": "আপনার জমি শুকিয়ে যাচ্ছে", "body": "মাটির আর্দ্রতা কমে {soil_moisture:.0f}% হয়েছে। শীঘ্রই সেচের পরিকল্পনা করুন।"},
        "kn": {"title": "ನಿಮ್ಮ ಹೊಲ ಒಣಗುತ್ತಿದೆ", "body": "ಮಣ್ಣಿನ ತೇವಾಂಶ {soil_moisture:.0f}%ಗೆ ಇಳಿದಿದೆ. ಶೀಘ್ರದಲ್ಲೇ ನೀರಾವರಿ ಯೋಜಿಸಿ."},
        "te": {"title": "మీ పొలం ఎండిపోతోంది", "body": "నేల తేమ {soil_moisture:.0f}%కి తగ్గింది. త్వరలో నీటిపారుదల ప్రణాళిక చేయండి."},
        "ta": {"title": "உங்கள் வயல் காய்ந்து வருகிறது", "body": "மண்ணின் ஈரப்பதம் {soil_moisture:.0f}% ஆகக் குறைந்துள்ளது. விரைவில் நீர்ப்பாசனம் திட்டமிடுங்கள்."},
    },
    NotificationType.MOISTURE_IS_IDEAL: {
        "en": {"title": "Soil moisture is ideal", "body": "Soil moisture is at a healthy {soil_moisture:.0f}%. No irrigation needed right now."},
        "hi": {"title": "मिट्टी की नमी उपयुक्त है", "body": "मिट्टी की नमी स्वस्थ {soil_moisture:.0f}% पर है। अभी सिंचाई की आवश्यकता नहीं है।"},
        "mr": {"title": "जमिनीतील ओलावा योग्य आहे", "body": "जमिनीतील ओलावा निरोगी {soil_moisture:.0f}% आहे. आत्ता पाणी देण्याची गरज नाही."},
        "gu": {"title": "જમીનની ભેજ યોગ્ય છે", "body": "જમીનની ભેજ તંદુરસ્ત {soil_moisture:.0f}% પર છે. અત્યારે સિંચાઈની જરૂર નથી."},
        "pa": {"title": "ਮਿੱਟੀ ਦੀ ਨਮੀ ਢੁੱਕਵੀਂ ਹੈ", "body": "ਮਿੱਟੀ ਦੀ ਨਮੀ ਸਿਹਤਮੰਦ {soil_moisture:.0f}% ਉੱਤੇ ਹੈ। ਹੁਣੇ ਸਿੰਚਾਈ ਦੀ ਲੋੜ ਨਹੀਂ ਹੈ।"},
        "bn": {"title": "মাটির আর্দ্রতা আদর্শ", "body": "মাটির আর্দ্রতা স্বাস্থ্যকর {soil_moisture:.0f}%-এ আছে। এখন সেচের প্রয়োজন নেই।"},
        "kn": {"title": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಸೂಕ್ತವಾಗಿದೆ", "body": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಆರೋಗ್ಯಕರ {soil_moisture:.0f}%ನಲ್ಲಿದೆ. ಈಗ ನೀರಾವರಿ ಅಗತ್ಯವಿಲ್ಲ."},
        "te": {"title": "నేల తేమ అనుకూలంగా ఉంది", "body": "నేల తేమ ఆరోగ్యకరమైన {soil_moisture:.0f}% వద్ద ఉంది. ప్రస్తుతం నీటిపారుదల అవసరం లేదు."},
        "ta": {"title": "மண் ஈரப்பதம் சரியாக உள்ளது", "body": "மண்ணின் ஈரப்பதம் ஆரோக்கியமான {soil_moisture:.0f}% இல் உள்ளது. இப்போது நீர்ப்பாசனம் தேவையில்லை."},
    },
    NotificationType.GROWTH_LOOKS_GREAT: {
        "en": {"title": "Crop growth looks great", "body": "Your crop growth is at {crop_growth:.0f}%. Keep up the good work."},
        "hi": {"title": "फसल की वृद्धि बहुत अच्छी है", "body": "आपकी फसल की वृद्धि {crop_growth:.0f}% पर है। इसी तरह अच्छा काम करते रहें।"},
        "mr": {"title": "पिकाची वाढ उत्तम आहे", "body": "तुमच्या पिकाची वाढ {crop_growth:.0f}% आहे. असेच चांगले काम सुरू ठेवा."},
        "gu": {"title": "પાકનો વિકાસ ઉત્તમ છે", "body": "તમારા પાકનો વિકાસ {crop_growth:.0f}% પર છે. આવું જ સારું કામ ચાલુ રાખો."},
        "pa": {"title": "ਫਸਲ ਦਾ ਵਾਧਾ ਵਧੀਆ ਹੈ", "body": "ਤੁਹਾਡੀ ਫਸਲ ਦਾ ਵਾਧਾ {crop_growth:.0f}% ਉੱਤੇ ਹੈ। ਇਸੇ ਤਰ੍ਹਾਂ ਵਧੀਆ ਕੰਮ ਜਾਰੀ ਰੱਖੋ।"},
        "bn": {"title": "ফসলের বৃদ্ধি চমৎকার", "body": "আপনার ফসলের বৃদ্ধি {crop_growth:.0f}%-এ আছে। এভাবেই ভালো কাজ চালিয়ে যান।"},
        "kn": {"title": "ಬೆಳೆಯ ಬೆಳವಣಿಗೆ ಉತ್ತಮವಾಗಿದೆ", "body": "ನಿಮ್ಮ ಬೆಳೆಯ ಬೆಳವಣಿಗೆ {crop_growth:.0f}%ನಲ್ಲಿದೆ. ಇದೇ ರೀತಿ ಉತ್ತಮ ಕೆಲಸ ಮುಂದುವರಿಸಿ."},
        "te": {"title": "పంట పెరుగుదల చాలా బాగుంది", "body": "మీ పంట పెరుగుదల {crop_growth:.0f}% వద్ద ఉంది. ఇలాగే మంచి పని కొనసాగించండి."},
        "ta": {"title": "பயிர் வளர்ச்சி சிறப்பாக உள்ளது", "body": "உங்கள் பயிர் வளர்ச்சி {crop_growth:.0f}% இல் உள்ளது. இதே போல் தொடருங்கள்."},
    },
    NotificationType.MONITOR_FIELD_CLOSELY_CROP_HEALTH: {
        "en": {"title": "Monitor your field closely", "body": "Crop growth is at {crop_growth:.0f}%. Keep a close eye on crop health."},
        "hi": {"title": "अपने खेत पर बारीकी से नज़र रखें", "body": "फसल की वृद्धि {crop_growth:.0f}% पर है। फसल की सेहत पर बारीकी से नज़र रखें।"},
        "mr": {"title": "तुमच्या शेतावर बारकाईने लक्ष ठेवा", "body": "पिकाची वाढ {crop_growth:.0f}% आहे. पिकाच्या आरोग्यावर बारकाईने लक्ष ठेवा."},
        "gu": {"title": "તમારા ખેતર પર બારીકાઈથી નજર રાખો", "body": "પાકનો વિકાસ {crop_growth:.0f}% પર છે. પાકના આરોગ્ય પર બારીકાઈથી નજર રાખો."},
        "pa": {"title": "ਆਪਣੇ ਖੇਤ 'ਤੇ ਧਿਆਨ ਨਾਲ ਨਜ਼ਰ ਰੱਖੋ", "body": "ਫਸਲ ਦਾ ਵਾਧਾ {crop_growth:.0f}% ਉੱਤੇ ਹੈ। ਫਸਲ ਦੀ ਸਿਹਤ 'ਤੇ ਧਿਆਨ ਨਾਲ ਨਜ਼ਰ ਰੱਖੋ।"},
        "bn": {"title": "আপনার জমির উপর নিবিড় নজর রাখুন", "body": "ফসলের বৃদ্ধি {crop_growth:.0f}%-এ আছে। ফসলের স্বাস্থ্যের উপর নিবিড় নজর রাখুন।"},
        "kn": {"title": "ನಿಮ್ಮ ಹೊಲವನ್ನು ಸೂಕ್ಷ್ಮವಾಗಿ ಗಮನಿಸಿ", "body": "ಬೆಳೆಯ ಬೆಳವಣಿಗೆ {crop_growth:.0f}%ನಲ್ಲಿದೆ. ಬೆಳೆಯ ಆರೋಗ್ಯವನ್ನು ಸೂಕ್ಷ್ಮವಾಗಿ ಗಮನಿಸಿ."},
        "te": {"title": "మీ పొలాన్ని నిశితంగా గమనించండి", "body": "పంట పెరుగుదల {crop_growth:.0f}% వద్ద ఉంది. పంట ఆరోగ్యాన్ని నిశితంగా గమనించండి."},
        "ta": {"title": "உங்கள் வயலை கூர்ந்து கவனியுங்கள்", "body": "பயிர் வளர்ச்சி {crop_growth:.0f}% இல் உள்ளது. பயிரின் ஆரோக்கியத்தை கூர்ந்து கவனியுங்கள்."},
    },
    NotificationType.MONITOR_FIELD_CLOSELY_FERTILIZER_LEVELS: {
        "en": {"title": "Check fertilizer levels", "body": "Leaf nitrogen is running low. Consider checking your fertilizer levels."},
        "hi": {"title": "खाद का स्तर जांचें", "body": "पत्तियों में नाइट्रोजन कम हो रहा है। अपनी खाद के स्तर की जांच करने पर विचार करें।"},
        "mr": {"title": "खताची पातळी तपासा", "body": "पानांतील नायट्रोजन कमी होत आहे. तुमच्या खताची पातळी तपासण्याचा विचार करा."},
        "gu": {"title": "ખાતરનું સ્તર તપાસો", "body": "પાંદડામાં નાઇટ્રોજન ઘટી રહ્યું છે. તમારા ખાતરનું સ્તર તપાસવાનું વિચારો."},
        "pa": {"title": "ਖਾਦ ਦਾ ਪੱਧਰ ਜਾਂਚੋ", "body": "ਪੱਤਿਆਂ ਵਿੱਚ ਨਾਈਟ੍ਰੋਜਨ ਘਟ ਰਿਹਾ ਹੈ। ਆਪਣੀ ਖਾਦ ਦੇ ਪੱਧਰ ਦੀ ਜਾਂਚ ਕਰਨ ਬਾਰੇ ਸੋਚੋ।"},
        "bn": {"title": "সারের মাত্রা পরীক্ষা করুন", "body": "পাতায় নাইট্রোজেন কমে যাচ্ছে। আপনার সারের মাত্রা পরীক্ষা করার কথা ভাবুন।"},
        "kn": {"title": "ಗೊಬ್ಬರದ ಮಟ್ಟವನ್ನು ಪರಿಶೀಲಿಸಿ", "body": "ಎಲೆಯಲ್ಲಿ ಸಾರಜನಕ ಕಡಿಮೆಯಾಗುತ್ತಿದೆ. ನಿಮ್ಮ ಗೊಬ್ಬರದ ಮಟ್ಟವನ್ನು ಪರಿಶೀಲಿಸುವುದನ್ನು ಪರಿಗಣಿಸಿ."},
        "te": {"title": "ఎరువుల స్థాయిని తనిఖీ చేయండి", "body": "ఆకులలో నత్రజని తగ్గుతోంది. మీ ఎరువుల స్థాయిని తనిఖీ చేయడాన్ని పరిగణించండి."},
        "ta": {"title": "உர அளவைச் சரிபார்க்கவும்", "body": "இலையில் நைட்ரஜன் குறைந்து வருகிறது. உங்கள் உர அளவைச் சரிபார்க்கக் கருதுங்கள்."},
    },
    NotificationType.PLAN_IRRIGATION_THIS_WEEK: {
        "en": {"title": "Plan irrigation this week", "body": "Irrigation is recommended this week. Open the app to see the schedule."},
        "hi": {"title": "इस सप्ताह सिंचाई की योजना बनाएं", "body": "इस सप्ताह सिंचाई की सलाह दी जाती है। समय-सारणी देखने के लिए ऐप खोलें।"},
        "mr": {"title": "या आठवड्यात सिंचनाची योजना करा", "body": "या आठवड्यात पाणी देण्याचा सल्ला आहे. वेळापत्रक पाहण्यासाठी ॲप उघडा."},
        "gu": {"title": "આ અઠવાડિયે સિંચાઈની યોજના બનાવો", "body": "આ અઠવાડિયે સિંચાઈની ભલામણ છે. સમયપત્રક જોવા માટે ઍપ ખોલો."},
        "pa": {"title": "ਇਸ ਹਫ਼ਤੇ ਸਿੰਚਾਈ ਦੀ ਯੋਜਨਾ ਬਣਾਓ", "body": "ਇਸ ਹਫ਼ਤੇ ਸਿੰਚਾਈ ਦੀ ਸਿਫ਼ਾਰਸ਼ ਕੀਤੀ ਜਾਂਦੀ ਹੈ। ਸਮਾਂ-ਸਾਰਣੀ ਵੇਖਣ ਲਈ ਐਪ ਖੋਲ੍ਹੋ।"},
        "bn": {"title": "এই সপ্তাহে সেচের পরিকল্পনা করুন", "body": "এই সপ্তাহে সেচের পরামর্শ দেওয়া হচ্ছে। সময়সূচি দেখতে অ্যাপ খুলুন।"},
        "kn": {"title": "ಈ ವಾರ ನೀರಾವರಿ ಯೋಜಿಸಿ", "body": "ಈ ವಾರ ನೀರಾವರಿ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ. ವೇಳಾಪಟ್ಟಿ ನೋಡಲು ಆ್ಯಪ್ ತೆರೆಯಿರಿ."},
        "te": {"title": "ఈ వారం నీటిపారుదల ప్రణాళిక చేయండి", "body": "ఈ వారం నీటిపారుదల సిఫార్సు చేయబడింది. షెడ్యూల్ చూడటానికి యాప్ తెరవండి."},
        "ta": {"title": "இந்த வாரம் நீர்ப்பாசனத்தைத் திட்டமிடுங்கள்", "body": "இந்த வாரம் நீர்ப்பாசனம் பரிந்துரைக்கப்படுகிறது. அட்டவணையைப் பார்க்க ஆப்பைத் திறக்கவும்."},
    },
    # --- Alerts ---
    AlertType.CRITICAL_WATER_STRESS: {
        "en": {"title": "Critical water stress", "body": "Soil moisture is critically low at {soil_moisture:.0f}%. Irrigate as soon as possible."},
        "hi": {"title": "गंभीर जल तनाव", "body": "मिट्टी की नमी गंभीर रूप से कम {soil_moisture:.0f}% है। जितनी जल्दी हो सके सिंचाई करें।"},
        "mr": {"title": "गंभीर पाणी ताण", "body": "जमिनीतील ओलावा धोकादायकरीत्या कमी {soil_moisture:.0f}% आहे. शक्य तितक्या लवकर पाणी द्या."},
        "gu": {"title": "ગંભીર જળ તણાવ", "body": "જમીનની ભેજ ગંભીર રીતે ઓછી {soil_moisture:.0f}% છે. શક્ય તેટલી જલદી સિંચાઈ કરો."},
        "pa": {"title": "ਗੰਭੀਰ ਪਾਣੀ ਦਾ ਤਣਾਅ", "body": "ਮਿੱਟੀ ਦੀ ਨਮੀ ਗੰਭੀਰ ਰੂਪ ਵਿੱਚ ਘੱਟ {soil_moisture:.0f}% ਹੈ। ਜਿੰਨੀ ਜਲਦੀ ਹੋ ਸਕੇ ਸਿੰਚਾਈ ਕਰੋ।"},
        "bn": {"title": "গুরুতর জলের চাপ", "body": "মাটির আর্দ্রতা গুরুতরভাবে কম {soil_moisture:.0f}%। যত তাড়াতাড়ি সম্ভব সেচ দিন।"},
        "kn": {"title": "ತೀವ್ರ ನೀರಿನ ಒತ್ತಡ", "body": "ಮಣ್ಣಿನ ತೇವಾಂಶ ತೀವ್ರವಾಗಿ ಕಡಿಮೆ {soil_moisture:.0f}% ಇದೆ. ಸಾಧ್ಯವಾದಷ್ಟು ಬೇಗ ನೀರಾವರಿ ಮಾಡಿ."},
        "te": {"title": "తీవ్ర నీటి ఒత్తిడి", "body": "నేల తేమ తీవ్రంగా తక్కువగా {soil_moisture:.0f}% ఉంది. వీలైనంత త్వరగా నీటిపారుదల చేయండి."},
        "ta": {"title": "கடுமையான நீர் அழுத்தம்", "body": "மண்ணின் ஈரப்பதம் ஆபத்தான அளவில் குறைவாக {soil_moisture:.0f}% உள்ளது. முடிந்தவரை விரைவில் நீர்ப்பாசனம் செய்யுங்கள்."},
    },
    AlertType.OVERWATERING_DETECTED: {
        "en": {"title": "Overwatering detected", "body": "Soil moisture is very high at {soil_moisture:.0f}%. Hold off on irrigation."},
        "hi": {"title": "अत्यधिक सिंचाई का पता चला", "body": "मिट्टी की नमी बहुत अधिक {soil_moisture:.0f}% है। फिलहाल सिंचाई रोक दें।"},
        "mr": {"title": "अतिरिक्त पाणी आढळले", "body": "जमिनीतील ओलावा खूप जास्त {soil_moisture:.0f}% आहे. सध्या पाणी देणे थांबवा."},
        "gu": {"title": "વધુ પડતી સિંચાઈ મળી", "body": "જમીનની ભેજ ખૂબ વધારે {soil_moisture:.0f}% છે. હાલ સિંચાઈ રોકો."},
        "pa": {"title": "ਵਾਧੂ ਸਿੰਚਾਈ ਦਾ ਪਤਾ ਲੱਗਾ", "body": "ਮਿੱਟੀ ਦੀ ਨਮੀ ਬਹੁਤ ਜ਼ਿਆਦਾ {soil_moisture:.0f}% ਹੈ। ਫ਼ਿਲਹਾਲ ਸਿੰਚਾਈ ਰੋਕ ਦਿਓ।"},
        "bn": {"title": "অতিরিক্ত সেচ শনাক্ত হয়েছে", "body": "মাটির আর্দ্রতা খুব বেশি {soil_moisture:.0f}%। আপাতত সেচ বন্ধ রাখুন।"},
        "kn": {"title": "ಅತಿಯಾದ ನೀರಾವರಿ ಪತ್ತೆಯಾಗಿದೆ", "body": "ಮಣ್ಣಿನ ತೇವಾಂಶ ತುಂಬಾ ಹೆಚ್ಚು {soil_moisture:.0f}% ಇದೆ. ಸದ್ಯಕ್ಕೆ ನೀರಾವರಿ ನಿಲ್ಲಿಸಿ."},
        "te": {"title": "అధిక నీటిపారుదల గుర్తించబడింది", "body": "నేల తేమ చాలా ఎక్కువగా {soil_moisture:.0f}% ఉంది. ప్రస్తుతానికి నీటిపారుదల ఆపండి."},
        "ta": {"title": "அதிக நீர்ப்பாசனம் கண்டறியப்பட்டது", "body": "மண்ணின் ஈரப்பதம் மிக அதிகமாக {soil_moisture:.0f}% உள்ளது. தற்போதைக்கு நீர்ப்பாசனத்தை நிறுத்துங்கள்."},
    },
    AlertType.CROP_HEALTH_DROPPING: {
        "en": {"title": "Crop health is dropping", "body": "Crop growth has been declining over the last {days_considered} readings. Inspect your field."},
        "hi": {"title": "फसल की सेहत गिर रही है", "body": "पिछली {days_considered} रीडिंग में फसल की वृद्धि घट रही है। अपने खेत का निरीक्षण करें।"},
        "mr": {"title": "पिकाचे आरोग्य घसरत आहे", "body": "मागील {days_considered} नोंदींमध्ये पिकाची वाढ घसरत आहे. तुमच्या शेताची पाहणी करा."},
        "gu": {"title": "પાકનું આરોગ્ય ઘટી રહ્યું છે", "body": "છેલ્લી {days_considered} નોંધોમાં પાકનો વિકાસ ઘટી રહ્યો છે. તમારા ખેતરનું નિરીક્ષણ કરો."},
        "pa": {"title": "ਫਸਲ ਦੀ ਸਿਹਤ ਡਿੱਗ ਰਹੀ ਹੈ", "body": "ਪਿਛਲੀਆਂ {days_considered} ਰੀਡਿੰਗਾਂ ਵਿੱਚ ਫਸਲ ਦਾ ਵਾਧਾ ਘਟ ਰਿਹਾ ਹੈ। ਆਪਣੇ ਖੇਤ ਦੀ ਜਾਂਚ ਕਰੋ।"},
        "bn": {"title": "ফসলের স্বাস্থ্য কমছে", "body": "গত {days_considered}টি রিডিংয়ে ফসলের বৃদ্ধি কমছে। আপনার জমি পরিদর্শন করুন।"},
        "kn": {"title": "ಬೆಳೆಯ ಆರೋಗ್ಯ ಕುಸಿಯುತ್ತಿದೆ", "body": "ಕಳೆದ {days_considered} ವಾಚನಗಳಲ್ಲಿ ಬೆಳೆಯ ಬೆಳವಣಿಗೆ ಕುಸಿಯುತ್ತಿದೆ. ನಿಮ್ಮ ಹೊಲವನ್ನು ಪರಿಶೀಲಿಸಿ."},
        "te": {"title": "పంట ఆరోగ్యం క్షీణిస్తోంది", "body": "గత {days_considered} రీడింగ్‌లలో పంట పెరుగుదల క్షీణిస్తోంది. మీ పొలాన్ని పరిశీలించండి."},
        "ta": {"title": "பயிர் ஆரோக்கியம் குறைந்து வருகிறது", "body": "கடந்த {days_considered} அளவீடுகளில் பயிர் வளர்ச்சி குறைந்து வருகிறது. உங்கள் வயலை ஆய்வு செய்யுங்கள்."},
    },
    AlertType.RAIN_ALERT_SKIP_IRRIGATION: {
        "en": {"title": "Rain expected — skip irrigation", "body": "Rain is forecast in the coming days. You can skip irrigation for now."},
        "hi": {"title": "बारिश की संभावना — सिंचाई न करें", "body": "आने वाले दिनों में बारिश का अनुमान है। फिलहाल आप सिंचाई छोड़ सकते हैं।"},
        "mr": {"title": "पावसाची शक्यता — पाणी देऊ नका", "body": "येत्या काही दिवसांत पावसाचा अंदाज आहे. सध्या तुम्ही पाणी देणे टाळू शकता."},
        "gu": {"title": "વરસાદની સંભાવના — સિંચાઈ ટાળો", "body": "આવનારા દિવસોમાં વરસાદની આગાહી છે. હાલ તમે સિંચાઈ ટાળી શકો છો."},
        "pa": {"title": "ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ — ਸਿੰਚਾਈ ਛੱਡੋ", "body": "ਆਉਣ ਵਾਲੇ ਦਿਨਾਂ ਵਿੱਚ ਮੀਂਹ ਦੀ ਭਵਿੱਖਬਾਣੀ ਹੈ। ਫ਼ਿਲਹਾਲ ਤੁਸੀਂ ਸਿੰਚਾਈ ਛੱਡ ਸਕਦੇ ਹੋ।"},
        "bn": {"title": "বৃষ্টির সম্ভাবনা — সেচ এড়িয়ে যান", "body": "আগামী দিনগুলিতে বৃষ্টির পূর্বাভাস রয়েছে। আপাতত আপনি সেচ এড়িয়ে যেতে পারেন।"},
        "kn": {"title": "ಮಳೆ ನಿರೀಕ್ಷೆ — ನೀರಾವರಿ ಬಿಟ್ಟುಬಿಡಿ", "body": "ಮುಂಬರುವ ದಿನಗಳಲ್ಲಿ ಮಳೆಯ ಮುನ್ಸೂಚನೆ ಇದೆ. ಸದ್ಯಕ್ಕೆ ನೀವು ನೀರಾವರಿ ಬಿಟ್ಟುಬಿಡಬಹುದು."},
        "te": {"title": "వర్షం అంచనా — నీటిపారుదల వదిలేయండి", "body": "రాబోయే రోజుల్లో వర్షం సూచన ఉంది. ప్రస్తుతానికి మీరు నీటిపారుదల వదిలేయవచ్చు."},
        "ta": {"title": "மழை எதிர்பார்ப்பு — நீர்ப்பாசனத்தைத் தவிர்க்கவும்", "body": "வரும் நாட்களில் மழை பெய்யும் என்று கணிக்கப்படுகிறது. தற்போதைக்கு நீங்கள் நீர்ப்பாசனத்தைத் தவிர்க்கலாம்."},
    },
}


def _fill(template: str, details_json: dict | None) -> str:
    """Interpolate ``details_json`` into ``template``; strip placeholders on failure."""
    try:
        return template.format(**(details_json or {}))
    except (KeyError, IndexError, ValueError):
        return _PLACEHOLDER_RE.sub("", template).replace("  ", " ").strip()


def resolve_event_text(event_type, details_json=None, language_code=None):
    """Return ``(title, body)`` for an alert/notification type in the given language.

    Falls back to English for unknown/untranslated languages and to a generic
    title for unknown types, so callers always get displayable text.
    """
    entry = EVENT_TEXT.get(event_type)
    if entry is None:
        pretty = str(event_type).replace("_", " ").title()
        return _GENERIC_TITLE, pretty

    templates = entry.get(language_code) or entry["en"]
    return _fill(templates["title"], details_json), _fill(templates["body"], details_json)
