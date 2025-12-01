from itertools import cycle

def validar_rut(rut):
    rut = rut.upper().strip()
    rut = rut.replace(".", "").replace("-", "")

    if len(rut) < 2:
        return False

    cuerpo, dv = rut[:-1], rut[-1:]

    if not cuerpo.isdigit():
        return False

    reverse_digits = map(int, reversed(cuerpo))
    factors = cycle(range(2, 8))
    total = sum(d * f for d, f in zip(reverse_digits, factors))

    res = 11 - (total % 11)
    if res == 11:
        dv_correcto = "0"
    elif res == 10:
        dv_correcto = "K"
    else:
        dv_correcto = str(res)

    return dv == dv_correcto
