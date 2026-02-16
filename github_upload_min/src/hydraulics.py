from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import math


G = 9.80665


@dataclass
class HydraulicResult:
    v_m_s: float
    i_m_per_m: float
    h_friction_m: float
    h_local_m: float
    h_total_m: float
    lambda_f: float
    dp_m: float
    re: float
    nu_m2_s: float


MATERIALS: Dict[str, Dict[str, str]] = {
    "steel_vgp": {
        "label": "Сталь водогазопроводная",
        "doc": "СП 30.13330.2020; ГОСТ 3262-75",
    },
    "steel_welded": {
        "label": "Сталь электросварная",
        "doc": "СП 30.13330.2020; ГОСТ 10704-91",
    },
    "cast_iron": {
        "label": "Чугун",
        "doc": "СП 30.13330.2020; ГОСТ ISO 2531-2022",
    },
    "plastic": {
        "label": "Пластик (PE/PVC)",
        "doc": "СП 30.13330.2020; ГОСТ Р 70628.2-2023",
    },
    "metal_plastic": {
        "label": "Металлопропилен (PP-R/AL/PP-R)",
        "doc": "СП 40-102-2000 (как справочный) + проверка по СП 30.13330.2020",
    },
    "fiberglass": {
        "label": "Стеклопластик",
        "doc": "СП 40-104-2001 (как справочный) + проверка по СП 30.13330.2020",
    },
    "polyplastic": {
        "label": "Полипропилен (PP-R)",
        "doc": "СП 41-109-2005 (как справочный) + проверка по СП 30.13330.2020",
    },
    "copper": {
        "label": "Медь",
        "doc": "СП 40-108-2004 (табл. 3.4, как справочный) + проверка по СП 30.13330.2020",
    },
}


# Наружный диаметр, мм -> толщина, мм
STEEL_DIMENSIONS: Dict[int, List[float]] = {
    15: [2.8, 3.2],
    20: [2.8, 3.2],
    25: [3.2, 4.0],
    32: [3.2, 4.0],
    40: [3.5, 4.0],
    50: [3.5, 4.0, 4.5],
    65: [4.0, 4.5],
    80: [4.0, 4.5],
    100: [4.5, 5.0],
    125: [4.5, 5.5],
    150: [5.0, 6.0],
    200: [6.0, 7.0],
}

CAST_IRON_DIMENSIONS: Dict[int, List[float]] = {
    65: [7.4, 8.3],
    80: [7.9, 8.8],
    100: [8.3, 9.0],
    125: [8.7, 9.5],
    150: [9.2, 10.0],
    200: [10.2, 11.0],
    250: [11.2, 12.0],
    300: [12.2, 13.0],
}

