"""Генерация PDF документов (ФТ-06-03)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Регистрируем шрифт с поддержкой кириллицы (поставляется с reportlab)
_REGISTERED = False


def _register_fonts() -> None:
    """Регистрирует DejaVu Sans (fonts-dejavu-core) — полная поддержка кириллицы."""
    global _REGISTERED
    if _REGISTERED:
        return
    base = "/usr/share/fonts/truetype/dejavu"
    pdfmetrics.registerFont(TTFont("DejaVuSans", f"{base}/DejaVuSans.ttf"))
    pdfmetrics.registerFont(
        TTFont("DejaVuSans-Bold", f"{base}/DejaVuSans-Bold.ttf")
    )

    pdfmetrics.registerFontFamily(
        "DejaVuSans",
        normal="DejaVuSans",
        bold="DejaVuSans-Bold",
        italic="DejaVuSans",  # italic-варианта в core нет, fallback на normal
        boldItalic="DejaVuSans-Bold",
    )
    # Регистрируем в ps2tt_map для ParaParser
    from reportlab.lib import fonts as _rl_fonts

    _rl_fonts._ps2tt_map.update(
        {
            "dejavusans": ("DejaVuSans", 0, 0),
            "dejavusans-bold": ("DejaVuSans", 1, 0),
        }
    )
    _REGISTERED = True


class CPItemData:
    """Простой DTO для позиции КП в PDF."""

    def __init__(
        self,
        index: int,
        article: str | None,
        name: str,
        quantity: int,
        unit_price: Decimal,
        discount_percent: Decimal,
        line_total: Decimal,
    ):
        self.index = index
        self.article = article
        self.name = name
        self.quantity = quantity
        self.unit_price = unit_price
        self.discount_percent = discount_percent
        self.line_total = line_total


def render_proposal_pdf(
    *,
    cp_number: str,
    version: int,
    created_at: str,
    valid_until: str | None,
    seller_company: str,
    seller_inn: str,
    client_company: str,
    client_inn: str,
    client_kpp: str | None,
    items: Sequence[CPItemData],
    total_amount: Decimal,
    payment_terms: str | None,
    delivery_terms: str | None,
    manager_name: str | None,
) -> bytes:
    """Рендерит коммерческое предложение в PDF и возвращает байты."""
    _register_fonts()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"КП {cp_number}",
    )

    # Стили используют базовый шрифт; bold/italic — через теги <b>/<i> в тексте.
    font = "DejaVuSans"
    font_bold = "DejaVuSans-Bold"
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "TitleRu",
        parent=styles["Title"],
        fontName=font,
        fontSize=16,
        alignment=TA_LEFT,
        spaceAfter=12,
    )
    style_h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
    )
    style_normal = ParagraphStyle(
        "Normal",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        leading=13,
    )
    style_right = ParagraphStyle(
        "Right",
        parent=style_normal,
        alignment=TA_RIGHT,
    )

    story = []

    # === Заголовок ===
    story.append(
        Paragraph(
            f"<b>Коммерческое предложение № {cp_number}"
            + (f" (версия {version})" if version > 1 else "")
            + "</b>",
            style_title,
        )
    )
    story.append(
        Paragraph(
            f"Дата формирования: {created_at}"
            + (f"<br/>Действительно до: {valid_until}" if valid_until else ""),
            style_normal,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # === Стороны ===
    story.append(Paragraph("<b>Поставщик</b>", style_h2))
    story.append(
        Paragraph(
            f"<b>{seller_company}</b><br/>ИНН: {seller_inn}", style_normal
        )
    )
    story.append(Paragraph("<b>Покупатель</b>", style_h2))
    kpp_line = f", КПП: {client_kpp}" if client_kpp else ""
    story.append(
        Paragraph(
            f"<b>{client_company}</b><br/>ИНН: {client_inn}{kpp_line}",
            style_normal,
        )
    )

    # === Таблица позиций ===
    story.append(Paragraph("<b>Состав коммерческого предложения</b>", style_h2))
    table_data: list[list] = [
        ["№", "Артикул", "Наименование", "Кол-во", "Цена", "Скидка", "Сумма"]
    ]
    for it in items:
        table_data.append(
            [
                str(it.index),
                it.article or "—",
                Paragraph(it.name, style_normal),
                str(it.quantity),
                f"{it.unit_price:.2f} ₽",
                f"{it.discount_percent:.0f}%"
                if it.discount_percent
                else "—",
                f"{it.line_total:.2f} ₽",
            ]
        )
    table_data.append(
        [
            "",
            "",
            Paragraph("<b>ИТОГО</b>", style_normal),
            "",
            "",
            "",
            f"{total_amount:.2f} ₽",
        ]
    )
    table = Table(
        table_data,
        colWidths=[
            0.8 * cm,  # №
            2.5 * cm,  # Артикул
            6.5 * cm,  # Наименование
            1.5 * cm,  # Кол-во
            2.0 * cm,  # Цена
            1.5 * cm,  # Скидка
            2.7 * cm,  # Сумма
        ],
        repeatRows=1,
    )
    # В TableStyle FONT можно указывать явный bold font — он применяется к ячейке
    # целиком (а не через парсер ParaParser), поэтому это безопасно.
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font, 9),
                ("FONT", (0, 0), (-1, 0), font_bold, 9),
                ("FONT", (0, -1), (-1, -1), font_bold, 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("ALIGN", (4, 0), (6, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)

    # === Условия ===
    if payment_terms:
        story.append(Paragraph("<b>Условия оплаты</b>", style_h2))
        story.append(Paragraph(payment_terms, style_normal))
    if delivery_terms:
        story.append(Paragraph("<b>Условия поставки</b>", style_h2))
        story.append(Paragraph(delivery_terms, style_normal))

    # === Менеджер ===
    if manager_name:
        story.append(Spacer(1, 1 * cm))
        story.append(
            Paragraph(
                f"<i>Подготовил: {manager_name}</i>", style_normal
            )
        )

    doc.build(story)
    return buf.getvalue()
