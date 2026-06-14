"""Shared RDL-2016 building blocks for Theragen paginated reports.

Extracted from build_paginated.py (the leadership Status Report) so the
governance / document report generators reuse the exact, production-proven RDL
structure: a PBIDATASET data source bound to the published semantic model, DAX
datasets (flattened columns bound as [Alias]), and tablix/textbox helpers that
already encode the renderer fixes (format-in-expression, dataset-scoped
standalone aggregates to avoid rsFieldReferenceAmbiguous, NoRowsMessage).

Each report generator composes a body from these helpers and calls build_rdl().
All datasets target the same published model as build_paginated.py, so every
paginated report and the interactive pages share one source of truth.
"""
import base64
import os
import uuid
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, "assets", "theragen-logo.jpeg")

# Published semantic model in the Power BI service (Playground / Theragen
# Project Planner) - the same target build_paginated.py uses. DATASET_GUID:
# open the model in the service; the URL contains .../datasets/<guid>/details.
TENANT_ID = "f0b72488-7082-488a-a7e8-eada97bd842d"
WORKSPACE_NAME = "Playground"
DATASET_NAME = "Theragen Project Planner"
DATASET_GUID = "e3e1f151-0f7d-4bbe-8428-d74dcfa640d4"

TEAL = "#219A80"
INK = "#252423"
GRID = "#DCE4E3"
LIGHT = "#F4F7F6"
FONT = "Segoe UI"

# Brand-aligned status / decision palette (shared across reports).
GREEN, YELLOW, RED, DARKRED = "#107C10", "#C19C00", "#C0392B", "#8B1A1A"
PURPLE, BLUE = "#6B3FA0", "#2E86AB"

# Decision colour: Approved green, Pending grey, Deferred amber, Rejected red.
DECISION_COLOR = ('=Switch(Fields!Decision.Value="Approved","{g}",'
                  'Fields!Decision.Value="Rejected","{r}",'
                  'Fields!Decision.Value="Deferred","{y}",True,"#605E5C")').format(
                      g=GREEN, r=RED, y=YELLOW)
# CR status colour across the lifecycle.
CRSTATUS_COLOR = ('=Switch(Fields!Status.Value="Verified","{g}",'
                  'Fields!Status.Value="Closed","{g}",'
                  'Fields!Status.Value="Rejected","{r}",'
                  'Fields!Status.Value="Implementing","{b}",True,"#605E5C")').format(
                      g=GREEN, r=RED, b=BLUE)


def textrun(value, *, size="8pt", bold=False, color=INK, italic=False):
    style = [f"<FontFamily>{FONT}</FontFamily>", f"<FontSize>{size}</FontSize>",
             f"<Color>{color}</Color>"]
    if bold:
        style.append("<FontWeight>Bold</FontWeight>")
    if italic:
        style.append("<FontStyle>Italic</FontStyle>")
    return f"<TextRun><Value>{value}</Value><Style>{''.join(style)}</Style></TextRun>"


def para(runs, align="Left"):
    return (f"<Paragraph><TextRuns>{runs}</TextRuns>"
            f"<Style><TextAlign>{align}</TextAlign></Style></Paragraph>")


def textbox(name, runs_xml, left, top, width, height, *, bg=None, border=GRID,
            align="Left", valign="Top", pad="2pt", grow=True):
    if bg is None:
        bg = "#FFFFFF"
    border_xml = (f"<Border><Color>{border}</Color><Style>Solid</Style></Border>"
                  if border else "<Border><Style>None</Style></Border>")
    style = [border_xml,
             f"<PaddingLeft>{pad}</PaddingLeft><PaddingRight>{pad}</PaddingRight>",
             "<PaddingTop>2pt</PaddingTop><PaddingBottom>2pt</PaddingBottom>",
             f"<VerticalAlign>{valign}</VerticalAlign>"]
    if bg and bg != "none":
        style.insert(1, f"<BackgroundColor>{bg}</BackgroundColor>")
    return f"""<Textbox Name="{name}">
  <CanGrow>{'true' if grow else 'false'}</CanGrow>
  <KeepTogether>true</KeepTogether>
  <Paragraphs>{runs_xml}</Paragraphs>
  <Top>{top}in</Top><Left>{left}in</Left><Height>{height}in</Height><Width>{width}in</Width>
  <Style>{''.join(style)}</Style>
</Textbox>"""


