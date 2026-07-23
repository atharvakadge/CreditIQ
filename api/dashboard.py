import streamlit as st
import requests
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

st.set_page_config(page_title="CreditIQ", layout="wide", initial_sidebar_state="expanded")

API_URL = "http://127.0.0.1:8000"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { background-color: #FAFAFA; }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E8E8E8;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label {
        font-family: 'Inter', sans-serif;
        color: #333333;
    }
    h1, h2, h3, p, span, label, div { font-family: 'Inter', sans-serif !important; }
    .main-header {
        font-size: 1.75rem; font-weight: 700; color: #111111;
        letter-spacing: -0.5px; margin-bottom: 0;
    }
    .sub-header {
        font-size: 0.9rem; color: #888888; font-weight: 400; margin-top: -8px;
    }
    .result-card {
        background: #FFFFFF; border: 1px solid #E8E8E8;
        border-radius: 12px; padding: 28px; margin: 8px 0;
    }
    .approved-card { border-left: 4px solid #22C55E; }
    .rejected-card { border-left: 4px solid #EF4444; }
    .decision-label {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; color: #888888; margin-bottom: 4px;
    }
    .decision-approved { font-size: 1.8rem; font-weight: 700; color: #22C55E; }
    .decision-rejected { font-size: 1.8rem; font-weight: 700; color: #EF4444; }
    .metric-card {
        background: #FFFFFF; border: 1px solid #E8E8E8;
        border-radius: 12px; padding: 24px; text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #111111; }
    .metric-label {
        font-size: 0.75rem; font-weight: 500; color: #999999;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .section-title {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; color: #AAAAAA;
        margin-bottom: 12px; margin-top: 32px;
    }
    .impact-row {
        display: flex; justify-content: space-between;
        padding: 14px 0; border-bottom: 1px solid #F0F0F0; font-size: 0.85rem;
    }
    .impact-label { color: #666666; }
    .impact-value { font-weight: 600; color: #111111; }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #111111; color: #FFFFFF; border: none;
        border-radius: 8px; padding: 10px 20px; font-weight: 600;
        font-size: 0.85rem; width: 100%; letter-spacing: 0.5px;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #333333;
    }
    .sidebar-title {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; color: #AAAAAA;
        margin-bottom: 16px; margin-top: 8px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


def generate_pdf_report(applicant_data, result):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=22, fontName='Helvetica-Bold',
        spaceAfter=6, textColor=HexColor('#111111')
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica',
        textColor=HexColor('#888888'), spaceAfter=20
    )
    section_style = ParagraphStyle(
        'SectionHead', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        textColor=HexColor('#AAAAAA'), spaceAfter=10, spaceBefore=24
    )
    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica',
        textColor=HexColor('#333333'), leading=16
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=HexColor('#888888')
    )
    value_style = ParagraphStyle(
        'Value', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        textColor=HexColor('#111111')
    )

    story = []

    story.append(Paragraph("CreditIQ", title_style))
    story.append(Paragraph(
        f"Loan Assessment Report &bull; {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#E8E8E8'), spaceAfter=10))

    is_approved = result['prediction'] == 'APPROVED'
    dec_color = '#22C55E' if is_approved else '#EF4444'
    dec_style = ParagraphStyle(
        'Decision', parent=styles['Normal'],
        fontSize=20, fontName='Helvetica-Bold',
        textColor=HexColor(dec_color), alignment=TA_CENTER
    )
    center_style = ParagraphStyle(
        'CenterInfo', parent=body_style, alignment=TA_CENTER, spaceAfter=6, spaceBefore=6
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph(result['prediction'], dec_style))
    story.append(Paragraph(
        f"Default Probability: {result['default_probability']*100:.1f}%"
        f" &bull; Confidence: {result['confidence']}%",
        center_style
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#E8E8E8'), spaceAfter=4))

    # Applicant summary using Paragraph objects for text wrapping
    story.append(Paragraph("APPLICANT SUMMARY", section_style))

    edu_text = applicant_data.get('NAME_EDUCATION_TYPE', 'N/A')
    family_text = applicant_data.get('NAME_FAMILY_STATUS', 'N/A')
    age_val = abs(applicant_data.get('DAYS_BIRTH', 0)) // 365
    emp_val = abs(applicant_data.get('DAYS_EMPLOYED', 0)) // 365

    rows = [
        [Paragraph('Annual Income', label_style),
         Paragraph(f"Rs. {applicant_data['AMT_INCOME_TOTAL']:,.0f}", value_style),
         Paragraph('Loan Amount', label_style),
         Paragraph(f"Rs. {applicant_data['AMT_CREDIT']:,.0f}", value_style)],
        [Paragraph('Monthly EMI', label_style),
         Paragraph(f"Rs. {applicant_data['AMT_ANNUITY']:,.0f}", value_style),
         Paragraph('Goods Price', label_style),
         Paragraph(f"Rs. {applicant_data['AMT_GOODS_PRICE']:,.0f}", value_style)],
        [Paragraph('Contract Type', label_style),
         Paragraph(applicant_data['NAME_CONTRACT_TYPE'], value_style),
         Paragraph('Gender', label_style),
         Paragraph(applicant_data['CODE_GENDER'], value_style)],
        [Paragraph('Education', label_style),
         Paragraph(edu_text, value_style),
         Paragraph('Family Status', label_style),
         Paragraph(family_text, value_style)],
        [Paragraph('Age', label_style),
         Paragraph(f"{age_val} years", value_style),
         Paragraph('Employment', label_style),
         Paragraph(f"{emp_val} years", value_style)],
        [Paragraph('Credit Score 1', label_style),
         Paragraph(f"{applicant_data['EXT_SOURCE_1']:.2f}", value_style),
         Paragraph('Credit Score 2', label_style),
         Paragraph(f"{applicant_data['EXT_SOURCE_2']:.2f}", value_style)],
        [Paragraph('Credit Score 3', label_style),
         Paragraph(f"{applicant_data['EXT_SOURCE_3']:.2f}", value_style),
         Paragraph('Active Loans', label_style),
         Paragraph(str(applicant_data['PREV_ACTIVE_LOANS']), value_style)],
    ]

    page_width = A4[0] - 4*cm
    col_w = page_width / 4
    app_table = Table(rows, colWidths=[col_w]*4)
    app_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor('#F0F0F0')),
    ]))
    story.append(app_table)

    # Risk factors
    story.append(Paragraph("RISK ANALYSIS", section_style))

    for factor in result['top_risk_factors']:
        is_risk = "increases" in factor['direction']
        color = HexColor('#EF4444') if is_risk else HexColor('#22C55E')
        sign = "+" if is_risk else "-"
        name_text = factor['feature'].replace('_', ' ').title()

        name_para = Paragraph(name_text, ParagraphStyle(
            'FName', parent=body_style, fontSize=10
        ))
        val_para = Paragraph(f"{sign} {abs(factor['impact']):.4f}", ParagraphStyle(
            'FVal', parent=body_style, fontSize=10,
            textColor=color, fontName='Helvetica-Bold', alignment=TA_RIGHT
        ))
        row_table = Table([[name_para, val_para]], colWidths=[page_width*0.65, page_width*0.35])
        row_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#F0F0F0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(row_table)

    # Financial impact
    story.append(Paragraph("FINANCIAL IMPACT", section_style))

    avg_default_cost = 500000
    expected_loss = result['default_probability'] * avg_default_cost

    fin_rows = [
        [Paragraph('Expected Loss (this applicant)', label_style),
         Paragraph(f"Rs. {expected_loss:,.0f}", value_style)],
        [Paragraph('Average Default Cost', label_style),
         Paragraph(f"Rs. {avg_default_cost:,.0f}", value_style)],
        [Paragraph('Default Probability', label_style),
         Paragraph(f"{result['default_probability']*100:.1f}%", value_style)],
        [Paragraph('Model AUC-ROC', label_style),
         Paragraph('0.7664', value_style)],
        [Paragraph('Model Recall (Defaulters)', label_style),
         Paragraph('68%', value_style)],
    ]
    fin_table = Table(fin_rows, colWidths=[page_width*0.65, page_width*0.35])
    fin_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor('#F0F0F0')),
    ]))
    story.append(fin_table)

    # Recommendation
    story.append(Paragraph("RECOMMENDATION", section_style))

    risk_features = [f['feature'].replace('_', ' ').lower()
                     for f in result['top_risk_factors'][:3]
                     if 'increases' in f['direction']]

    if is_approved:
        rec = (
            f"Based on the model assessment, this applicant presents an acceptable credit risk "
            f"with a {result['default_probability']*100:.1f}% probability of default. "
            f"The applicant's credit scores and financial profile indicate adequate repayment capacity. "
            f"Recommendation: <b>Proceed with loan approval</b> subject to standard verification."
        )
    else:
        concerns = ', '.join(risk_features) if risk_features else 'multiple elevated risk indicators'
        rec = (
            f"Based on the model assessment, this applicant presents an elevated credit risk "
            f"with a {result['default_probability']*100:.1f}% probability of default. "
            f"Key concerns: {concerns}. "
            f"Recommendation: <b>Decline or request additional collateral</b> before proceeding."
        )
    story.append(Paragraph(rec, body_style))

    # Disclaimer
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#E0E0E0'), spaceAfter=8))
    disc_style = ParagraphStyle(
        'Disc', parent=body_style, fontSize=7.5, textColor=HexColor('#AAAAAA'), leading=11
    )
    story.append(Paragraph(
        "This report is generated by CreditIQ, an AI-powered credit risk assessment tool. "
        "Predictions are based on a LightGBM model trained on historical loan data and should be "
        "used as a decision-support tool, not as the sole basis for lending decisions. "
        "Model AUC-ROC: 0.7664.",
        disc_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─── Header ─────────────────────────────────────────────────
st.markdown('<p class="main-header">CreditIQ</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-powered credit risk assessment with explainability</p>', unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sidebar-title">Loan Details</p>', unsafe_allow_html=True)
    income = st.number_input("Annual Income", min_value=25000, max_value=10000000, value=200000, step=10000)
    credit = st.number_input("Loan Amount", min_value=45000, max_value=4000000, value=500000, step=10000)
    annuity = st.number_input("Monthly EMI", min_value=1000, max_value=300000, value=25000, step=1000)
    goods_price = st.number_input("Goods Price", min_value=40000, max_value=4000000, value=450000, step=10000)
    contract = st.selectbox("Contract Type", ["Cash loans", "Revolving loans"])

    st.markdown('<p class="sidebar-title">Applicant Profile</p>', unsafe_allow_html=True)
    gender = st.selectbox("Gender", ["M", "F"])
    own_car = st.selectbox("Owns Car", ["N", "Y"])
    own_realty = st.selectbox("Owns Property", ["Y", "N"])
    income_type = st.selectbox("Income Type", ["Working", "Commercial associate", "Pensioner", "State servant"])
    education = st.selectbox("Education", [
        "Secondary / secondary special", "Higher education",
        "Incomplete higher", "Lower secondary", "Academic degree"
    ])
    family_status = st.selectbox("Family Status", [
        "Married", "Single / not married", "Civil marriage", "Separated", "Widow"
    ])
    housing = st.selectbox("Housing", [
        "House / apartment", "With parents", "Rented apartment",
        "Municipal apartment", "Office apartment"
    ])
    age = st.slider("Age", 18, 70, 30)
    employment_years = st.slider("Years Employed", 0, 40, 5)

    st.markdown('<p class="sidebar-title">Credit History</p>', unsafe_allow_html=True)
    ext1 = st.slider("Credit Score 1", 0.0, 1.0, 0.50, 0.01)
    ext2 = st.slider("Credit Score 2", 0.0, 1.0, 0.50, 0.01)
    ext3 = st.slider("Credit Score 3", 0.0, 1.0, 0.50, 0.01)
    prev_loans = st.number_input("Previous Loans", 0, 50, 3)
    active_loans = st.number_input("Active Loans", 0, 20, 1)
    total_debt = st.number_input("Outstanding Debt", 0, 10000000, 100000, step=10000)

    st.markdown("---")
    predict_btn = st.button("Assess Risk", use_container_width=True, type="primary")

# ─── Main ───────────────────────────────────────────────────
if predict_btn:
    payload = {
        "AMT_INCOME_TOTAL": income,
        "AMT_CREDIT": credit,
        "AMT_ANNUITY": annuity,
        "AMT_GOODS_PRICE": goods_price,
        "NAME_CONTRACT_TYPE": contract,
        "CODE_GENDER": gender,
        "FLAG_OWN_CAR": own_car,
        "FLAG_OWN_REALTY": own_realty,
        "NAME_INCOME_TYPE": income_type,
        "NAME_EDUCATION_TYPE": education,
        "NAME_FAMILY_STATUS": family_status,
        "NAME_HOUSING_TYPE": housing,
        "DAYS_BIRTH": -age * 365,
        "DAYS_EMPLOYED": -employment_years * 365,
        "EXT_SOURCE_1": ext1,
        "EXT_SOURCE_2": ext2,
        "EXT_SOURCE_3": ext3,
        "PREV_LOAN_COUNT": prev_loans,
        "PREV_ACTIVE_LOANS": active_loans,
        "PREV_TOTAL_DEBT": total_debt
    }

    try:
        response = requests.post(f"{API_URL}/predict", json=payload)
        result = response.json()

        if response.status_code == 200:
            is_approved = result['prediction'] == 'APPROVED'

            col1, col2, col3 = st.columns([2, 1.5, 1.5])
            with col1:
                card_class = "approved-card" if is_approved else "rejected-card"
                dec_class = "decision-approved" if is_approved else "decision-rejected"
                st.markdown(f'''
                <div class="result-card {card_class}">
                    <p class="decision-label">Decision</p>
                    <p class="{dec_class}">{result["prediction"]}</p>
                </div>
                ''', unsafe_allow_html=True)
            with col2:
                st.markdown(f'''
                <div class="metric-card">
                    <p class="metric-label">Default Probability</p>
                    <p class="metric-value">{result["default_probability"]*100:.1f}%</p>
                </div>
                ''', unsafe_allow_html=True)
            with col3:
                st.markdown(f'''
                <div class="metric-card">
                    <p class="metric-label">Confidence</p>
                    <p class="metric-value">{result["confidence"]}%</p>
                </div>
                ''', unsafe_allow_html=True)

            col_left, col_right = st.columns([3, 2])

            with col_left:
                st.markdown('<p class="section-title">Risk Factors</p>', unsafe_allow_html=True)
                for factor in result['top_risk_factors']:
                    is_risk = "increases" in factor['direction']
                    name = factor['feature'].replace('_', ' ').title()
                    impact = abs(factor['impact'])
                    sign = "+" if is_risk else "-"

                    if is_risk:
                        color = "#EF4444"
                        dot = "🔴"
                    else:
                        color = "#22C55E"
                        dot = "🟢"

                    st.markdown(
                        f"{dot} &nbsp; **{name}** &mdash; "
                        f"<span style='color:{color}; font-weight:600;'>"
                        f"{sign}{impact:.4f}</span>",
                        unsafe_allow_html=True
                    )

            with col_right:
                st.markdown('<p class="section-title">Financial Impact</p>', unsafe_allow_html=True)
                avg_default_cost = 500000
                expected_loss = result['default_probability'] * avg_default_cost
                st.markdown(f'''
                <div class="result-card" style="padding: 8px 20px;">
                    <div class="impact-row">
                        <span class="impact-label">Expected Loss</span>
                        <span class="impact-value">&#8377;{expected_loss:,.0f}</span>
                    </div>
                    <div class="impact-row">
                        <span class="impact-label">Avg Default Cost</span>
                        <span class="impact-value">&#8377;5,00,000</span>
                    </div>
                    <div class="impact-row">
                        <span class="impact-label">Model AUC-ROC</span>
                        <span class="impact-value">0.7664</span>
                    </div>
                    <div class="impact-row" style="border-bottom:none;">
                        <span class="impact-label">Defaulter Recall</span>
                        <span class="impact-value">68%</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

            st.markdown('<p class="section-title">Report</p>', unsafe_allow_html=True)
            pdf_buffer = generate_pdf_report(payload, result)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            st.download_button(
                label="Download Assessment Report (PDF)",
                data=pdf_buffer,
                file_name=f"CreditIQ_Report_{timestamp}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        else:
            st.error(f"Error: {result.get('detail', 'Unknown error')}")

    except requests.exceptions.ConnectionError:
        st.markdown('''
        <div class="result-card" style="border-left: 4px solid #F59E0B;">
            <p style="color: #92400E; font-weight: 600; margin: 0;">Cannot connect to API</p>
            <p style="color: #666; font-size: 0.85rem; margin: 4px 0 0 0;">
                Make sure FastAPI is running: <code>uvicorn app.app:app --reload</code>
            </p>
        </div>
        ''', unsafe_allow_html=True)
else:
    st.markdown('''
    <div style="text-align:center; padding: 80px 20px;">
        <p style="font-size: 3rem; margin-bottom: 8px; opacity: 0.15;">&#x2B21;</p>
        <p style="font-size: 1rem; color: #AAAAAA; font-weight: 500;">
            Enter applicant details in the sidebar and click Assess Risk
        </p>
    </div>
    ''', unsafe_allow_html=True)