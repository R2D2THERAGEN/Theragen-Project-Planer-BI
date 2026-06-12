"""Emit the Theragen Status Report paginated report (.rdl).

Pixel-perfect leadership one-pager mirroring the Sync 3.0 status deck,
parameterized by @ProjectCode and bound to the published Power BI semantic
model (all DAX datasets reuse the model's measures - no duplicated logic).

Output: paginated/Theragen Status Report.rdl (RDL 2016, letter landscape).
After the semantic model is published, open the .rdl in Power BI Report
Builder, repoint the data source to the published model, and publish to the
same workspace.
"""
import base64
import os
import uuid
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "paginated", "Theragen Status Report.rdl")
LOGO = os.path.join(ROOT, "assets", "theragen-logo.jpeg")

TEAL = "#219A80"
INK = "#252423"
GRID = "#DCE4E3"
LIGHT = "#F4F7F6"
FONT = "Segoe UI"

# Status colors lifted from the Theragen status deck's text runs.
DECK_GREEN, DECK_YELLOW, DECK_RED = "#00FF00", "#D6D60D", "#FF0000"
DECK_KEY_YELLOW, DECK_HOLD, DECK_CANCEL = "#FFFF00", "#7030A0", "#00B0F0"

AREA_COLOR = ('=Switch(Fields!AreaStatus.Value="Green","{g}",'
              'Fields!AreaStatus.Value="Yellow","{y}",'
              'Fields!AreaStatus.Value="Red","{r}",True,"#000000")').format(
                  g=DECK_GREEN, y=DECK_YELLOW, r=DECK_RED)
WS_COLOR = ('=Switch(Fields!WsStatus.Value="ON TRACK","{g}",'
            'Fields!WsStatus.Value="AT RISK","{y}",True,"#000000")').format(
                g=DECK_GREEN, y=DECK_YELLOW)
SEV_COLOR = ('=Switch(Fields!Severity.Value="Critical","{r}",'
             'Fields!Severity.Value="High","{r}",'
             'Fields!Severity.Value="Medium","{y}",True,"#000000")').format(
                 r=DECK_RED, y=DECK_YELLOW)