def label_value_box(name, label, value_expr, left, top, width, height,
                    *, vsize="10pt", vbold=True, vcolor=INK, align="Left"):
    # label is always literal text -> escape it (&, <, >); value_expr is an
    # expression (=...) whose literal parts the caller pre-escapes.
    runs = (para(textrun(escape(label), size="6.5pt", bold=True, color=TEAL), align) +
            para(textrun(value_expr, size=vsize, bold=vbold, color=vcolor), align))
    return textbox(name, runs, left, top, width, height, align=align)


def section_title(name, text, left, top, width):
    """A teal section band - the visual separator between dossier sections."""
    return textbox(name, para(textrun(escape(text), size="9pt", bold=True,
                                       color="#FFFFFF")),
                   left, top, width, 0.24, bg=TEAL, border=TEAL, valign="Middle")


def tablix(name, dataset, columns, left, top, width, *, header_bg=TEAL,
           detail_size="7.5pt", sort_field=None, sort_desc=False, design_h=0.42,
           no_rows="No rows."):
    """columns: list of (header, field_expr, width_in, align[, format[, color[, bold]]])."""
    total_w = sum(c[2] for c in columns)
    scale = width / total_w
    cols_xml = "".join(f"<TablixColumn><Width>{c[2]*scale:.3f}in</Width></TablixColumn>"
                       for c in columns)
    hdr_cells, det_cells = [], []
    for i, c in enumerate(columns):
        header, expr, _, align = c[0], c[1], c[2], c[3]
        fmt = c[4] if len(c) > 4 else None
        color = c[5] if len(c) > 5 else INK
        bold = c[6] if len(c) > 6 else False
        # Format in the expression itself - style-level <Format> is unreliable
        # across renderers (and never print 12:00:00 AM on pure dates).
        if fmt and expr.startswith("="):
            expr = f'=Format({expr[1:]}, "{fmt}")'
            fmt = None
        hdr_cells.append(
            "<TablixCell><CellContents>" + f"""<Textbox Name="{name}_h{i}">
              <CanGrow>true</CanGrow>
              <Paragraphs>{para(textrun(escape(header), size='7pt', bold=True, color='#FFFFFF'), align)}</Paragraphs>
              <Style><Border><Color>{header_bg}</Color><Style>Solid</Style></Border>
              <BackgroundColor>{header_bg}</BackgroundColor>
              <PaddingLeft>3pt</PaddingLeft><PaddingRight>3pt</PaddingRight>
              <PaddingTop>2pt</PaddingTop><PaddingBottom>2pt</PaddingBottom>
              <VerticalAlign>Middle</VerticalAlign></Style>
            </Textbox>""" + "</CellContents></TablixCell>")
        style_fmt = f"<Format>{fmt}</Format>" if fmt else ""
        det_cells.append(
            "<TablixCell><CellContents>" + f"""<Textbox Name="{name}_d{i}">
              <CanGrow>true</CanGrow>
              <Paragraphs>{para(textrun(expr, size=detail_size, color=color, bold=bold), align)}</Paragraphs>
              <Style><Border><Color>{GRID}</Color><Style>Solid</Style></Border>
              <BackgroundColor>#FFFFFF</BackgroundColor>
              {style_fmt}
              <PaddingLeft>3pt</PaddingLeft><PaddingRight>3pt</PaddingRight>
              <PaddingTop>2pt</PaddingTop><PaddingBottom>2pt</PaddingBottom></Style>
            </Textbox>""" + "</CellContents></TablixCell>")
    sort_xml = ""
    if sort_field:
        direction = "<SortExpression><Value>=Fields!%s.Value</Value>%s</SortExpression>" % (
            sort_field, "<Direction>Descending</Direction>" if sort_desc else "")
        sort_xml = f"<SortExpressions>{direction}</SortExpressions>"
    return f"""<Tablix Name="{name}">
  <TablixBody>
    <TablixColumns>{cols_xml}</TablixColumns>
    <TablixRows>
      <TablixRow><Height>0.22in</Height><TablixCells>{''.join(hdr_cells)}</TablixCells></TablixRow>
      <TablixRow><Height>0.2in</Height><TablixCells>{''.join(det_cells)}</TablixCells></TablixRow>
    </TablixRows>
  </TablixBody>
  <TablixColumnHierarchy><TablixMembers>{'<TablixMember />' * len(columns)}</TablixMembers></TablixColumnHierarchy>
  <TablixRowHierarchy><TablixMembers>
    <TablixMember><KeepWithGroup>After</KeepWithGroup></TablixMember>
    <TablixMember><Group Name="{name}_Details" />{sort_xml}</TablixMember>
  </TablixMembers></TablixRowHierarchy>
  <DataSetName>{dataset}</DataSetName>
  <NoRowsMessage>{escape(no_rows)}</NoRowsMessage>
  <Top>{top}in</Top><Left>{left}in</Left><Height>{design_h}in</Height><Width>{width:.3f}in</Width>
  <Style><Border><Style>None</Style></Border></Style>
</Tablix>"""


