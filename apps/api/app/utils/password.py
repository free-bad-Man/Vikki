"""
Утилиты для хеширования паролей.

Использует bcrypt.
"""
import bcrypt


def hash_password(password: str) -> str:
    """
    Хеширует пароль используя bcrypt.
    
    Args:
        password: Исходный пароль
        
    Returns:
        Хешированный пароль
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие пароля хешу.
    
    Args:
        plain_password: Исходный пароль
        hashed_password: Хешированный пароль
        
    Returns:
        True если пароль верный, False иначе
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8'),
        )
    except Exception:
        return False
