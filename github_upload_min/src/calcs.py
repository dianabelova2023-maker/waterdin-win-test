from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class WaterInputs:
    # Базовый "универсальный" ввод (не нормативный СП, а понятный старт).
    residents: int
    cold_l_per_person_day: float
    hot_l_per_person_day: float
    peak_hour_factor: float  # коэффициент максимального часа (обычно 1.2–2.5 в зависимости от объекта)


@dataclass
class HeatElement:
    name: str
    area_m2: float
    u_w_m2k: float  # коэффициент теплопередачи U
    delta_t_k: float = 0.0  # поле сохранено для обратной совместимости интерфейса


@dataclass
class WaterConsumer:
    name: str
    unit: str
    count: float
    cold_l_per_unit_day: float
    hot_l_per_unit_day: float
    use_prod_water_source: bool = False
    q_u_total_l_day: float = 0.0
    q_u_hot_l_day: float = 0.0
    q_hr_total_l_h: float = 0.0
    q_hr_hot_l_h: float = 0.0
    q0_total_l_s: float = 0.0
    q0_total_l_h: float = 0.0
    q0_spec_l_s: float = 0.0
    q0_spec_l_h: float = 0.0
    t_hours: float = 24.0
    source_doc: str = ""
    source_item: str = ""
    object_kind: str = "nonproduction"
    sewer_target_override: str = ""  # "", "domestic", "production"
    water_quality_override: str = ""
    np_source_override: str = ""  # "", "Горводопровод", "Скважины", "Техвода", "Оборотные системы"
    np_sewer_override: str = ""   # "", "Хоз.-быт.", "Норм.-чистые", "Загр. мех./мин.", "Загр. хим./орг."


@dataclass
class LegacyWaterRow:
    section: str  # cold|hot|total
    consumer_name: str
    fixtures_np: float
    users_u: float
    q_u_day: float  # л/(ед*сут)
    q_u_hr: float  # л/(ед*ч)
    q0: float  # л/с
    q0hr: float  # л/ч
    alpha: float
    alpha_hr: float
    source_doc: str = ""
    source_item: str = ""


def calc_water(inputs: WaterInputs) -> Dict[str, float]:
    """
    ВНИМАНИЕ: это стартовая (упрощённая) модель.
    Позже заменим на методики и коэффициенты по СП 30.13330.2020 и т.д.
    """
    res = max(int(inputs.residents), 0)

    cold_l_day = res * float(inputs.cold_l_per_person_day)
    hot_l_day = res * float(inputs.hot_l_per_person_day)
    total_l_day = cold_l_day + hot_l_day

    # Средний час
    avg_l_hour = total_l_day / 24.0
    # Максимальный час
    max_l_hour = avg_l_hour * float(inputs.peak_hour_factor)

    # Переводы
    cold_m3_day = cold_l_day / 1000.0
    hot_m3_day = hot_l_day / 1000.0
    total_m3_day = total_l_day / 1000.0

    max_m3_hour = max_l_hour / 1000.0
    max_l_sec = max_l_hour / 3600.0  # л/с (макс. час / 3600)

    return {
        "cold_m3_day": cold_m3_day,
        "hot_m3_day": hot_m3_day,
        "total_m3_day": total_m3_day,
        "max_m3_hour": max_m3_hour,
        "max_l_sec": max_l_sec,
    }


def calc_water_by_consumers(consumers: List[WaterConsumer], peak_hour_factor: float) -> Dict[str, float | List[Dict[str, float | str]]]:
    """
    Универсальный расчет по набору потребителей:
    Qсут = Σ(Ni * qi), где:
    - Ni: число единиц потребителя (чел, место, койка и т.д.)
    - qi: удельная норма, л/ед·сут
    """
    rows: List[Dict[str, float | str]] = []
    cold_l_day_total = 0.0
    hot_l_day_total = 0.0

    for item in consumers:
        n = max(float(item.count), 0.0)
        q_cold = max(float(item.cold_l_per_unit_day), 0.0)
        q_hot = max(float(item.hot_l_per_unit_day), 0.0)

        cold_l_day = n * q_cold
        hot_l_day = n * q_hot
        total_l_day = cold_l_day + hot_l_day

        cold_l_day_total += cold_l_day
        hot_l_day_total += hot_l_day

        rows.append(
            {
                "name": item.name,
                "unit": item.unit,
                "count": n,
                "cold_l_per_unit_day": q_cold,
                "hot_l_per_unit_day": q_hot,
                "cold_m3_day": cold_l_day / 1000.0,
                "hot_m3_day": hot_l_day / 1000.0,
                "total_m3_day": total_l_day / 1000.0,
                "source_doc": item.source_doc.strip(),
                "source_item": item.source_item.strip(),
                "object_kind": (item.object_kind or "nonproduction").strip().lower(),
            }
        )

    total_l_day = cold_l_day_total + hot_l_day_total
    avg_l_hour = total_l_day / 24.0
    k_hour = max(float(peak_hour_factor), 1.0)
    max_l_hour = avg_l_hour * k_hour

    return {
        "cold_m3_day": cold_l_day_total / 1000.0,
        "hot_m3_day": hot_l_day_total / 1000.0,
        "total_m3_day": total_l_day / 1000.0,
        "max_m3_hour": max_l_hour / 1000.0,
        "max_l_sec": max_l_hour / 3600.0,
        "rows": rows,
    }