# ---------------------------------------------------------------- datasets
# Every output column is aliased through SELECTCOLUMNS/ROW so RDL field
# DataField names are clean single tokens.
DATASETS = {
    "DsProjectList": dict(
        dax=(
            "EVALUATE SELECTCOLUMNS('Project', \"ProjectCode\", 'Project'[Project Code], "
            "\"ProjectName\", 'Project'[Project Name]) ORDER BY [ProjectName]"
        ),
        fields=["ProjectCode", "ProjectName"], params=False),
    "DsHeader": dict(
        dax=(
            "EVALUATE CALCULATETABLE(ROW("
            "\"ProjectName\", SELECTEDVALUE('Project'[Project Name]), "
            "\"ProjectManager\", [Project Manager (Selected)], "
            "\"TargetDate\", [Target Date Completion], "
            "\"Phase\", [Current Phase], "
            "\"MainStatus\", [Main Status], "
            "\"StatusColor\", [Status Color], "
            "\"Description\", [Project Description (Selected)], "
            "\"BusinessValue\", [Business Value (Selected)], "
            "\"ReportDate\", [Report Date], "
            "\"DecisionsNeeded\", [Decisions Needed (Latest)]), "
            "TREATAS({@ProjectCode}, 'Project'[Project Code]))"
        ),
        fields=["ProjectName", "ProjectManager", "TargetDate", "Phase", "MainStatus",
                "StatusColor", "Description", "BusinessValue", "ReportDate",
                "DecisionsNeeded"], params=True),
    "DsHealth": dict(
        dax=(
            "EVALUATE SELECTCOLUMNS(SUMMARIZECOLUMNS('Knowledge Area'[Knowledge Area], "
            "'Knowledge Area'[KA Sort], TREATAS({@ProjectCode}, 'Project'[Project Code]), "
            "\"AreaStatusM\", [Latest Area Status]), "
            "\"KnowledgeArea\", 'Knowledge Area'[Knowledge Area], "
            "\"KASort\", 'Knowledge Area'[KA Sort], "
            "\"AreaStatus\", [AreaStatusM]) ORDER BY [KASort]"
        ),
        fields=["KnowledgeArea", "KASort", "AreaStatus"], params=True),
    "DsRaid": dict(
        dax=(
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Risk', "
            "TREATAS({@ProjectCode}, 'Project'[Project Code])), "
            "\"RaidType\", 'Risk'[RAID Type], "
            "\"Description\", 'Risk'[Risk Description], "
            "\"Owner\", 'Risk'[Owner], "
            "\"DueDate\", 'Risk'[Due Date], "
            "\"Score\", 'Risk'[Risk Score], "
            "\"Severity\", 'Risk'[Severity], "
            "\"RiskStatus\", 'Risk'[Risk Status]) ORDER BY [Score] DESC"
        ),
        fields=["RaidType", "Description", "Owner", "DueDate", "Score", "Severity",
                "RiskStatus"], params=True),
    "DsWorkstreams": dict(
        dax=(
            "EVALUATE SELECTCOLUMNS(SUMMARIZECOLUMNS('WBS Element'[Deliverable], "
            "TREATAS({@ProjectCode}, 'Project'[Project Code]), "
            "\"StartDateM\", [Workstream Start], "
            "\"TargetDateM\", [Workstream Target], "
            "\"PctCompleteM\", [Pct Complete (Duration Weighted)], "
            "\"WsStatusM\", [Workstream Status]), "
            "\"Deliverable\", 'WBS Element'[Deliverable], "
            "\"StartDate\", [StartDateM], \"TargetDate\", [TargetDateM], "
            "\"PctComplete\", [PctCompleteM], \"WsStatus\", [WsStatusM]) "
            "ORDER BY [StartDate]"
        ),
        fields=["Deliverable", "StartDate", "TargetDate", "PctComplete", "WsStatus"],
        params=True),
    "DsAccomplishments": dict(
        dax=(
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Recent Accomplishment', "
            "TREATAS({@ProjectCode}, 'Project'[Project Code])), "
            "\"Accomplishment\", 'Recent Accomplishment'[Accomplishment], "
            "\"Source\", 'Recent Accomplishment'[Source], "
            "\"CompletedDate\", 'Recent Accomplishment'[Completed Date]) "
            "ORDER BY [CompletedDate] DESC"
        ),
        fields=["Accomplishment", "Source", "CompletedDate"], params=True),
    "DsGauge": dict(
        dax=(
            "EVALUATE CALCULATETABLE(ROW("
            "\"AvgScore\", [Avg Risk Score (Open)], "
            "\"RiskRating\", [Risk Rating], "
            "\"RatingColor\", [Risk Rating Color]), "
            "TREATAS({@ProjectCode}, 'Project'[Project Code]))"
        ),
        fields=["AvgScore", "RiskRating", "RatingColor"], params=True),
    "DsNextSteps": dict(
        dax=(
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Upcoming Next Step', "
            "TREATAS({@ProjectCode}, 'Project'[Project Code])), "
            "\"NextStep\", 'Upcoming Next Step'[Next Step], "
            "\"Owner\", 'Upcoming Next Step'[Owner], "
            "\"TargetDate\", 'Upcoming Next Step'[Target Date]) "
            "ORDER BY [TargetDate]"
        ),
        fields=["NextStep", "Owner", "TargetDate"], params=True),
}


def textrun(value, *, size="8pt", bold=False, color=INK, italic=False):
    style = [f"<FontFamily>{FONT}</FontFamily>", f"<FontSize>{size}</FontSize>",
             f"<Color>{color}</Color>"]
    if bold:
        style.append("<FontWeight>Bold</FontWeight>")
    if italic:
        style.append("<FontStyle>Italic</FontStyle>")
    return (f"<TextRun><Value>{value}</Value><Style>{''.join(style)}</Style></TextRun>")


