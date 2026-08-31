import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """
    Password ကို Bcrypt ဖြင့် Hash လုပ်ပေးသည်
    (bcrypt 72-byte limit ကို explicit ကိုင်တွယ်ထားသည်)
    """
    return bcrypt.hashpw(
        password.encode("utf-8")[:72],
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Plain Password နှင့် Hashed Password ကို တိုက်ဆိုင်စစ်ဆေးသည်
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# User မရှိသည့်အခါ password နှိုင်းယှဉ် Timing Attack (User Enumeration) ကို
# ကာကွယ်ရန် dummy bcrypt hash တစ်ခုစီ သုံးပါသည်။
_DUMMY_PASSWORD = "dummy-password-for-timing-attack"
DUMMY_BCRYPT_HASH = get_password_hash(_DUMMY_PASSWORD)


def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Access Token ထုတ်ပေးသည့် Function (Default Expiration Time: 60 min)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # Issued-At — token ထုတ်ချိန် မှတ်တမ်း
        "sub": str(subject),
        "type": "access",
        "jti": str(uuid.uuid4()),  # JWT ID - logout/revocation အတွက် လိုအပ်သည်
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Refresh Token ထုတ်ပေးသည့် Function (Default Expiration Time: 7 days)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # Issued-At — token ထုတ်ချိန် မှတ်တမ်း
        "sub": str(subject),
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # JWT ID - logout/revocation အတွက် လိုအပ်သည်
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    JWT Token ကို Verify လုပ်ပြီး Payload ပြန်ထုတ်ပေးသည်
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None