def calc_water_by_consumers_advanced(
    consumers: List[WaterConsumer],
    peak_hour_factor: float,
    day_factor: float,
    reserve_factor: float,
    leakage_percent: float,
    max_day_factor: float = 1.1,
    wastewater_factor: float = 1.0,
) -> Dict[str, float | List[Dict[str, float | str]]]:
    """
    Расчет воды с дополнительными коэффициентами:
    - day_factor: коэффициент суточной неравномерности
    - reserve_factor: коэффициент запаса
    - leakage_percent: потери/утечки в процентах
    """
    def _infer_prod_sewer_target(name: str, override: str) -> str:
        ov = (override or "").strip().lower()
        if ov in ("domestic", "production"):
            return ov
        n = (name or "").strip().lower()
        production_markers = [
            "цех",
            "завод",
            "производ",
            "пищеблок",
            "столов",
            "прачеч",
            "лаборатор",
            "бассейн",
            "душевые в бытовых помещениях промышленных предприятий",
            "инфекцион",
            "патолого",
            "морг",
            "кров",
        ]
        if any(m in n for m in production_markers):
            return "production"
        return "domestic"

    # Приложение Б СП 30.13330.2020:
    # B.1: P>0.1 и N<=200  -> alpha=f(N,P)
    # B.2: P<=0.1 при любом N, а также P>0.1 и N>200 -> alpha=f(NP)
    _B1_P_GRID = [0.1, 0.125, 0.16, 0.2, 0.25, 0.316, 0.4, 0.5, 0.63, 0.8]
    _B1_TABLE: Dict[int, List[float]] = {
        2: [0.39, 0.39, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40],
        4: [0.58, 0.62, 0.65, 0.69, 0.72, 0.76, 0.78, 0.80, 0.80, 0.80],
        6: [0.72, 0.78, 0.83, 0.90, 0.97, 1.04, 1.11, 1.16, 1.20, 1.20],
        8: [0.84, 0.91, 0.99, 1.08, 1.18, 1.29, 1.39, 1.50, 1.58, 1.59],
        10: [0.95, 1.04, 1.14, 1.25, 1.38, 1.52, 1.66, 1.81, 1.94, 1.97],
        12: [1.05, 1.15, 1.28, 1.41, 1.57, 1.74, 1.92, 2.11, 2.29, 2.36],
        14: [1.14, 1.27, 1.41, 1.57, 1.75, 1.95, 2.17, 2.40, 2.63, 2.75],
        16: [1.25, 1.37, 1.53, 1.71, 1.92, 2.15, 2.41, 2.69, 2.96, 3.14],
        18: [1.32, 1.47, 1.65, 1.85, 2.09, 2.35, 2.55, 2.97, 3.24, 3.53],
        20: [1.41, 1.57, 1.77, 1.99, 2.25, 2.55, 2.88, 3.24, 3.60, 3.92],
        22: [1.49, 1.67, 1.88, 2.13, 2.41, 2.74, 3.11, 3.51, 3.94, 4.33],
        24: [1.57, 1.77, 2.00, 2.26, 2.57, 2.93, 3.33, 3.78, 4.27, 4.70],
        26: [1.64, 1.86, 2.11, 2.39, 2.73, 3.11, 3.55, 4.04, 4.60, 5.11],
        28: [1.72, 1.95, 2.21, 2.52, 2.88, 3.30, 3.77, 4.30, 4.94, 5.51],
        30: [1.80, 2.04, 2.32, 2.65, 3.03, 3.48, 3.99, 4.56, 5.27, 5.89],
        32: [1.87, 2.13, 2.43, 2.77, 3.18, 3.66, 4.20, 4.82, 5.60, 6.24],
        34: [1.94, 2.21, 2.53, 2.90, 3.33, 3.84, 4.42, 5.08, 5.92, 6.65],
        36: [2.02, 2.30, 2.63, 3.02, 3.48, 4.02, 4.63, 5.33, 6.23, 7.02],
        38: [2.09, 2.38, 2.73, 3.14, 3.62, 4.20, 4.84, 5.58, 6.60, 7.43],
        40: [2.16, 2.47, 2.83, 3.26, 3.77, 4.38, 5.05, 5.83, 6.91, 7.84],
        45: [2.33, 2.67, 3.08, 3.53, 4.12, 4.78, 5.55, 6.45, 7.72, 8.87],
        50: [2.50, 2.88, 3.32, 3.80, 4.47, 5.18, 6.05, 7.07, 8.52, 9.90],
        55: [2.66, 3.07, 3.56, 4.07, 4.82, 5.58, 6.55, 7.69, 9.40, 10.80],
        60: [2.83, 3.27, 3.79, 4.34, 5.16, 5.98, 7.05, 8.31, 10.20, 11.80],
        65: [2.99, 3.46, 4.02, 4.61, 5.50, 6.38, 7.55, 8.93, 11.00, 12.70],
        70: [3.14, 3.65, 4.25, 4.88, 5.83, 6.78, 8.05, 9.55, 11.70, 13.70],
        75: [3.30, 3.84, 4.48, 5.15, 6.16, 7.18, 8.55, 10.17, 12.50, 14.70],
        80: [3.45, 4.02, 4.70, 5.42, 6.49, 7.58, 9.06, 10.79, 13.40, 15.70],
        85: [3.60, 4.20, 4.92, 5.69, 6.82, 7.98, 9.57, 11.41, 14.20, 16.80],
        90: [3.75, 4.38, 5.14, 5.96, 7.15, 8.38, 10.08, 12.04, 14.90, 17.70],
        95: [3.90, 4.56, 5.36, 6.23, 7.48, 8.78, 10.59, 12.67, 15.60, 18.60],
        100: [4.05, 4.74, 5.58, 6.50, 7.81, 9.18, 11.10, 13.30, 16.50, 19.60],
        105: [4.20, 4.92, 5.80, 6.77, 8.14, 9.58, 11.61, 13.93, 17.20, 20.60],
        110: [4.35, 5.10, 6.02, 7.04, 8.47, 9.99, 12.12, 14.56, 18.00, 21.60],
        115: [4.50, 5.28, 6.24, 7.31, 8.80, 10.40, 12.63, 15.19, 18.80, 22.60],
        120: [4.65, 5.46, 6.46, 7.58, 9.13, 10.81, 13.14, 15.87, 19.50, 23.60],
        125: [4.80, 5.64, 6.68, 7.85, 9.46, 11.22, 13.65, 16.45, 20.20, 24.60],
        130: [4.95, 5.82, 6.90, 8.12, 9.79, 11.63, 14.16, 17.08, 21.00, 25.50],
        135: [5.10, 6.00, 7.12, 8.39, 10.12, 12.04, 14.67, 17.71, 21.90, 26.50],
        140: [5.25, 6.18, 7.34, 8.66, 10.45, 12.45, 15.18, 18.34, 22.70, 27.50],
        145: [5.39, 6.36, 7.56, 8.93, 10.77, 12.86, 15.69, 18.97, 23.40, 28.40],
        150: [5.53, 6.54, 7.78, 9.20, 11.09, 13.27, 16.20, 19.60, 24.20, 29.40],
        155: [5.67, 6.72, 8.00, 9.47, 11.41, 13.68, 16.71, 20.23, 25.00, 30.40],
        160: [5.81, 6.90, 8.22, 9.74, 11.73, 14.09, 17.22, 20.86, 25.60, 31.30],
        165: [5.95, 7.07, 8.44, 10.01, 12.05, 14.50, 17.73, 21.49, 26.40, 32.50],
        170: [6.09, 7.23, 8.66, 10.28, 12.37, 14.91, 18.24, 22.12, 27.10, 33.60],
        175: [6.23, 7.39, 8.88, 10.55, 12.69, 15.32, 18.75, 22.75, 27.90, 34.70],
        180: [6.37, 7.55, 9.10, 10.82, 13.01, 15.73, 19.26, 23.38, 28.50, 35.40],
        185: [6.50, 7.71, 9.32, 11.09, 13.33, 16.14, 19.77, 24.01, 29.40, 36.60],
        190: [6.63, 7.87, 9.54, 11.36, 13.65, 16.55, 20.28, 24.64, 30.10, 37.60],
        195: [6.76, 8.03, 9.75, 11.63, 13.97, 16.96, 20.79, 25.27, 30.90, 38.30],
        200: [6.89, 8.19, 9.96, 11.90, 14.30, 17.40, 21.30, 25.90, 31.80, 39.50],
    }

    # Таблица B.2 (ядро диапазона до NP=9.7 + контрольные высокие точки).
    _B2_POINTS = [
        (0.0, 0.2), (0.015, 0.202), (0.02, 0.215), (0.03, 0.237), (0.04, 0.256),
        (0.05, 0.273), (0.06, 0.289), (0.07, 0.304), (0.08, 0.318), (0.09, 0.331),
        (0.10, 0.343), (0.11, 0.355), (0.12, 0.367), (0.13, 0.378), (0.14, 0.389),
        (0.15, 0.399), (0.16, 0.410), (0.17, 0.420), (0.18, 0.430), (0.19, 0.439),
        (0.20, 0.449), (0.21, 0.458), (0.22, 0.467), (0.23, 0.476), (0.24, 0.485),
        (0.25, 0.493), (0.26, 0.502), (0.27, 0.510), (0.28, 0.518), (0.29, 0.526),
        (0.30, 0.534), (0.35, 0.573), (0.38, 0.595), (0.39, 0.602), (0.40, 0.610),
        (0.41, 0.617), (0.42, 0.624), (0.43, 0.631), (0.44, 0.638), (0.45, 0.645),
        (0.46, 0.652), (0.47, 0.658), (0.48, 0.665), (0.49, 0.672), (0.50, 0.678),
        (0.60, 0.742), (0.70, 0.803), (0.80, 0.860), (0.90, 0.916), (1.00, 0.969),
        (1.10, 1.021), (1.20, 1.071), (1.30, 1.120), (1.40, 1.168), (1.50, 1.215),
        (1.55, 1.238), (1.60, 1.261), (1.70, 1.306), (1.80, 1.350), (1.90, 1.394),
        (2.00, 1.437), (2.10, 1.479), (2.20, 1.521), (2.30, 1.563), (2.40, 1.604),
        (2.50, 1.644), (2.60, 1.684), (2.70, 1.724), (2.80, 1.763), (2.90, 1.802),
        (3.00, 1.840), (3.10, 1.879), (3.20, 1.917), (3.30, 1.954), (3.40, 1.991),
        (3.50, 2.029), (3.60, 2.065), (3.70, 2.102), (3.80, 2.138), (3.90, 2.174),
        (4.00, 2.210), (4.10, 2.246), (4.20, 2.281), (4.30, 2.317), (4.40, 2.352),
        (4.50, 2.386), (4.60, 2.421), (4.70, 2.456), (4.80, 2.490), (4.90, 2.524),
        (5.00, 2.558), (5.50, 2.726), (6.00, 2.891), (6.50, 3.053), (7.00, 3.212),
        (7.50, 3.369), (8.00, 3.524), (8.50, 3.677), (8.60, 3.707), (8.70, 3.738),
        (8.80, 3.768), (8.90, 3.798), (9.00, 3.828), (9.10, 3.858), (9.20, 3.888),
        (9.30, 3.918), (9.40, 3.948), (9.50, 3.978), (9.60, 4.008), (9.70, 4.037),
        (10.0, 4.127), (15.0, 5.547), (20.0, 6.893), (27.0, 8.701), (40.0, 11.92),
        (50.0, 14.32), (80.0, 21.33), (100.0, 25.91), (150.0, 37.21), (200.0, 48.44),
        (300.0, 70.29), (500.0, 113.32), (1000.0, 218.87), (1250.0, 271.14),
        (1600.0, 343.90), (2000.0, 426.80),
    ]

    def _interp_1d(points: List[tuple[float, float]], x: float) -> float:
        if not points:
            return 0.0
        x = float(x)
        if x <= points[0][0]:
            return float(points[0][1])
        if x >= points[-1][0]:
            return float(points[-1][1])
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            if x1 <= x <= x2:
                if x2 == x1:
                    return float(y1)
                t = (x - x1) / (x2 - x1)
                return float(y1 + (y2 - y1) * t)
        return float(points[-1][1])

    def _alpha_from_b2(np_val: float) -> float:
        return max(_interp_1d(_B2_POINTS, max(float(np_val), 0.0)), 0.0)

    def _alpha_from_b1(n_val: float, p_val: float) -> float:
        n = max(float(n_val), 0.0)
        p = max(float(p_val), 0.0)
        n_keys = sorted(_B1_TABLE.keys())
        p_keys = _B1_P_GRID
        # Ограничения таблицы B.1
        n = min(max(n, n_keys[0]), n_keys[-1])
        p = min(max(p, p_keys[0]), p_keys[-1])

        # Индексы по P
        p_hi_idx = 0
        while p_hi_idx < len(p_keys) and p_keys[p_hi_idx] < p:
            p_hi_idx += 1
        if p_hi_idx == 0:
            p_lo_idx = p_hi_idx = 0
        elif p_hi_idx >= len(p_keys):
            p_lo_idx = p_hi_idx = len(p_keys) - 1
        else:
            p_lo_idx = p_hi_idx - 1

        # Индексы по N
        n_hi_idx = 0
        while n_hi_idx < len(n_keys) and n_keys[n_hi_idx] < n:
            n_hi_idx += 1
        if n_hi_idx == 0:
            n_lo_idx = n_hi_idx = 0
        elif n_hi_idx >= len(n_keys):
            n_lo_idx = n_hi_idx = len(n_keys) - 1
        else:
            n_lo_idx = n_hi_idx - 1

        n1 = n_keys[n_lo_idx]
        n2 = n_keys[n_hi_idx]
        p1 = p_keys[p_lo_idx]
        p2 = p_keys[p_hi_idx]

        q11 = _B1_TABLE[n1][p_lo_idx]
        q12 = _B1_TABLE[n1][p_hi_idx]
        q21 = _B1_TABLE[n2][p_lo_idx]
        q22 = _B1_TABLE[n2][p_hi_idx]

        # Билинейная интерполяция.
        if n2 == n1 and p2 == p1:
            return float(q11)
        if n2 == n1:
            tp = 0.0 if p2 == p1 else (p - p1) / (p2 - p1)
            return float(q11 + (q12 - q11) * tp)
        if p2 == p1:
            tn = (n - n1) / (n2 - n1)
            return float(q11 + (q21 - q11) * tn)

        tn = (n - n1) / (n2 - n1)
        tp = (p - p1) / (p2 - p1)
        qn1 = q11 + (q21 - q11) * tn
        qn2 = q12 + (q22 - q12) * tn
        return float(qn1 + (qn2 - qn1) * tp)

    def _alpha_sp(n_val: float, p_val: float, np_val: float) -> float:
        # Выбор таблицы в точном соответствии с Приложением Б.
        if p_val > 0.1 and n_val <= 200:
            return _alpha_from_b1(n_val, p_val)
        return _alpha_from_b2(np_val)

    day_k = max(float(day_factor), 1.0)
    reserve_k = max(float(reserve_factor), 1.0)
    leakage_k = 1.0 + max(float(leakage_percent), 0.0) / 100.0
    adjust_k = day_k * reserve_k * leakage_k

    rows: List[Dict[str, float | str]] = []
    # Авто-подпитка котельной: доля от базового расхода объекта (если строка есть в таблице).
    boiler_makeup_share = 0.064
    non_special_base_m3_day = 0.0
    for item in consumers:
        n = max(float(item.count), 0.0)
        if n <= 0:
            continue
        name_l = (item.name or "").strip().lower()
        if "полив" in name_l or "заливка поверхности катка" in name_l or "подпитка котельной" in name_l:
            continue
        q_u_tot = float(item.q_u_total_l_day) if float(item.q_u_total_l_day) > 0 else float(item.cold_l_per_unit_day + item.hot_l_per_unit_day)
        non_special_base_m3_day += n * max(q_u_tot, 0.0) / 1000.0
    cold_m3_day_base = 0.0
    hot_m3_day_base = 0.0
    cold_max_m3_hour_base = 0.0
    hot_max_m3_hour_base = 0.0
    cold_max_l_s_base = 0.0
    hot_max_l_s_base = 0.0
    total_max_l_s_base = 0.0
    cold_max_m3_hour_formula_base = 0.0
    hot_max_m3_hour_formula_base = 0.0
    total_max_m3_hour_formula_base = 0.0
    cold_avg_m3_hour_base = 0.0
    hot_avg_m3_hour_base = 0.0

    for item in consumers:
        n = max(float(item.count), 0.0)
        t_h = max(float(item.t_hours), 0.0)
        name_l = (item.name or "").strip().lower()

        if "подпитка котельной" in name_l:
            q_u_tot_raw = float(item.q_u_total_l_day) if float(item.q_u_total_l_day) > 0 else float(item.cold_l_per_unit_day + item.hot_l_per_unit_day)
            if q_u_tot_raw > 0:
                n = (non_special_base_m3_day * boiler_makeup_share * 1000.0) / q_u_tot_raw

        q_u_tot = float(item.q_u_total_l_day) if float(item.q_u_total_l_day) > 0 else float(item.cold_l_per_unit_day + item.hot_l_per_unit_day)
        q_u_hot = float(item.q_u_hot_l_day) if float(item.q_u_hot_l_day) > 0 else float(item.hot_l_per_unit_day)
        q_u_cold = max(q_u_tot - q_u_hot, 0.0)

        has_qhr_or_q0 = any(
            float(v) > 0.0
            for v in (
                item.q_hr_total_l_h,
                item.q_hr_hot_l_h,
                item.q0_total_l_s,
                item.q0_total_l_h,
                item.q0_spec_l_s,
                item.q0_spec_l_h,
            )
        )

        # Для строк А.2 с прочерками по q_hr/q0 (например, полив) не формируем искусственные пики.
        if not has_qhr_or_q0:
            q_hr_tot = 0.0
            q_hr_hot = 0.0
            q_hr_cold = 0.0
            q0_tot = 0.0
            q0hr_tot = 0.0
            q0_sec = 0.0
            q0hr_sec = 0.0
        else:
            # Приоритет расчетных параметров по СП:
            # 1) q_hr,u из таблицы;
            # 2) q0,hr (если задан);
            # 3) оценка из q_u,m и времени работы T;
            # 4) fallback через коэффициент максимального часа.
            if float(item.q_hr_total_l_h) > 0:
                q_hr_tot = float(item.q_hr_total_l_h)
            elif float(item.q0_total_l_h) > 0:
                q_hr_tot = float(item.q0_total_l_h)
            elif t_h > 0:
                q_hr_tot = q_u_tot / t_h
            else:
                q_hr_tot = q_u_tot / 24.0 * max(float(peak_hour_factor), 1.0)

            if float(item.q_hr_hot_l_h) > 0:
                q_hr_hot = float(item.q_hr_hot_l_h)
            elif float(item.q0_spec_l_h) > 0:
                q_hr_hot = float(item.q0_spec_l_h)
            elif t_h > 0:
                q_hr_hot = q_u_hot / t_h
            else:
                q_hr_hot = q_u_hot / 24.0 * max(float(peak_hour_factor), 1.0)
            q_hr_cold = max(q_hr_tot - q_hr_hot, 0.0)
            q0_tot = float(item.q0_total_l_s) if float(item.q0_total_l_s) > 0 else q_hr_tot / 3600.0
            q0hr_tot = float(item.q0_total_l_h) if float(item.q0_total_l_h) > 0 else q_hr_tot

            # В СП для разделов ХВС/ГВС используется "расход воды прибором, л/с (л/ч)" для
            # соответствующей секции. В каталоге храним его в q0_spec_*.
            # Если не задано, fallback на общий q0.
            q0_sec = float(item.q0_spec_l_s) if float(item.q0_spec_l_s) > 0 else q0_tot
            q0hr_sec = float(item.q0_spec_l_h) if float(item.q0_spec_l_h) > 0 else q0hr_tot

        cold_m3_day_i = n * q_u_cold / 1000.0
        hot_m3_day_i = n * q_u_hot / 1000.0
        total_m3_day_i = cold_m3_day_i + hot_m3_day_i
        if t_h > 0:
            cold_avg_m3_hour_base += cold_m3_day_i / t_h
            hot_avg_m3_hour_base += hot_m3_day_i / t_h
        else:
            cold_avg_m3_hour_base += cold_m3_day_i / 24.0
            hot_avg_m3_hour_base += hot_m3_day_i / 24.0

        # Расчет NP/NPhr и alpha/alpha_hr (логика табличной методики СП).
        np_cold = (n * q_hr_cold) / (q0_sec * 3600.0) if q0_sec > 0 else 0.0
        np_hot = (n * q_hr_hot) / (q0_sec * 3600.0) if q0_sec > 0 else 0.0
        np_tot = (n * q_hr_tot) / (q0_tot * 3600.0) if q0_tot > 0 else 0.0

        np_hr_cold = (n * q_hr_cold) / q0hr_sec if q0hr_sec > 0 else 0.0
        np_hr_hot = (n * q_hr_hot) / q0hr_sec if q0hr_sec > 0 else 0.0
        np_hr_tot = (n * q_hr_tot) / q0hr_tot if q0hr_tot > 0 else 0.0

        p_cold = q_hr_cold / (q0_sec * 3600.0) if q0_sec > 0 else 0.0
        p_hot = q_hr_hot / (q0_sec * 3600.0) if q0_sec > 0 else 0.0
        p_tot = q_hr_tot / (q0_tot * 3600.0) if q0_tot > 0 else 0.0
        p_hr_cold = q_hr_cold / q0hr_sec if q0hr_sec > 0 else 0.0
        p_hr_hot = q_hr_hot / q0hr_sec if q0hr_sec > 0 else 0.0
        p_hr_tot = q_hr_tot / q0hr_tot if q0hr_tot > 0 else 0.0

        alpha_cold = _alpha_sp(n, p_cold, np_cold)
        alpha_hot = _alpha_sp(n, p_hot, np_hot)
        alpha_tot = _alpha_sp(n, p_tot, np_tot)

        alpha_hr_cold = _alpha_sp(n, p_hr_cold, np_hr_cold)
        alpha_hr_hot = _alpha_sp(n, p_hr_hot, np_hr_hot)
        alpha_hr_tot = _alpha_sp(n, p_hr_tot, np_hr_tot)

        cold_max_l_s_i = 5.0 * q0_sec * alpha_cold
        hot_max_l_s_i = 5.0 * q0_sec * alpha_hot
        total_max_l_s_i = 5.0 * q0_tot * alpha_tot

        cold_max_m3_hour_i = 0.005 * q0hr_sec * alpha_hr_cold
        hot_max_m3_hour_i = 0.005 * q0hr_sec * alpha_hr_hot
        total_max_m3_hour_i = 0.005 * q0hr_tot * alpha_hr_tot

        cold_m3_day_base += cold_m3_day_i
        hot_m3_day_base += hot_m3_day_i
        cold_max_m3_hour_base += n * q_hr_cold / 1000.0
        hot_max_m3_hour_base += n * q_hr_hot / 1000.0
        cold_max_m3_hour_formula_base += cold_max_m3_hour_i
        hot_max_m3_hour_formula_base += hot_max_m3_hour_i
        total_max_m3_hour_formula_base += total_max_m3_hour_i
        cold_max_l_s_base += cold_max_l_s_i
        hot_max_l_s_base += hot_max_l_s_i
        total_max_l_s_base += total_max_l_s_i

        rows.append(
            {
                "name": item.name,
                "unit": item.unit,
                "count": n,
                "use_prod_water_source": bool(item.use_prod_water_source),
                "object_kind": (item.object_kind or "nonproduction").strip().lower(),
                "q_u_total_l_day": q_u_tot,
                "q_u_hot_l_day": q_u_hot,
                "q_hr_total_l_h": q_hr_tot,
                "q_hr_hot_l_h": q_hr_hot,
                "q0_total_l_s": q0_tot,
                "q0_total_l_h": float(item.q0_total_l_h),
                "q0_spec_l_s": q0_sec,
                "q0_spec_l_h": q0hr_sec,
                "np_cold": np_cold,
                "np_hot": np_hot,
                "np_total": np_tot,
                "p_cold": p_cold,
                "p_hot": p_hot,
                "p_total": p_tot,
                "np_hr_cold": np_hr_cold,
                "np_hr_hot": np_hr_hot,
                "np_hr_total": np_hr_tot,
                "p_hr_cold": p_hr_cold,
                "p_hr_hot": p_hr_hot,
                "p_hr_total": p_hr_tot,
                "alpha_cold": alpha_cold,
                "alpha_hot": alpha_hot,
                "alpha_total": alpha_tot,
                "alpha_hr_cold": alpha_hr_cold,
                "alpha_hr_hot": alpha_hr_hot,
                "alpha_hr_total": alpha_hr_tot,
                "t_hours": t_h,
                "cold_l_per_unit_day": q_u_cold,
                "hot_l_per_unit_day": q_u_hot,
                "cold_m3_day": cold_m3_day_i,
                "hot_m3_day": hot_m3_day_i,
                "total_m3_day": total_m3_day_i,
                "cold_max_m3_hour": cold_max_m3_hour_i,
                "hot_max_m3_hour": hot_max_m3_hour_i,
                "total_max_m3_hour": total_max_m3_hour_i,
                "cold_max_l_sec": cold_max_l_s_i,
                "hot_max_l_sec": hot_max_l_s_i,
                "total_max_l_sec": total_max_l_s_i,
                "source_doc": item.source_doc.strip(),
                "source_item": item.source_item.strip(),
                "sewer_target": _infer_prod_sewer_target(
                    name=item.name,
                    override=item.sewer_target_override,
                ),
                "water_quality_override": (item.water_quality_override or "").strip(),
                "np_source_override": (item.np_source_override or "").strip(),
                "np_sewer_override": (item.np_sewer_override or "").strip(),
            }
        )

    total_m3_day_base = cold_m3_day_base + hot_m3_day_base
    cold_m3_day_adj = cold_m3_day_base * adjust_k
    hot_m3_day_adj = hot_m3_day_base * adjust_k
    total_m3_day_adj = total_m3_day_base * adjust_k

    max_day_k = max(float(max_day_factor), 1.0)
    # Для максимальных секундных/часовых расходов используем расчет по формульной части СП:
    # q = 5*q0*alpha, q_hr = 0.005*q0hr*alpha_hr.
    cold_max_m3_hour = cold_max_m3_hour_formula_base * adjust_k
    hot_max_m3_hour = hot_max_m3_hour_formula_base * adjust_k
    max_m3_hour = total_max_m3_hour_formula_base * adjust_k
    cold_max_l_s = cold_max_l_s_base * adjust_k
    hot_max_l_s = hot_max_l_s_base * adjust_k
    max_l_s = total_max_l_s_base * adjust_k
    if max_l_s <= 0:
        max_l_s = max_m3_hour * 1000.0 / 3600.0
    if cold_max_l_s <= 0:
        cold_max_l_s = cold_max_m3_hour * 1000.0 / 3600.0
    if hot_max_l_s <= 0:
        hot_max_l_s = hot_max_m3_hour * 1000.0 / 3600.0
    cold_avg_m3_hour = cold_avg_m3_hour_base * adjust_k
    hot_avg_m3_hour = hot_avg_m3_hour_base * adjust_k
    avg_m3_hour = cold_avg_m3_hour + hot_avg_m3_hour
    cold_max_m3_day = cold_m3_day_adj * max_day_k
    hot_max_m3_day = hot_m3_day_adj * max_day_k
    total_max_m3_day = total_m3_day_adj * max_day_k

    wastewater_k = max(float(wastewater_factor), 0.0)
    sewer_avg_m3_day = total_m3_day_adj * wastewater_k
    sewer_max_m3_day = total_max_m3_day * wastewater_k
    sewer_max_m3_hour = max_m3_hour * wastewater_k
    sewer_max_l_s = max_l_s * wastewater_k

    balance_rows = [
        {
            "name": "ХВС",
            "q_sec_l_s": cold_max_l_s,
            "q_avg_day_m3_day": cold_m3_day_adj,
            "q_max_day_m3_day": cold_max_m3_day,
            "q_max_hour_m3_hour": cold_max_m3_hour,
        },
        {
            "name": "ГВС",
            "q_sec_l_s": hot_max_l_s,
            "q_avg_day_m3_day": hot_m3_day_adj,
            "q_max_day_m3_day": hot_max_m3_day,
            "q_max_hour_m3_hour": hot_max_m3_hour,
        },
        {
            "name": "Итого водоснабжение",
            "q_sec_l_s": max_l_s,
            "q_avg_day_m3_day": total_m3_day_adj,
            "q_max_day_m3_day": total_max_m3_day,
            "q_max_hour_m3_hour": max_m3_hour,
        },
        {
            "name": "Итого водоотведение",
            "q_sec_l_s": sewer_max_l_s,
            "q_avg_day_m3_day": sewer_avg_m3_day,
            "q_max_day_m3_day": sewer_max_m3_day,
            "q_max_hour_m3_hour": sewer_max_m3_hour,
        },
    ]

    return {
        "cold_m3_day_base": cold_m3_day_base,
        "hot_m3_day_base": hot_m3_day_base,
        "total_m3_day_base": total_m3_day_base,
        "cold_m3_day": cold_m3_day_adj,
        "hot_m3_day": hot_m3_day_adj,
        "total_m3_day": total_m3_day_adj,
        "avg_m3_hour": avg_m3_hour,
        "max_m3_hour": max_m3_hour,
        "max_l_sec": max_l_s,
        "cold_avg_m3_hour": cold_avg_m3_hour,
        "hot_avg_m3_hour": hot_avg_m3_hour,
        "cold_max_m3_hour": cold_max_m3_hour,
        "hot_max_m3_hour": hot_max_m3_hour,
        "cold_max_l_sec": cold_max_l_s,
        "hot_max_l_sec": hot_max_l_s,
        "cold_max_m3_day": cold_max_m3_day,
        "hot_max_m3_day": hot_max_m3_day,
        "total_max_m3_day": total_max_m3_day,
        "max_day_factor": max_day_k,
        "wastewater_factor": wastewater_k,
        "sewer_avg_m3_day": sewer_avg_m3_day,
        "sewer_max_m3_day": sewer_max_m3_day,
        "sewer_max_m3_hour": sewer_max_m3_hour,
        "sewer_max_l_sec": sewer_max_l_s,
        "balance_rows": balance_rows,
        "day_factor": day_k,
        "reserve_factor": reserve_k,
        "leakage_percent": max(float(leakage_percent), 0.0),
        "adjustment_factor": adjust_k,
        "rows": rows,
    }


