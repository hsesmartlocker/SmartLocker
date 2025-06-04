import random
from datetime import datetime, timedelta
from typing import Tuple


def generate_postamat_code() -> Tuple[str, datetime]:
    code = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=3)
    return code, expiry
