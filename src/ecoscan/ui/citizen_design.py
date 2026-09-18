"""Compact citizen workspace, separate from the secretariat dashboard."""


def render_citizen_design(st, image_uri):
    st.markdown('''<style>
    .stApp {background:#f4f7f6 !important; color:#192c29;}
    .stApp, .stApp button, .stApp input, .stApp textarea {
      font-family:Inter,"Segoe UI",Arial,sans-serif; letter-spacing:0 !important;
    }
    [data-testid="stMainBlockContainer"], .main .block-container {
      max-width:1080px !important; padding-top:1.1rem !important;
      box-shadow:none !important; border:0 !important; background:transparent !important;
    }
    .eco-citizen-header {display:flex; align-items:center; gap:16px;
      padding:16px 0 20px; border-bottom:1px solid #d4e2dd; margin-bottom:8px;}
    .eco-citizen-header img {width:64px; height:64px; object-fit:contain; flex-shrink:0;}
    .eco-citizen-header h1 {font-size:28px !important; line-height:1.15;
      margin:0 !important; padding:0 !important; color:#145c48; letter-spacing:0;}
    .eco-citizen-header p {font-size:15px; color:#496059; margin:6px 0 0;}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
      gap:4px !important; border-radius:0 !important; box-shadow:none !important;
      border-bottom:1px solid #cfddd7; overflow-x:auto; padding:4px 0 !important;
    }
    [data-testid="stTabs"] button[role="tab"] {min-height:48px; flex-shrink:0;
      padding:10px 14px !important; font-size:14px !important; min-width:74px !important;}
    [data-testid="stTabs"] button[aria-selected="true"] {color:#126049 !important;
      background:#e5f3ed !important; border-radius:6px 6px 0 0 !important;}
    [data-testid="stFileUploader"] {background:#fff; border:1px solid #c9dbd2;
      border-radius:8px; padding:12px;}
    button[kind="primary"] {background:#17684f !important; border-color:#17684f !important;}
    .ecoscan-section-title {font-size:20px !important; margin:14px 0 !important;}
    .ecoscan-camera-panel, .ecoscan-result, .ecoscan-evidence-panel {
      box-shadow:none !important; border-radius:6px !important;}
    .ecoscan-tech-summary, .ecoscan-evidence-panel {background:#fff !important; color:#233c34 !important;}
    @media(max-width:600px) {
      [data-testid="stMainBlockContainer"], .main .block-container {
        padding-left:16px !important; padding-right:16px !important; padding-bottom:32px !important;}
      .eco-citizen-header h1 {font-size:25px !important;}
      .eco-citizen-header img {width:48px; height:48px;}
      [data-testid="stTabs"] button[role="tab"] {padding:10px !important;}
      [data-testid="stButton"] button {min-height:44px;}
    }
    </style>''', unsafe_allow_html=True)
    st.markdown(f'''<header class="eco-citizen-header">
      <img src="{image_uri}" alt="Coleta de materiais recicláveis">
      <div><h1>EcoScan</h1><p>Seu próximo descarte começa aqui.</p></div>
    </header>''', unsafe_allow_html=True)
