import base64
import datetime as dt
import requests

def _base_url(env: str) -> str:
    return "https://sandbox.safaricom.co.ke" if env == "sandbox" else "https://api.safaricom.co.ke"

def get_access_token(app) -> str:
    env = app.config["MPESA_ENV"]
    url = _base_url(env) + "/oauth/v1/generate?grant_type=client_credentials"

    key = app.config["MPESA_CONSUMER_KEY"]
    secret = app.config["MPESA_CONSUMER_SECRET"]

    r = requests.get(url, auth=(key, secret), timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def stk_push(app, phone_254: str, amount: int):
    """
    Initiate STK push to phone. phone_254 must be like 2547XXXXXXXX.
    """
    env = app.config["MPESA_ENV"]
    url = _base_url(env) + "/mpesa/stkpush/v1/processrequest"

    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    shortcode = app.config["MPESA_SHORTCODE"]
    passkey = app.config["MPESA_PASSKEY"]
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    token = get_access_token(app)

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_254,
        "PartyB": shortcode,
        "PhoneNumber": phone_254,
        "CallBackURL": app.config["MPESA_CALLBACK_URL"],
        "AccountReference": app.config["MPESA_ACCOUNT_REF"],
        "TransactionDesc": app.config["MPESA_TX_DESC"],
    }

    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()
