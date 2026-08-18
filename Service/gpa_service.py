"""本科生成绩与绩点换算规则。"""

from decimal import Decimal, ROUND_HALF_UP


GPA_RULE_NOTE = (
    "本科生成绩和绩点计算办法的百分制区间换算："
    "90-100=4.0，85-89=3.7，82-84=3.3，78-81=3.0，"
    "75-77=2.7，72-74=2.3，68-71=2.0，64-67=1.5，60-63=1.0，60分以下=0。"
    "优秀、良好、中等、合格等等级成绩保留原始等级，不按百分制虚拟换算。"
)


def grade_point_for_score(score: Decimal | float | int | None) -> Decimal | None:
    if score is None:
        return None
    value = Decimal(str(score))
    if value >= 90:
        point = Decimal("4.0")
    elif value >= 85:
        point = Decimal("3.7")
    elif value >= 82:
        point = Decimal("3.3")
    elif value >= 78:
        point = Decimal("3.0")
    elif value >= 75:
        point = Decimal("2.7")
    elif value >= 72:
        point = Decimal("2.3")
    elif value >= 68:
        point = Decimal("2.0")
    elif value >= 64:
        point = Decimal("1.5")
    elif value >= 60:
        point = Decimal("1.0")
    else:
        point = Decimal("0.0")
    return point.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)


def weighted_gpa(records) -> Decimal | None:
    total_credits = Decimal("0")
    weighted_points = Decimal("0")
    for record in records:
        point = record.get("grade_point") if isinstance(record, dict) else getattr(record, "grade_point", None)
        credits = record.get("credits") if isinstance(record, dict) else getattr(record, "credits", None)
        if point in (None, "") or credits in (None, ""):
            continue
        total_credits += Decimal(str(credits))
        weighted_points += Decimal(str(point)) * Decimal(str(credits))
    if not total_credits:
        return None
    return (weighted_points / total_credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