# Field type overrides by alias (anything not listed defaults to System.String).
_TYPES = {"Int64": "Int64", "Decimal": "Decimal", "DateTime": "DateTime",
          "Boolean": "Boolean"}


def dataset_xml(name, dax, fields, *, params=(), types=None):
    """A DAX dataset against the published model. fields are bound as [Alias]
    (the DAX flattened-rowset naming), which build_paginated.py verified against
    Theragen's production .rdls - binding bare names leaves every field null."""
    types = types or {}
    qp = ""
    if params:
        body = "".join(
            f'<QueryParameter Name="{p}"><Value>=Parameters!{p}.Value</Value></QueryParameter>'
            for p in params)
        qp = f"<QueryParameters>{body}</QueryParameters>"
    fields_xml = "".join(
        f'<Field Name="{f}"><rd:TypeName>System.{types.get(f, "String")}</rd:TypeName>'
        f'<DataField>[{f}]</DataField></Field>' for f in fields)
    return f"""<DataSet Name="{name}">
  <Query>
    <DataSourceName>TheragenModel</DataSourceName>
    {qp}
    <CommandText>{escape(dax)}</CommandText>
  </Query>
  <Fields>{fields_xml}</Fields>
</DataSet>"""


def _data_source():
    return f"""<DataSource Name="TheragenModel">
      <rd:SecurityType>None</rd:SecurityType>
      <ConnectionProperties>
        <DataProvider>PBIDATASET</DataProvider>
        <ConnectString>Data Source=pbiazure://api.powerbi.com/;Identity Provider="https://login.microsoftonline.com/organizations, https://analysis.windows.net/powerbi/api, {TENANT_ID}";Initial Catalog=sobe_wowvirtualserver-{DATASET_GUID};Integrated Security=ClaimsToken</ConnectString>
      </ConnectionProperties>
      <rd:DataSourceID>{uuid.uuid5(uuid.NAMESPACE_URL, 'thg-bi/paginated/datasource')}</rd:DataSourceID>
      <rd:PowerBIWorkspaceName>{WORKSPACE_NAME}</rd:PowerBIWorkspaceName>
      <rd:PowerBIDatasetName>{DATASET_NAME}</rd:PowerBIDatasetName>
    </DataSource>"""