# ГОСТ ISO 2531-2022 (Приложение D): DN -> (DE, e_min, e_nom)
# Для интерфейса гидравлики используем выбор класса давления и DN,
# а толщину стенки задаем в диапазоне от e_min до e_nom.
CAST_IRON_BY_CLASS: Dict[str, Dict[int, Tuple[float, float, float]]] = {
    "C25": {
        350: (378.0, 3.4, 5.1),
        400: (429.0, 3.8, 5.5),
        450: (480.0, 4.3, 6.1),
        500: (532.0, 4.7, 6.5),
        600: (635.0, 5.7, 7.6),
        700: (738.0, 6.8, 8.8),
        800: (842.0, 7.5, 9.6),
        900: (945.0, 8.4, 10.6),
        1000: (1048.0, 9.3, 11.6),
        1100: (1152.0, 10.2, 12.6),
        1200: (1255.0, 11.1, 13.6),
        1400: (1462.0, 13.0, 15.7),
        1500: (1565.0, 13.9, 16.7),
        1600: (1668.0, 14.8, 17.7),
        1800: (1875.0, 16.6, 19.7),
        2000: (2082.0, 18.5, 21.8),
        2200: (2288.0, 20.3, 23.8),
        2400: (2495.0, 22.1, 25.8),
        2600: (2702.0, 24.0, 27.9),
    },
    "C30": {
        300: (326.0, 3.5, 5.1),
        350: (378.0, 4.6, 6.3),
        400: (429.0, 4.8, 6.5),
        450: (480.0, 5.1, 6.9),
        500: (532.0, 5.7, 7.5),
        600: (635.0, 6.8, 8.7),
        700: (738.0, 7.9, 9.9),
        800: (842.0, 9.0, 11.1),
        900: (945.0, 10.1, 12.3),
        1000: (1048.0, 11.1, 13.4),
        1100: (1152.0, 12.3, 14.7),
        1200: (1255.0, 13.3, 15.8),
        1400: (1462.0, 15.5, 18.2),
        1500: (1565.0, 16.6, 19.4),
        1600: (1668.0, 17.7, 20.6),
        1800: (1875.0, 19.9, 23.0),
        2000: (2082.0, 22.1, 25.4),
    },
    "C40": {
        40: (56.0, 3.0, 4.4),
        50: (66.0, 3.0, 4.4),
        60: (77.0, 3.0, 4.4),
        65: (82.0, 3.0, 4.4),
        80: (98.0, 3.0, 4.4),
        100: (118.0, 3.0, 4.4),
        125: (144.0, 3.0, 4.5),
        150: (170.0, 3.0, 4.5),
        200: (222.0, 3.2, 4.7),
        250: (274.0, 3.9, 5.5),
        300: (326.0, 4.6, 6.2),
        350: (378.0, 5.4, 7.1),
        400: (429.0, 6.1, 7.8),
        450: (480.0, 6.8, 8.6),
        500: (532.0, 7.5, 9.3),
        600: (635.0, 9.0, 10.9),
        700: (738.0, 10.4, 12.4),
        800: (842.0, 11.9, 14.0),
        900: (945.0, 13.3, 15.5),
        1000: (1048.0, 14.8, 17.1),
        1100: (1152.0, 16.3, 18.7),
        1200: (1255.0, 17.7, 20.2),
    },
    "C50": {
        40: (56.0, 3.0, 4.4),
        50: (66.0, 3.0, 4.4),
        60: (77.0, 3.0, 4.4),
        65: (82.0, 3.0, 4.4),
        80: (98.0, 3.0, 4.4),
        100: (118.0, 3.0, 4.4),
        125: (144.0, 3.0, 4.5),
        150: (170.0, 3.0, 4.5),
        200: (222.0, 3.9, 5.4),
        250: (274.0, 4.8, 6.4),
        300: (326.0, 5.8, 7.4),
        350: (378.0, 6.7, 8.4),
        400: (429.0, 7.6, 9.3),
        450: (480.0, 8.5, 10.3),
        500: (532.0, 9.4, 11.2),
        600: (635.0, 11.2, 13.1),
        700: (738.0, 13.0, 15.0),
        800: (842.0, 14.8, 16.9),
        900: (945.0, 16.6, 18.8),
        1000: (1048.0, 18.4, 20.7),
        1100: (1152.0, 20.3, 22.7),
    },
    "C64": {
        40: (56.0, 3.0, 4.4),
        50: (66.0, 3.0, 4.4),
        60: (77.0, 3.0, 4.4),
        65: (82.0, 3.0, 4.4),
        80: (98.0, 3.0, 4.4),
        100: (118.0, 3.0, 4.4),
        125: (144.0, 3.3, 4.8),
        150: (170.0, 3.8, 5.3),
        200: (222.0, 5.0, 6.5),
        250: (274.0, 6.2, 7.8),
        300: (326.0, 7.3, 8.9),
        350: (378.0, 8.5, 10.2),
        400: (429.0, 9.6, 11.3),
        450: (480.0, 10.8, 12.6),
        500: (532.0, 11.9, 13.7),
        600: (635.0, 14.2, 16.1),
        700: (738.0, 16.5, 18.5),
        800: (842.0, 18.9, 21.0),
        900: (945.0, 21.2, 23.4),
    },
    "C100": {
        40: (56.0, 3.0, 4.4),
        50: (66.0, 3.0, 4.4),
        60: (77.0, 3.0, 4.4),
        65: (82.0, 3.0, 4.4),
        80: (98.0, 3.4, 4.8),
        100: (118.0, 4.1, 5.5),
        125: (144.0, 5.0, 6.5),
        150: (170.0, 5.9, 7.4),
        200: (222.0, 7.7, 9.2),
        250: (274.0, 9.5, 11.1),
        300: (326.0, 11.3, 12.9),
        350: (378.0, 13.1, 14.8),
        400: (429.0, 14.8, 16.5),
        450: (480.0, 16.6, 18.4),
        500: (532.0, 18.4, 20.2),
        600: (635.0, 21.9, 23.8),
        700: (738.0, 25.5, 27.5),
    },
}

