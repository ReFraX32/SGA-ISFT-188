import re
import datetime
from typing import Optional, Tuple
from django.core.exceptions import ValidationError


def calcular_digito_cuil(cuil_limpio: str) -> int:
    multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(cuil_limpio[i]) * multiplicadores[i] for i in range(10))
    resto = suma % 11

    if resto == 0:
        return 0
    elif resto == 1:
        prefijo = cuil_limpio[:2]
        if prefijo == '20':
            return 9
        elif prefijo == '27':
            return 4
        else:
            return int(cuil_limpio[10]) if len(cuil_limpio) > 10 and cuil_limpio[10].isdigit() else 0
    else:
        return 11 - resto


def validar_cuil_detallado(cuil_raw: str, dni_val: Optional[str] = None) -> Tuple[str, Optional[str]]:
    cuil_str = str(cuil_raw or "").strip()
    if not cuil_str:
        return "", "El número de CUIL es obligatorio."

    if not re.match(r'^[\d\-\s]+$', cuil_str):
        return "", "El CUIL debe contener solo números y guiones."

    cuil_limpio = re.sub(r'[^\d]', '', cuil_str)
    if len(cuil_limpio) != 11:
        return "", f"El número de CUIL no es correcto: debe tener exactamente 11 números (ingresaste {len(cuil_limpio)}). Verificá que no falten dígitos."

    prefijo = cuil_limpio[:2]
    if prefijo not in ['20', '23', '24', '27']:
        return "", f"El número de CUIL no es correcto: el prefijo '{prefijo}' no es válido en Argentina. Los prefijos habilitados por ANSES son 20, 23, 24 o 27."

    if dni_val:
        dni_digitos = re.sub(r'[^\d]', '', str(dni_val)).zfill(8)
        cuil_dni_part = cuil_limpio[2:10]
        if cuil_dni_part != dni_digitos:
            return "", f"El número de CUIL no es correcto: los 8 dígitos centrales ({cuil_dni_part}) no coinciden con el DNI ingresado ({dni_digitos})."

    digito_esperado = calcular_digito_cuil(cuil_limpio)
    digito_ingresado = int(cuil_limpio[10])

    if digito_ingresado != digito_esperado:
        suma = sum(int(cuil_limpio[i]) * [5, 4, 3, 2, 7, 6, 5, 4, 3, 2][i] for i in range(10))
        resto = suma % 11
        if resto == 1 and prefijo in ['20', '27']:
            return "", (
                f"El número de CUIL no es correcto: para este DNI, por regla oficial de ANSES, "
                f"el prefijo debe ser 23 y terminar en {digito_esperado} (en lugar de terminar en {digito_ingresado}). "
                f"Por favor revisá tu constancia oficial de CUIL."
            )
        return "", (
            f"El número de CUIL no es correcto: el último número (dígito verificador {digito_ingresado}) "
            f"no coincide con el cálculo oficial de ANSES (para este DNI y prefijo debe terminar en {digito_esperado}). "
            f"Revisá si hay algún número mal tipeado en el DNI o en el CUIL."
        )

    cuil_formateado = f"{cuil_limpio[:2]}-{cuil_limpio[2:10]}-{cuil_limpio[10:]}"
    return cuil_formateado, None
