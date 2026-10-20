from functools import wraps

def add_greattings(greattings=''):
    def add_greattings_decorador(f):
        @wraps(f)
        def wraper(*args, **kwargs):
            return f(greattings, *args, **kwargs)
        return wraper
    return add_greattings_decorador

@add_greattings()
def print_name(greattings, name, pepe, fransisco, juancho):
    print(greattings, name, pepe, fransisco, juancho)

print_name("Pepe", "Carlos", "Juancho", "Pepe")