PLASTIC_DIMENSIONS: Dict[int, List[float]] = {
    20: [2.0, 2.3],
    25: [2.3, 2.8],
    32: [2.4, 3.0],
    40: [3.0, 3.7],
    50: [3.7, 4.6],
    63: [4.7, 5.8],
    75: [5.6, 6.8],
    90: [6.7, 8.2],
    110: [6.6, 10.0],
    125: [7.4, 11.4],
    140: [8.3, 12.7],
    160: [9.5, 14.6],
    200: [11.9, 18.2],
    250: [14.8, 22.7],
    315: [18.7, 28.6],
}

# СП 40-108-2004, табл. 3:
# допустимые сочетания dн/s берем только из ячеек, где задано предельное отклонение.
COPPER_DIMENSIONS: Dict[float, List[float]] = {
    6.0: [0.6, 0.8, 1.0],
    8.0: [0.6, 0.8, 1.0],
    10.0: [0.6, 0.7, 0.8, 1.0],
    12.0: [0.6, 0.8, 1.0],
    15.0: [0.7, 0.8, 1.0],
    18.0: [0.8, 1.0],
    22.0: [0.9, 1.0, 1.2, 1.5],
    28.0: [0.9, 1.0, 1.2, 1.5],
    35.0: [1.2, 1.5],
    42.0: [1.2, 1.5],
    54.0: [1.2, 1.5, 2.0],
    64.0: [2.0],
    66.7: [1.2],
    76.1: [1.5, 2.0],
    88.9: [2.0],
    108.0: [1.5, 2.5],
    133.0: [1.5, 3.0],
    159.0: [2.0, 3.0],
    219.0: [3.0],
    267.0: [3.0],
}

# СП 40-104-2001 (табл. 2, 3, 3а): внутренний диаметр -> (s_min, s_max), мм
FIBERGLASS_DIMENSIONS: Dict[str, Dict[str, Dict[int, Tuple[float, float]]]] = {
    # Таблица 2: трубы методов РПН/КППН, значения по рабочему давлению 1.0 и 1.6 МПа.
    "РПН/КППН": {
        "1.0 МПа": {
            50: (3.0, 3.0),
            80: (3.0, 3.0),
            110: (3.0, 3.0),
            150: (3.3, 3.3),
            215: (3.6, 3.6),
            265: (4.2, 4.2),
            315: (4.6, 4.6),
        },
        "1.6 МПа": {
            50: (3.0, 3.0),
            80: (3.0, 3.0),
            110: (3.0, 3.0),
            150: (3.3, 3.3),
            215: (3.6, 3.6),
            265: (4.8, 4.8),
            315: (5.4, 5.4),
        },
    },
    # Таблица 3: НППН.
    "НППН": {
        "0.6–1.6 МПа": {
            60: (3.0, 5.0),
            90: (3.0, 5.0),
            175: (4.0, 8.0),
            200: (4.0, 8.0),
            300: (5.0, 10.0),
            400: (6.0, 12.0),
        }
    },
    # Таблица 3а: базальтопластиковые трубы НППН.
    "Базальтопластик НППН": {
        "0.6–1.6 МПа": {
            50: (2.5, 3.2),
            65: (3.0, 3.5),
            80: (3.0, 3.7),
            100: (3.2, 4.0),
            122: (3.2, 4.0),
            150: (3.4, 4.2),
            175: (3.5, 4.4),
            200: (4.0, 4.4),
            300: (4.5, 5.2),
            400: (5.5, 6.2),
            500: (6.5, 7.0),
        }
    },
}
# Ряды диаметров: используются как набор наружных dн,
# толщина s рассчитывается автоматически от выбранной SDR/S-серии.
METAL_PLASTIC_ID_MM = [20, 25, 32, 40, 50, 63, 75, 90, 110]
POLYPLASTIC_ID_MM = [20, 25, 32, 40, 50, 63, 75, 90, 110, 125, 140, 160]

METAL_PLASTIC_DIMENSIONS: Dict[int, List[float]] = {d: [0.0] for d in METAL_PLASTIC_ID_MM}