def _kcir_from_ratio(qh_to_qcir: float) -> float:
    """
    Приложение Г СП 30.13330.2020 (табличная аппроксимация).
    qh_to_qcir = qh / qcir
    """
    points = [
        (1.2, 0.57),
        (1.3, 0.48),
        (1.4, 0.43),
        (1.5, 0.40),
        (1.6, 0.38),
        (1.7, 0.36),
        (1.8, 0.33),
        (1.9, 0.25),
        (2.0, 0.12),
        (2.1, 0.00),
    ]
    x = float(qh_to_qcir)
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            return y1 + (y2 - y1) * t
    return 0.0


def calc_gvs_passport(
    qh_avg_m3_h: float,
    qh_max_m3_h: float,
    t_hot_c: float,
    t_cold_c: float,
    qht_kW: float,
    delta_t_supply_c: float,
) -> Dict[str, float]:
    """
    СП 30.13330.2020:
    - Формула (12): QTh = 1.16 * qT_h * (th - tc) + Qht
    - Формула (13): Qhr_h = 1.16 * qhr_h * (th - tc) + Qht
    - Формула (16): qcir = ΣQht / (Δt * C * 3600), где ΣQht в ккал/ч
    - Формула (17): qh,cir = qh * (1 + kcir)
    """
    qh_avg = max(float(qh_avg_m3_h), 0.0)
    qh_max = max(float(qh_max_m3_h), 0.0)
    dt_hw = max(float(t_hot_c) - float(t_cold_c), 0.0)
    qht_kw = max(float(qht_kW), 0.0)
    dt_supply = max(float(delta_t_supply_c), 0.1)

    qth_kw = 1.16 * qh_avg * dt_hw + qht_kw
    qhrh_kw = 1.16 * qh_max * dt_hw + qht_kw

    # Перевод Qht (кВт) -> ккал/ч
    qht_kcal_h = qht_kw * 860.0
    # C ~= 1 ккал/(кг*°C), rho ~= 1 кг/л
    qcir_l_s = qht_kcal_h / (dt_supply * 3600.0)

    qh_l_s = qh_max * 1000.0 / 3600.0
    ratio = qh_l_s / qcir_l_s if qcir_l_s > 0 else 2.1
    kcir = _kcir_from_ratio(ratio)
    qh_cir_l_s = qh_l_s * (1.0 + kcir)

    return {
        "qh_avg_m3_h": qh_avg,
        "qh_max_m3_h": qh_max,
        "t_hot_c": max(float(t_hot_c), 0.0),
        "t_cold_c": max(float(t_cold_c), 0.0),
        "delta_t_hw_c": dt_hw,
        "qht_kW": qht_kw,
        "qth_kW": qth_kw,
        "qhrh_kW": qhrh_kw,
        "delta_t_supply_c": dt_supply,
        "qcir_l_s": qcir_l_s,
        "qh_l_s": qh_l_s,
        "qh_to_qcir": ratio,
        "kcir": kcir,
        "qh_cir_l_s": qh_cir_l_s,
        "qcir_m3_h": qcir_l_s * 3.6,
        "qh_cir_m3_h": qh_cir_l_s * 3.6,
    }