def textbox(name, runs_xml, left, top, width, height, *, bg=None, border=GRID,
            align="Left", valign="Top", pad="2pt", grow=True):
    style = [f"<Border><Color>{border}</Color><Style>{'Solid' if border else 'None'}</Style></Border>",
             f"<PaddingLeft>{pad}</PaddingLeft><PaddingRight>{pad}</PaddingRight>",
             "<PaddingTop>2pt</PaddingTop><PaddingBottom>2pt</PaddingBottom>",
             f"<VerticalAlign>{valign}</VerticalAlign>"]
    if bg:
        style.insert(1, f"<BackgroundColor>{bg}</BackgroundColor>")
    return f"""<Textbox Name="{name}">
  <CanGrow>{'true' if grow else 'false'}</CanGrow>
  <KeepTogether>true</KeepTogether>
  <Paragraphs>{runs_xml}</Paragraphs>
  <Top>{top}in</Top><Left>{left}in</Left><Height>{height}in</Height><Width>{width}in</Width>
  <Style>{''.join(style)}</Style>
</Textbox>"""


def para(runs, align="Left"):
    return (f"<Paragraph><TextRuns>{runs}</TextRuns>"
            f"<Style><TextAlign>{align}</TextAlign></Style></Paragraph>")


def label_value_box(name, label, value_expr, left, top, width, height,
                    *, vsize="10pt", vbold=True, vcolor=INK, align="Left"):
    runs = (para(textrun(label, size="6.5pt", bold=True, color=TEAL), align) +
            para(textrun(value_expr, size=vsize, bold=vbold, color=vcolor), align))
    return textbox(name, runs, left, top, width, height, align=align)


def tablix(name, dataset, columns, left, top, width, *, header_bg=TEAL,
           detail_size="7.5pt", sort_field=None, sort_desc=False):
    """columns: list of (header, field_expr, width_in, align[, format[, color[, bold]]])"""
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
  <NoRowsMessage>No rows for the selected Project parameter.</NoRowsMessage>
  <Top>{top}in</Top><Left>{left}in</Left><Height>0.42in</Height><Width>{width:.3f}in</Width>
  <Style><Border><Style>None</Style></Border></Style>
</Tablix>"""


def risk_gauge(left, top, width, height):
    """Radial severity gauge: avg open-risk score on 0-25 with PMI band colors
    (LOW <6, MODERATE <12, HIGH <20, CRITICAL <=25) and needle pointer."""
    bands = [("BandLow", 0, 6, DECK_GREEN), ("BandModerate", 6, 12, DECK_YELLOW),
             ("BandHigh", 12, 20, DECK_RED), ("BandCritical", 20, 25, "#C00000")]
    ranges = "".join(
        f"""<ScaleRange Name="{n}">
              <StartValue><Value>{a}</Value></StartValue>
              <EndValue><Value>{b}</Value></EndValue>
              <StartWidth>8</StartWidth><EndWidth>8</EndWidth>
              <Style><Border><Style>None</Style></Border><BackgroundColor>{c}</BackgroundColor></Style>
            </ScaleRange>""" for n, a, b, c in bands)
    return f"""<GaugePanel Name="RiskGauge">
  <RadialGauges>
    <RadialGauge Name="RiskRadial">
      <GaugeScales>
        <RadialScale Name="RiskScale">
          <GaugePointers>
            <RadialPointer Name="RiskPointer">
              <GaugeInputValue><Value>=First(Fields!AvgScore.Value)</Value></GaugeInputValue>
              <Type>Needle</Type>
              <Style><Border><Style>None</Style></Border><BackgroundColor>{INK}</BackgroundColor></Style>
            </RadialPointer>
          </GaugePointers>
          <ScaleRanges>{ranges}</ScaleRanges>
          <MaximumValue><Value>25</Value></MaximumValue>
          <MinimumValue><Value>0</Value></MinimumValue>
          <Interval>5</Interval>
          <Style><Border><Style>None</Style></Border><FontSize>6pt</FontSize></Style>
        </RadialScale>
      </GaugeScales>
    </RadialGauge>
  </RadialGauges>
  <DataSetName>DsGauge</DataSetName>
  <Top>{top}in</Top><Left>{left}in</Left><Height>{height}in</Height><Width>{width}in</Width>
  <Style><Border><Color>{GRID}</Color><Style>Solid</Style></Border></Style>