def picker_parameter(name, prompt, dataset, value_field, label_field):
    """A dropdown parameter whose valid values come from a list dataset."""
    return f"""<ReportParameter Name="{name}">
      <DataType>String</DataType>
      <DefaultValue>
        <DataSetReference><DataSetName>{dataset}</DataSetName><ValueField>{value_field}</ValueField></DataSetReference>
      </DefaultValue>
      <Prompt>{escape(prompt)}</Prompt>
      <ValidValues>
        <DataSetReference><DataSetName>{dataset}</DataSetName><ValueField>{value_field}</ValueField><LabelField>{label_field}</LabelField></DataSetReference>
      </ValidValues>
    </ReportParameter>"""


def logo_b64():
    with open(LOGO, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def logo_image(left=0.0, top=0.05, width=1.5, height=0.4):
    return ('<Image Name="LogoImg"><Source>Embedded</Source><Value>TheragenLogo</Value>'
            '<Sizing>FitProportional</Sizing>'
            f'<Top>{top}in</Top><Left>{left}in</Left><Height>{height}in</Height><Width>{width}in</Width>'
            '<Style><Border><Style>None</Style></Border></Style></Image>')


def build_rdl(*, report_id_seed, datasets, body_items, body_height, body_width,
              parameters=(), param_columns=1, page_w="11in", page_h="8.5in",
              margin="0.35in", embed_logo=True):
    """Assemble a full RDL 2016 document. body_items are absolutely positioned
    report items (tablixes CanGrow + push items below them down a page)."""
    datasets_xml = "".join(datasets)
    images = ""
    if embed_logo:
        images = (f'<EmbeddedImages><EmbeddedImage Name="TheragenLogo">'
                  f'<MIMEType>image/jpeg</MIMEType><ImageData>{logo_b64()}</ImageData>'
                  f'</EmbeddedImage></EmbeddedImages>')
    params_xml = ""
    layout_xml = ""
    if parameters:
        params_xml = f"<ReportParameters>{''.join(parameters)}</ReportParameters>"
        # one cell per parameter, laid out left-to-right
        cells = "".join(
            f"<CellDefinition><ColumnIndex>{i}</ColumnIndex><RowIndex>0</RowIndex>"
            f"<ParameterName>{n}</ParameterName></CellDefinition>"
            for i, n in enumerate(param_columns if isinstance(param_columns, list) else
                                  [p.split('"')[1] for p in parameters]))
        ncols = len(parameters)
        layout_xml = (f"<ReportParametersLayout><GridLayoutDefinition>"
                      f"<NumberOfColumns>{ncols}</NumberOfColumns><NumberOfRows>1</NumberOfRows>"
                      f"<CellDefinitions>{cells}</CellDefinitions>"
                      f"</GridLayoutDefinition></ReportParametersLayout>")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition"
        xmlns:rd="http://schemas.microsoft.com/SQLServer/reporting/reportdesigner">
  <AutoRefresh>0</AutoRefresh>
  <DataSources>{_data_source()}</DataSources>
  <DataSets>{datasets_xml}</DataSets>
  {images}
  <ReportSections>
    <ReportSection>
      <Body>
        <ReportItems>{''.join(body_items)}</ReportItems>
        <Height>{body_height}in</Height>
        <Style />
      </Body>
      <Width>{body_width}in</Width>
      <Page>
        <PageHeight>{page_h}</PageHeight>
        <PageWidth>{page_w}</PageWidth>
        <LeftMargin>{margin}</LeftMargin>
        <RightMargin>{margin}</RightMargin>
        <TopMargin>{margin}</TopMargin>
        <BottomMargin>{margin}</BottomMargin>
        <Style />
      </Page>
    </ReportSection>
  </ReportSections>
  {params_xml}
  {layout_xml}
  <rd:ReportUnitType>Inch</rd:ReportUnitType>
  <rd:ReportID>{uuid.uuid5(uuid.NAMESPACE_URL, report_id_seed)}</rd:ReportID>
</Report>"""