def calc_heat(elements: List[HeatElement]) -> Dict[str, float]:
    """
    Теплопотери: Q = Σ(U * A * ΔT)
    Это базовая физика. Нормативные корректировки (коэффициенты, инфильтрация и т.д.)
    подключим по СП 50.13330.2024 / СП 60.13330.2020 после твоей документации.
    """
    total_w = 0.0
    for el in elements:
        a = max(float(el.area_m2), 0.0)
        u = max(float(el.u_w_m2k), 0.0)
        dt = max(float(el.delta_t_k), 0.0)
        total_w += u * a * dt

    total_kw = total_w / 1000.0
    return {"heat_loss_w": total_w, "heat_loss_kw": total_kw}


def calc_heat_advanced(
    elements: List[HeatElement],
    indoor_temp_c: float,
    outdoor_temp_c: float,
    ventilation_flow_m3_h: float,
    reserve_factor: float,
    internal_gains_w: float,
    heating_hours: float,
    average_load_factor: float,
) -> Dict[str, float]:
    """
    Расширенный расчет:
    Qtr = Σ(U * A * ΔT)
    Qvent = 0.335 * L * ΔT
    Qdesign = (Qtr + Qvent - Qinternal) * Kreserve
    """
    dt = max(float(indoor_temp_c) - float(outdoor_temp_c), 0.0)

    transmission_w = 0.0
    for el in elements:
        a = max(float(el.area_m2), 0.0)
        u = max(float(el.u_w_m2k), 0.0)
        transmission_w += u * a * dt

    vent_flow = max(float(ventilation_flow_m3_h), 0.0)
    ventilation_w = 0.335 * vent_flow * dt

    internal = max(float(internal_gains_w), 0.0)
    raw_w = max(transmission_w + ventilation_w - internal, 0.0)
    reserve_k = max(float(reserve_factor), 1.0)
    design_w = raw_w * reserve_k

    period_h = max(float(heating_hours), 0.0)
    load_factor = min(max(float(average_load_factor), 0.0), 1.0)
    annual_kwh = design_w * period_h * load_factor / 1000.0

    return {
        "delta_t_k": dt,
        "transmission_w": transmission_w,
        "ventilation_w": ventilation_w,
        "internal_gains_w": internal,
        "raw_heat_loss_w": raw_w,
        "reserve_factor": reserve_k,
        "heat_loss_w": design_w,
        "heat_loss_kw": design_w / 1000.0,
        "annual_energy_kwh": annual_kwh,
    }


