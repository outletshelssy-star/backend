from __future__ import annotations

import math


def validate_inputs(temp_obs_f: float, lectura_api: float) -> None:
    temp_min = -58.0
    temp_max = 302.0
    if temp_obs_f < temp_min or temp_obs_f > temp_max:
        raise ValueError(
            f"Temperatura fuera del rango permitido: {temp_obs_f:.1f} °F"
        )
    if lectura_api <= 0:
        raise ValueError(f"Lectura API debe ser mayor que cero: {lectura_api}")
    densidad = (141.5 * 999.016) / (lectura_api + 131.5)
    if densidad < 610.6 or densidad > 1163.5:
        raise ValueError(
            f"Densidad calculada fuera de rango: {densidad:.1f} kg/m³"
        )


def api_60f_crude(temp_obs_f: float, lectura_api: float) -> float:
    """
    Calcula API a 60°F para crudo (ASTM 1298B).
    Basado en el script VBA proporcionado.
    """
    validate_inputs(temp_obs_f, lectura_api)

    presion = 0.0
    s60 = 0.01374979547

    densidad = (141.5 / (lectura_api + 131.5)) * 999.016
    hyc = 1 - (0.00001278 * (temp_obs_f - 60)) - (
        0.0000000062 * ((temp_obs_f - 60) ** 2)
    )
    densidad_hyc = densidad * hyc

    # Conversion ITS-90 a IPTS-68
    a1 = -0.148759
    a2 = -0.267408
    a3 = 1.08076
    a4 = 1.269056
    a5 = -4.089591
    a6 = -1.871251
    a7 = 7.438081
    a8 = -3.536296

    tc90 = (temp_obs_f - 32.0) / 1.8
    tau = tc90 / 630.0
    delta_tau = (
        a1
        + (a2 + (a3 + (a4 + (a5 + (a6 + (a7 + (a8 * tau)) * tau) * tau) * tau) * tau) * tau) * tau
    ) * tau
    tc68 = tc90 - delta_tau
    tf68 = (1.8 * tc68) + 32.0

    # Coeficientes para Crudo
    k0 = 341.0957
    k1 = 0.0
    k2 = 0.0
    tb = 60.0068749
    da = 2.0

    i = 0
    v = 1.0
    densidad_m = densidad_hyc

    while True:
        if i >= 15 or v < 0.0001:
            break

        a = (s60 / 2.0) * ((((k0 / densidad_m) + k1) / densidad_m) + k2)
        b = (2.0 * k0 + k1 * densidad_m) / (
            k0 + (k1 + k2 * densidad_m) * densidad_m
        )
        de = densidad_m * (
            1.0 + ((math.exp(a * (1.0 + 0.8 * a)) - 1.0) / (1.0 + a * (1.0 + 1.6 * a) * b))
        )
        alfa60 = ((k0 / de) + k1) * (1.0 / de) + k2
        dt = tf68 - tb
        ctl = math.exp(-alfa60 * dt * (1.0 + 0.8 * alfa60 * (dt + s60)))
        fp = math.exp(-1.9947 + 0.00013427 * tf68 + ((793920 + 2326 * tf68) / (de ** 2)))
        cpl = 1.0 / (1.0 - fp * presion * 0.00001)
        ctpl = ctl * cpl

        e_m = (densidad_hyc / (ctl * cpl)) - densidad_m
        dt2 = tf68 - 60.0
        d_tm = da * alfa60 * dt2 * (1.0 + 1.6 * alfa60 * dt2)
        d_pm = (
            (2.0 * cpl * presion * fp * (7.9392 + 0.02326 * tf68))
            / (densidad_m ** 2)
        )
        ddensidad_m = e_m / (1.0 + d_tm + d_pm)
        densidad_m = densidad_m + ddensidad_m

        spo = densidad_hyc - densidad_m * ctpl
        v = abs(spo)
        i += 1

    densidad60 = densidad_m
    api = (141.5 / (densidad60 / 999.016)) - 131.5
    return round(api, 1)