POLYPLASTIC_DIMENSIONS: Dict[int, List[float]] = {d: [0.0] for d in POLYPLASTIC_ID_MM}

PLASTIC_PE_GRADES = [
    "ПЭ32 (MRS 3.2)",
    "ПЭ63 (MRS 6.3)",
    "ПЭ80 (MRS 8.0)",
    "ПЭ100 (MRS 10.0)",
]

PLASTIC_SDR_SERIES = [
    "SDR41 (S20)",
    "SDR33 (S16)",
    "SDR26 (S12.5)",
    "SDR21 (S10)",
    "SDR17.6 (S8.3)",
    "SDR17 (S8)",
    "SDR13.6 (S6.3)",
    "SDR11 (S5)",
    "SDR9 (S4)",
    "SDR7.4 (S3.2)",
    "SDR6 (S2.5)",
]

MLPEX_SDR_SERIES = [
    "SDR26 (S12.5)",
    "SDR21 (S10)",
    "SDR17.6 (S8.3)",
    "SDR17 (S8)",
    "SDR13.6 (S6.3)",
    "SDR11 (S5)",
    "SDR9 (S4)",
    "SDR7.4 (S3.2)",
    "SDR6 (S2.5)",
]


K_PRESETS = {
    "Объединенный, хозяйственно-питьевой и противопожарный (жилые и общественные здания)": 0.20,
    "Производственный водопровод": 0.20,
    "Хозяйственно-питьевой водопровод (жилые и общественные здания)": 0.30,
    "Объединенный, производственный и противопожарный": 0.15,
    "Противопожарный водопровод": 0.10,
    "Пользовательский": None,
}


def water_kinematic_viscosity_m2_s(temp_c: float) -> float:
    # Табличная интерполяция (приближение) для воды.
    pts = [
        (5.0, 1.52e-6),
        (10.0, 1.31e-6),
        (20.0, 1.00e-6),
        (30.0, 0.80e-6),
        (40.0, 0.66e-6),
        (50.0, 0.55e-6),
        (60.0, 0.47e-6),
        (70.0, 0.41e-6),
    ]
    x = float(temp_c)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            return y1 + (y2 - y1) * t
    return 1.0e-6


def _friction_smooth(re: float) -> float:
    if re <= 0:
        return 0.0
    if re < 2300:
        return 64.0 / re
    return 0.3164 / (re ** 0.25)


def _material_i_lambda(material: str, dp_m: float, v_m_s: float, nu_m2_s: float, is_new: bool) -> Tuple[float, float]:
    dp_m = max(dp_m, 1.0e-6)
    v_m_s = max(v_m_s, 0.0)
    nu_m2_s = max(nu_m2_s, 1.0e-9)
    re = (v_m_s * dp_m / nu_m2_s) if v_m_s > 0 else 0.0

    if material in ("steel_vgp", "steel_welded"):
        if is_new:
            lam = (0.312 / (dp_m ** 0.226)) * ((1.9e-6 + nu_m2_s / max(v_m_s, 1.0e-9)) ** 0.226)
            i_val = lam * (v_m_s**2) / (2.0 * G * dp_m)
            return i_val, lam
        ratio = v_m_s / nu_m2_s if nu_m2_s > 0 else 0.0
        if ratio >= 9.2e5:
            i_val = 0.021 * (v_m_s**2) / (dp_m ** 0.3)
            lam = i_val * 2.0 * G * dp_m / max(v_m_s**2, 1.0e-12)
            return i_val, lam
        i_val = (v_m_s**2) / (dp_m ** 0.3) * ((1.5e-6 + nu_m2_s / max(v_m_s, 1.0e-9)) ** 0.3)
        lam = i_val * 2.0 * G * dp_m / max(v_m_s**2, 1.0e-12)
        return i_val, lam

    if material == "cast_iron":
        if is_new:
            lam = (0.01424 / (dp_m ** 0.284)) * ((1.0 + 2.36 / max(v_m_s, 1.0e-9)) ** 0.284)
            i_val = lam * (v_m_s**2) / (2.0 * G * dp_m)
            return i_val, lam
        if v_m_s > 1.2:
            i_val = 0.00107 * (v_m_s**2) / (dp_m ** 1.3)
            lam = i_val * 2.0 * G * dp_m / max(v_m_s**2, 1.0e-12)
            return i_val, lam
        i_val = 0.000912 * (v_m_s**2) / (dp_m ** 1.3) * ((1.0 + 0.867 / max(v_m_s, 1.0e-9)) ** 0.3)
        lam = i_val * 2.0 * G * dp_m / max(v_m_s**2, 1.0e-12)
        return i_val, lam

    if material == "plastic":
        i_val = 0.000685 * (v_m_s ** 1.774) / (dp_m ** 1.226)
        lam = i_val * 2.0 * G * dp_m / max(v_m_s**2, 1.0e-12) if v_m_s > 0 else 0.0
        return i_val, lam

    if material == "fiberglass":
        lam = 0.0146 * ((max(v_m_s * dp_m, 1.0e-12)) ** -0.226)
        i_val = lam * (v_m_s**2) / (2.0 * G * dp_m)
        return i_val, lam

    # Металлопластик / полипластик / медь — гладкие трубы.
    lam = _friction_smooth(re)
    i_val = lam * (v_m_s**2) / (2.0 * G * dp_m) if dp_m > 0 else 0.0
    return i_val, lam