def build_data_checks(
    water_rows: List[Dict[str, float | str]],
    heat_elements: List[HeatElement],
    require_heat_elements: bool = True,
) -> List[str]:
    checks: List[str] = []

    if not water_rows:
        checks.append("Не заполнены группы потребителей воды.")

    missing_sources = 0
    zero_norms = 0
    inconsistent_q = 0
    invalid_t = 0
    for row in water_rows:
        cold = float(row.get("cold_l_per_unit_day", 0.0) or 0.0)
        hot = float(row.get("hot_l_per_unit_day", 0.0) or 0.0)
        if cold == 0.0 and hot == 0.0:
            zero_norms += 1
        if not str(row.get("source_doc", "")).strip():
            missing_sources += 1
        q_u_tot = float(row.get("q_u_total_l_day", 0.0) or 0.0)
        q_u_hot = float(row.get("q_u_hot_l_day", 0.0) or 0.0)
        q_hr_tot = float(row.get("q_hr_total_l_h", 0.0) or 0.0)
        q_hr_hot = float(row.get("q_hr_hot_l_h", 0.0) or 0.0)
        if (q_u_tot > 0 and q_u_hot > q_u_tot + 1e-9) or (q_hr_tot > 0 and q_hr_hot > q_hr_tot + 1e-9):
            inconsistent_q += 1
        # T обязательно только если строка не имеет явного q_hr/q0hr.
        if (
            float(row.get("count", 0.0) or 0.0) > 0
            and float(row.get("t_hours", 24.0) or 0.0) <= 0
            and float(row.get("q_hr_total_l_h", 0.0) or 0.0) <= 0
            and float(row.get("q0_total_l_h", 0.0) or 0.0) <= 0
        ):
            invalid_t += 1

    if zero_norms > 0:
        checks.append(f"Есть строки воды без норм (ХВС и ГВС = 0): {zero_norms}.")
    if missing_sources > 0:
        checks.append(f"Есть строки воды без ссылки на нормативный документ: {missing_sources}.")
    if inconsistent_q > 0:
        checks.append(f"Есть строки с противоречием норм (q горячей > q общей): {inconsistent_q}.")
    if invalid_t > 0:
        checks.append(f"Есть строки с нулевым временем работы T при ненулевом количестве: {invalid_t}.")

    if require_heat_elements and not heat_elements:
        checks.append("Не заполнены ограждающие конструкции для теплопотерь.")
    elif require_heat_elements:
        invalid_heat = 0
        for el in heat_elements:
            if float(el.area_m2) <= 0.0 or float(el.u_w_m2k) <= 0.0:
                invalid_heat += 1
        if invalid_heat > 0:
            checks.append(f"Есть строки теплопотерь с нулевой площадью/U: {invalid_heat}.")

    return checks


