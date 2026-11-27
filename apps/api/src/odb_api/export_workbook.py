"""Modelo Excel: apresentação e cinco tabelas rastreáveis, sem fórmulas de fonte."""

from __future__ import annotations

import io
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
import xlsxwriter

NAVY = "#071D41"
BLUE = "#1351B4"
MAX_CELL = 32_767
MAX_ROWS = 1_048_575


class WorkbookLimitError(ValueError):
    """Conteúdo não cabe em uma planilha sem perda."""


def _text(value: Any) -> str:
    """Serializa estruturas e mantém códigos/decimais textuais."""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)


def _metadata_rows(meta: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Particiona campos extensos com ordem explícita, sem cortar o conteúdo."""
    out: list[dict[str, Any]] = []
    for key, value in meta.items():
        text = _text(value)
        parts = [text[i : i + MAX_CELL] for i in range(0, len(text), MAX_CELL)] or [""]
        out.extend(
            {"campo": key, "parte": i, "partes": len(parts), "valor": part}
            for i, part in enumerate(parts, 1)
        )
    return out


def _table(
    book: Any,
    name: str,
    records: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
    meta: Mapping[str, Any],
) -> None:
    """Escreve tabelas em A1; a marca fica fora das células tabulares."""
    if len(records) > MAX_ROWS:
        raise WorkbookLimitError(f"a aba {name} excede o limite de linhas do Excel")
    sheet = book.add_worksheet(name)
    sheet.hide_gridlines(2)
    sheet.freeze_panes(1, 1)
    sheet.set_tab_color(BLUE if name == "dados" else NAVY)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.repeat_rows(0)
    sheet.set_header("&LGerado pelo Open Data Brasil")
    generated = str(meta["gerado_em"]).replace("&", "&&")
    sheet.set_footer(f"&Lhttps://opendatabrasil.org&C{generated}&RPágina &P de &N")
    header = book.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": NAVY,
            "text_wrap": True,
            "valign": "vcenter",
        }
    )
    sheet.set_row(0, 35)
    for i, column in enumerate(columns):
        width = 48 if column in {"definicao", "valor", "url", "lacunas", "metodo"} else 24
        sheet.set_column(i, i, width)
        if name == "dados" and column in {"indicator_id", "kpi_id", "release_id", "block_id"}:
            sheet.set_column(i, i, width, None, {"hidden": True, "level": 1})
        sheet.write_string(0, i, column, header)
    for row, record in enumerate(records, 1):
        for col, column in enumerate(columns):
            value = record.get(column)
            if value is None:
                continue
            if isinstance(value, (bool, int, float)):
                sheet.write(row, col, value)
            else:
                text = _text(value)
                if len(text) > MAX_CELL:
                    msg = f"campo {column} da aba {name} excede o limite do Excel"
                    raise WorkbookLimitError(msg)
                sheet.write_string(row, col, text)
    # Uma tabela vazia não ganha uma observação fictícia. Mantém cabeçalho e filtro.
    if records:
        sheet.add_table(
            0,
            0,
            len(records),
            len(columns) - 1,
            {
                "name": "odb_" + name,
                "style": "Table Style Medium 2",
                "columns": [{"header": column, "header_format": header} for column in columns],
            },
        )
    else:
        sheet.autofilter(0, 0, 0, len(columns) - 1)


def render_workbook(data: pl.DataFrame, meta: Mapping[str, Any]) -> bytes:
    """Projeta os mesmos dados/metadados comuns; capa não é uma observação."""
    output = io.BytesIO()
    with xlsxwriter.Workbook(
        output, {"strings_to_formulas": False, "strings_to_urls": False}
    ) as book:
        book.set_properties(
            {
                "title": meta["kpi"].get("label", "Dados exportados"),
                "author": "Open Data Brasil",
                "company": "Open Data Brasil",
                "created": datetime.fromisoformat(str(meta["gerado_em"])),
            }
        )
        for key, value in meta["artifact"].items():
            book.set_custom_property(key, _text(value))
        cover = book.add_worksheet("Apresentação")
        cover.hide_gridlines(2)
        cover.set_column("A:L", 10)
        title = book.add_format(
            {
                "bg_color": NAVY,
                "font_color": "#FFFFFF",
                "bold": True,
                "font_size": 25,
                "valign": "vcenter",
                "text_wrap": True,
            }
        )
        body = book.add_format(
            {"font_color": NAVY, "font_size": 12, "text_wrap": True, "valign": "vcenter"}
        )
        link = book.add_format({"bg_color": BLUE, "font_color": "#FFFFFF", "bold": True})
        logo = Path(__file__).parent / "assets" / "logo-open-data-brasil.png"
        if logo.is_file():
            cover.insert_image(
                "B2",
                str(logo),
                {"x_scale": 0.35, "y_scale": 0.35, "description": "Open Data Brasil"},
            )
        cover.merge_range("B7:K10", meta["kpi"].get("label", "Dados exportados"), title)
        cover.merge_range(
            "B12:K14", f"{data.height} observações · Dados, dicionário, fontes e métodos", body
        )
        for i, (sheet, label) in enumerate(
            (
                ("dados", "Dados"),
                ("metadados", "Metadados"),
                ("dicionario", "Dicionário"),
                ("fontes", "Fontes"),
                ("metodos", "Métodos"),
            ),
            17,
        ):
            cover.merge_range(i, 1, i, 10, "", link)
            cover.write_url(i, 1, f"internal:'{sheet}'!A1", link, label)
            cover.set_row(i, 27)
        cover.merge_range("B25:K28", meta["aviso"], body)
        cover.merge_range(
            "B30:K33",
            "O arquivo mantém os períodos separados. Acumulados apenas "
            "visuais do gráfico não são exportados. Consulte as lacunas documentais "
            "e a seleção efetiva em Metadados.",
            body,
        )
        cover.set_header("&LGerado pelo Open Data Brasil")
        cover.set_footer(f"&Lhttps://opendatabrasil.org&C{meta['gerado_em']}&RPágina &P de &N")
        cover.print_area("A1:L35")
        cover.fit_to_pages(1, 1)
        _table(book, "dados", data.to_dicts(), data.columns, meta)
        _table(book, "metadados", _metadata_rows(meta), ["campo", "parte", "partes", "valor"], meta)
        for name, columns in (
            ("dicionario", ["campo", "tipo", "definicao", "codigo", "fonte"]),
            ("fontes", ["source_id", "produtor", "url", "edicao", "secao", "afirmacao", "licenca"]),
            (
                "metodos",
                ["method_id", "tipo", "definicao", "metodo", "universo", "limites", "lacunas"],
            ),
        ):
            _table(book, name, meta.get(name, []), columns, meta)
    return output.getvalue()
