import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'payment_settings.json')

DEFAULT_SETTINGS = {
    "merchant_name": "Fresh Dairy Products",
    "merchant_upi_id": "41837498566@sbi",
    "razorpay_key_id": "rzp_test_dairy2025demo",
    "razorpay_key_secret": "test_secret_key_dairy_12345",
    "razorpay_webhook_secret": "whsec_dairy_demo_secret_123",
    "stripe_publishable_key": "pk_test_51DairyDemoPublishableKey123",
    "stripe_secret_key": "sk_test_51DairyDemoSecretKey123",
    "bank_name": "State Bank of India",
    "account_number": "41837498566",
    "ifsc_code": "SBIN0000784",
    "payment_mode": "test" # 'test' or 'live'
}

def load_payment_settings():
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=4)
        except Exception:
            pass
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_payment_settings(new_settings):
    current = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current.update(json.load(f))
        except Exception:
            pass
    current.update(new_settings)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=4)
    return current

def is_real_razorpay(cfg):
    key_id = cfg.get('razorpay_key_id', '').strip()
    key_secret = cfg.get('razorpay_key_secret', '').strip()
    return bool(key_id and key_secret and not key_id.startswith('rzp_test_dairy2025demo') and not key_secret.startswith('test_secret_key_dairy'))

def is_real_stripe(cfg):
    sec_key = cfg.get('stripe_secret_key', '').strip()
    return bool(sec_key and not sec_key.startswith('sk_test_51DairyDemoSecretKey'))