def calc_legacy_water_table(rows: List[LegacyWaterRow]) -> Dict[str, Dict[str, float] | List[Dict[str, float | str]]]:
    """
    Аналог структуры старого Water.exe / формы из DOC:
    - qT (м3/сут) = q_u_day * U / 1000
    - qhr (л/ч) = q_u_hr * U
    - q_calc (л/с) = 5 * q0 * alpha
    - q_calc_hr (м3/ч) = 0.005 * q0hr * alpha_hr
    - q_avg_hr (м3/ч) = qT / 24
    """
    result_rows: List[Dict[str, float | str]] = []
    totals: Dict[str, Dict[str, float]] = {
        "cold": {"qT_m3_day": 0.0, "qhr_l_h": 0.0, "q_calc_l_s": 0.0, "q_calc_hr_m3_h": 0.0, "q_avg_hr_m3_h": 0.0},
        "hot": {"qT_m3_day": 0.0, "qhr_l_h": 0.0, "q_calc_l_s": 0.0, "q_calc_hr_m3_h": 0.0, "q_avg_hr_m3_h": 0.0},
        "total": {"qT_m3_day": 0.0, "qhr_l_h": 0.0, "q_calc_l_s": 0.0, "q_calc_hr_m3_h": 0.0, "q_avg_hr_m3_h": 0.0},
    }

    for row in rows:
        section = row.section if row.section in ("cold", "hot", "total") else "total"
        u = max(float(row.users_u), 0.0)
        q_u_day = max(float(row.q_u_day), 0.0)
        q_u_hr = max(float(row.q_u_hr), 0.0)
        q0 = max(float(row.q0), 0.0)
        q0hr = max(float(row.q0hr), 0.0)
        alpha = max(float(row.alpha), 0.0)
        alpha_hr = max(float(row.alpha_hr), 0.0)

        qT_m3_day = q_u_day * u / 1000.0
        qhr_l_h = q_u_hr * u
        q_calc_l_s = 5.0 * q0 * alpha
        q_calc_hr_m3_h = 0.005 * q0hr * alpha_hr
        q_avg_hr_m3_h = qT_m3_day / 24.0

        result_rows.append(
            {
                "section": section,
                "consumer_name": row.consumer_name,
                "fixtures_np": max(float(row.fixtures_np), 0.0),
                "users_u": u,
                "q_u_day": q_u_day,
                "q_u_hr": q_u_hr,
                "q0": q0,
                "q0hr": q0hr,
                "alpha": alpha,
                "alpha_hr": alpha_hr,
                "qT_m3_day": qT_m3_day,
                "qhr_l_h": qhr_l_h,
                "q_calc_l_s": q_calc_l_s,
                "q_calc_hr_m3_h": q_calc_hr_m3_h,
                "q_avg_hr_m3_h": q_avg_hr_m3_h,
                "source_doc": row.source_doc.strip(),
                "source_item": row.source_item.strip(),
            }
        )

        for key in ("qT_m3_day", "qhr_l_h", "q_calc_l_s", "q_calc_hr_m3_h", "q_avg_hr_m3_h"):
            totals[section][key] += float(result_rows[-1][key])

    # Общий раздел всегда как сумма cold+hot, даже если строки total не заданы вручную.
    for key in ("qT_m3_day", "qhr_l_h", "q_calc_l_s", "q_calc_hr_m3_h", "q_avg_hr_m3_h"):
        totals["total"][key] = totals["cold"][key] + totals["hot"][key]

    heat_flow_kw_max = totals["hot"]["q_calc_hr_m3_h"] * 16.3 if totals["hot"]["q_calc_hr_m3_h"] > 0 else 0.0
    heat_flow_kw_avg = totals["hot"]["q_avg_hr_m3_h"] * 16.3 if totals["hot"]["q_avg_hr_m3_h"] > 0 else 0.0

    return {
        "rows": result_rows,
        "totals": totals,
        "heat": {"max_kw": heat_flow_kw_max, "avg_kw": heat_flow_kw_avg},
    }
    def _infer_prod_sewer_target(name: str, override: str) -> str:
        ov = (override or "").strip().lower()
        if ov in ("domestic", "production"):
            return ov
        n = (name or "").strip().lower()
        production_markers = [
            "цех",
            "завод",
            "производ",
            "пищеблок",
            "столов",
            "прачеч",
            "лаборатор",
            "бассейн",
            "душевые в бытовых помещениях промышленных предприятий",
            "инфекцион",
            "патолого",
            "морг",
            "кров",
        ]
        if any(m in n for m in production_markers):
            return "production"
        return "domestic"
