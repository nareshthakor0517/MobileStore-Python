from itsdangerous import URLSafeTimedSerializer
from django.conf import settings

def generate_payment_token(data: dict) -> str:
    s = URLSafeTimedSerializer(settings.SECRET_KEY)
    return s.dumps(data)

def verify_payment_token(token: str, max_age=300):
    """
    max_age = token valid time (5 minutes)
    """
    s = URLSafeTimedSerializer(settings.SECRET_KEY)
    try:
        return s.loads(token, max_age=max_age)
    except Exception:
        return None
