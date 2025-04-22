import random
from datetime import datetime, timedelta
from typing import Tuple

def generate_postamat_code() -> Tuple[str, datetime]:
    """
    Генерирует 6-значный числовой код и время его истечения через 3 минуты.
    Возвращает кортеж (код, время_истечения).
    """
    code = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=3)
    return code, expiry