</GaugePanel>"""


def dataset_xml(name, d):
    qp = ("""<QueryParameters><QueryParameter Name="@ProjectCode">
            <Value>=Parameters!ProjectCode.Value</Value>
          </QueryParameter></QueryParameters>""" if d["params"] else "")
    fields = "".join(
        f'<Field Name="{f}"><DataField>{f}</DataField>'
        f'<rd:TypeName>System.Object</rd:TypeName></Field>' for f in d["fields"])
    return f"""<DataSet Name="{name}">
  <Query>
    <DataSourceName>TheragenModel</DataSourceName>
    {qp}
    <CommandText>{escape(d["dax"])}</CommandText>
  </Query>
  <Fields>{fields}</Fields>
</DataSet>"""


def build():
    # Inside a tablix, plain Fields! references resolve against the region's
    # dataset. Standalone textboxes in a multi-dataset report MUST use a
    # dataset-scoped aggregate or the service rejects the .rdl with
    # rsFieldReferenceAmbiguous.
    F = "=Fields!{}.Value".format
    FH = '=First(Fields!{}.Value, "DsHeader")'.format
    body_items = []

    # --- Row A: logo + verify the project (top 0 .. 0.55) ------------------
    body_items.append(
        '<Image Name="LogoImg"><Source>Embedded</Source><Value>TheragenLogo</Value>'
        '<Sizing>FitProportional</Sizing>'
        '<Top>0.05in</Top><Left>0in</Left><Height>0.4in</Height><Width>1.5in</Width>'
        '<Style><Border><Style>None</Style></Border></Style></Image>')
    body_items.append(label_value_box("HdrName", "THERAGEN PROJECT NAME",
                                      FH("ProjectName"), 1.58, 0, 2.7, 0.5, vsize="11pt"))
    body_items.append(label_value_box("HdrPM", "PROJECT MANAGER",
                                      FH("ProjectManager"), 4.36, 0, 1.6, 0.5))
    body_items.append(label_value_box("HdrTarget", "TARGET DATE COMPLETION",
                                      FH("TargetDate"), 6.04, 0, 1.45, 0.5))
    body_items.append(label_value_box("HdrPhase", "CURRENT PHASE",
                                      FH("Phase"), 7.57, 0, 1.3, 0.5))
    body_items.append(label_value_box("HdrDate", "DATE OF REPORT",
                                      FH("ReportDate"), 8.95, 0, 1.35, 0.5))

    # --- Row B: main status / description / value / gauge / health (0.62..2.07)
    # Deck style: big colored letter on white, not white-on-color.
    runs = (para(textrun("MAIN STATUS", size="6.5pt", bold=True, color=TEAL), "Center") +
            para(textrun(FH("MainStatus"), size="44pt", bold=True, color=FH("StatusColor")), "Center"))
    body_items.append(textbox("MainStatus", runs, 0, 0.62, 1.2, 1.45,
                              border=GRID, valign="Middle", grow=False))
    runs = (para(textrun("PROJECT DESCRIPTION", size="6.5pt", bold=True, color=TEAL)) +
            para(textrun(FH("Description"), size="8pt")))
    body_items.append(textbox("Descr", runs, 1.28, 0.62, 2.5, 1.45))
    runs = (para(textrun("BUSINESS VALUE", size="6.5pt", bold=True, color=TEAL)) +
            para(textrun(FH("BusinessValue"), size="8pt")))
    body_items.append(textbox("Value", runs, 3.86, 0.62, 2.5, 1.45))
    # Severity gauge + banded rating (same calculations as the interactive page).
    body_items.append(risk_gauge(6.44, 0.62, 1.6, 1.0))
    runs = (para(textrun("RISK RATING", size="6.5pt", bold=True, color=TEAL), "Center") +
            para(textrun('=First(Fields!RiskRating.Value, "DsGauge")', size="11pt", bold=True,
                         color='=First(Fields!RatingColor.Value, "DsGauge")'), "Center"))
    body_items.append(textbox("RiskRatingBox", runs, 6.44, 1.66, 1.6, 0.41,
                              border=GRID, valign="Middle", grow=False))
    body_items.append(tablix("HealthCheck", "DsHealth", [
        ("Health Check", F("KnowledgeArea"), 1.2, "Left"),
        ("Status", F("AreaStatus"), 0.8, "Center", None, AREA_COLOR, True),
    ], 8.12, 0.62, 2.18))

    # --- Row C: RAID (2.2 ..) ---------------------------------------------
    body_items.append(tablix("Raid", "DsRaid", [
        ("Type", F("RaidType"), 0.7, "Left"),
        ("Updates / Key Issues / Risks / Decisions / Dependencies",
         F("Description"), 4.6, "Left"),
        ("Owner", F("Owner"), 1.3, "Left"),
        ("Target Date", F("DueDate"), 1.0, "Center", "yyyy-MM-dd"),
        ("Score", F("Score"), 0.6, "Center"),
        ("Severity", F("Severity"), 0.9, "Center", None, SEV_COLOR, True),
        ("Status", F("RiskStatus"), 1.2, "Center"),
    ], 0, 2.2, 10.3, sort_field="Score", sort_desc=True))

    # --- Row D: key project areas -------------------------------------------
    body_items.append(tablix("Workstreams", "DsWorkstreams", [
        ("Key Project Areas", F("Deliverable"), 4.0, "Left"),
        ("Start Date", F("StartDate"), 1.4, "Center", "yyyy-MM-dd"),
        ("Target Implementation Date", F("TargetDate"), 1.8, "Center", "yyyy-MM-dd"),
        ("% Complete", F("PctComplete"), 1.3, "Center", "0.0%"),
        ("Current Status", F("WsStatus"), 1.8, "Center", None, WS_COLOR, True),
    ], 0, 4.05, 10.3, sort_field="StartDate"))

    # --- Row E: accomplishments + next steps ---------------------------------
    body_items.append(tablix("Accomplishments", "DsAccomplishments", [
        ("Accomplishments", F("Accomplishment"), 3.4, "Left"),
        ("Source", F("Source"), 0.8, "Center"),
        ("Completed Date", F("CompletedDate"), 1.0, "Center", "yyyy-MM-dd"),
    ], 0, 5.55, 5.07, sort_field="CompletedDate", sort_desc=True))
    body_items.append(tablix("NextSteps", "DsNextSteps", [
        ("Next Steps", F("NextStep"), 3.2, "Left"),
        ("Owner", F("Owner"), 1.1, "Left"),
        ("Target Date", F("TargetDate"), 1.0, "Center", "yyyy-MM-dd"),
    ], 5.23, 5.55, 5.07, sort_field="TargetDate"))

    # --- Row F: keys (multi-colored runs exactly like the deck) --------------
    key_runs = "".join([
        textrun("Key:    ", size="7pt", bold=True, color=TEAL),
        textrun("G – Green   ", size="7pt", bold=True, color=DECK_GREEN),
        textrun("Y – Yellow   ", size="7pt", bold=True, color=DECK_KEY_YELLOW),
        textrun("R – Off Track   ", size="7pt", bold=True, color=DECK_RED),
        textrun("C – Completed   ", size="7pt", bold=True, color="#000000"),
        textrun("NS - Not Started   ", size="7pt", bold=True, color="#000000"),
        textrun("H – Hold   ", size="7pt", bold=True, color=DECK_HOLD),
        textrun("CN – Cancelled        ", size="7pt", bold=True, color=DECK_CANCEL),
        textrun("Phase:  Initiating, Planning, Executing, Monitoring, Closing",
                size="7pt", color="#605E5C"),
    ])
    body_items.append(textbox("Keys", para(key_runs), 0, 7.05, 10.3, 0.25, bg=LIGHT))

    datasets = "".join(dataset_xml(n, d) for n, d in DATASETS.items())
    with open(LOGO, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode("ascii")

    rdl = f"""<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition"
        xmlns:rd="http://schemas.microsoft.com/SQLServer/reporting/reportdesigner">
  <AutoRefresh>0</AutoRefresh>
  <DataSources>
    <DataSource Name="TheragenModel">
      <ConnectionProperties>
        <DataProvider>PBISERVICE</DataProvider>
        <ConnectString>Data Source=powerbi://api.powerbi.com/v1.0/myorg/YOUR_WORKSPACE;Initial Catalog=Theragen Project Planner</ConnectString>
      </ConnectionProperties>
      <rd:SecurityType>None</rd:SecurityType>
    </DataSource>
  </DataSources>
  <DataSets>{datasets}</DataSets>
  <EmbeddedImages>
    <EmbeddedImage Name="TheragenLogo">
      <MIMEType>image/jpeg</MIMEType>
      <ImageData>{logo_b64}</ImageData>
    </EmbeddedImage>
  </EmbeddedImages>
  <ReportSections>
    <ReportSection>
      <Body>
        <ReportItems>{''.join(body_items)}</ReportItems>
        <Height>7.45in</Height>
        <Style />
      </Body>
      <Width>10.3in</Width>
      <Page>
        <PageHeight>8.5in</PageHeight>
        <PageWidth>11in</PageWidth>
        <LeftMargin>0.35in</LeftMargin>
        <RightMargin>0.35in</RightMargin>
        <TopMargin>0.35in</TopMargin>
        <BottomMargin>0.35in</BottomMargin>
        <Style />
      </Page>
    </ReportSection>
  </ReportSections>
  <ReportParameters>
    <ReportParameter Name="ProjectCode">
      <DataType>String</DataType>
      <DefaultValue>
        <DataSetReference>
          <DataSetName>DsProjectList</DataSetName>
          <ValueField>ProjectCode</ValueField>
        </DataSetReference>
      </DefaultValue>
      <Prompt>Project</Prompt>
      <ValidValues>
        <DataSetReference>
          <DataSetName>DsProjectList</DataSetName>
          <ValueField>ProjectCode</ValueField>
          <LabelField>ProjectName</LabelField>
        </DataSetReference>
      </ValidValues>
    </ReportParameter>
  </ReportParameters>
  <ReportParametersLayout>
    <GridLayoutDefinition>
      <NumberOfColumns>4</NumberOfColumns>
      <NumberOfRows>1</NumberOfRows>
      <CellDefinitions>
        <CellDefinition>
          <ColumnIndex>0</ColumnIndex>
          <RowIndex>0</RowIndex>
          <ParameterName>ProjectCode</ParameterName>
        </CellDefinition>
      </CellDefinitions>
    </GridLayoutDefinition>
  </ReportParametersLayout>
  <rd:ReportUnitType>Inch</rd:ReportUnitType>
  <rd:ReportID>{uuid.uuid5(uuid.NAMESPACE_URL, 'thg-bi/paginated/status-report')}</rd:ReportID>
</Report>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(rdl)
    print(os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    build()