def calc_hydraulics(
    material: str,
    q_l_s: float,
    dp_m: float,
    length_m: float,
    temp_c: float,
    is_new: bool,
    local_mode: str,
    k_local: float,
    xi_sum: float,
) -> HydraulicResult:
    q_l_s = max(float(q_l_s), 0.0)
    dp_m = max(float(dp_m), 1.0e-6)
    length_m = max(float(length_m), 0.0)
    nu = water_kinematic_viscosity_m2_s(float(temp_c))
    area = math.pi * dp_m * dp_m / 4.0
    v = (q_l_s / 1000.0) / area if area > 0 else 0.0
    re = (v * dp_m / nu) if nu > 0 else 0.0
    i_val, lam = _material_i_lambda(material, dp_m, v, nu, is_new)
    h_f = i_val * length_m

    h_local = 0.0
    if local_mode == "k":
        h_local = h_f * max(float(k_local), 0.0)
    elif local_mode == "xi":
        h_local = max(float(xi_sum), 0.0) * (v * v) / (2.0 * G)

    return HydraulicResult(
        v_m_s=v,
        i_m_per_m=i_val,
        h_friction_m=h_f,
        h_local_m=h_local,
        h_total_m=h_f + h_local,
        lambda_f=lam,
        dp_m=dp_m,
        re=re,
        nu_m2_s=nu,
    )


def recommended_dp_candidates_mm(material: str) -> List[int]:
    if material in ("steel_vgp", "steel_welded"):
        return sorted(STEEL_DIMENSIONS.keys())
    if material == "cast_iron":
        return sorted(CAST_IRON_DIMENSIONS.keys())
    if material == "plastic":
        return sorted(PLASTIC_DIMENSIONS.keys())
    if material == "copper":
        return sorted(COPPER_DIMENSIONS.keys())
    if material == "fiberglass":
        return sorted(FIBERGLASS_DIMENSIONS.keys())
    if material == "metal_plastic":
        return list(METAL_PLASTIC_ID_MM)
    return list(POLYPLASTIC_ID_MM)


def find_recommended_diameter_mm(
    material: str,
    q_l_s: float,
    temp_c: float,
    is_new: bool,
    v_max_m_s: float = 3.0,
    v_min_m_s: float = 0.0,
) -> Tuple[int, List[Tuple[int, float, float]]]:
    # Возвращает выбранный dвн, мм и shortlist: (d, v, i)
    cands = recommended_dp_candidates_mm(material)
    rows: List[Tuple[int, float, float]] = []
    best = cands[-1] if cands else 100
    for dmm in cands:
        r = calc_hydraulics(
            material=material,
            q_l_s=q_l_s,
            dp_m=dmm / 1000.0,
            length_m=1.0,
            temp_c=temp_c,
            is_new=is_new,
            local_mode="none",
            k_local=0.0,
            xi_sum=0.0,
        )
        rows.append((dmm, r.v_m_s, r.i_m_per_m))
        if v_min_m_s <= r.v_m_s <= v_max_m_s:
            best = dmm
            break
        if r.v_m_s <= v_max_m_s:
            best = dmm
    return best, rows
