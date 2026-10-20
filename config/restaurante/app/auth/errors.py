class AuthError(Exception):
    """
    Excepción estándar para fallos de autenticación.
    Lleva el código de error en diccionario y el status_code HTTP (normalmente 401).
    """
    def __init__(self, error, status_code=401):
        self.error = error
        self.status_code = status_code
