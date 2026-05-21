"""
Custom CSS Styles for Wyckoff Trader App
Dark trading theme with modern design
"""

CUSTOM_CSS = """
<style>
    /* ===== GLOBAL STYLES ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    :root {
        --bg-primary: #0d1117;
        --bg-secondary: #161b22;
        --bg-tertiary: #21262d;
        --bg-card: #1c2128;
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
        --text-muted: #6e7681;
        --accent-green: #2ea043;
        --accent-green-light: #3fb950;
        --accent-red: #f85149;
        --accent-blue: #58a6ff;
        --accent-purple: #a371f7;
        --accent-yellow: #d29922;
        --accent-orange: #db6d28;
        --border-color: #30363d;
        --gradient-gold: linear-gradient(135deg, #f7931a 0%, #ffab40 100%);
        --gradient-green: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        --gradient-blue: linear-gradient(135deg, #1f6feb 0%, #58a6ff 100%);
    }
    
    .stApp {
        background: var(--bg-primary);
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
    }
    
    /* ===== HEADER STYLES ===== */
    .main-header {
        background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--gradient-gold);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #f7931a 0%, #ffcc00 50%, #f7931a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        color: var(--text-secondary);
        font-size: 1.1rem;
    }
    
    /* ===== SIDEBAR STYLES ===== */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }
    
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--text-primary);
    }
    
    /* ===== CARD STYLES ===== */
    .custom-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .custom-card:hover {
        border-color: var(--accent-blue);
        box-shadow: 0 4px 20px rgba(88, 166, 255, 0.1);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border-color);
    }
    
    .card-header h3 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* ===== CHAT STYLES ===== */
    .chat-container {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.5rem;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .user-message {
        background: var(--gradient-blue);
        color: white;
        padding: 1rem 1.25rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.75rem 0;
        margin-left: 20%;
        font-size: 0.95rem;
        box-shadow: 0 2px 8px rgba(88, 166, 255, 0.2);
    }
    
    .bot-message {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        padding: 1rem 1.25rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.75rem 0;
        margin-right: 20%;
        font-size: 0.95rem;
    }
    
    .bot-message::before {
        content: '🤖 Wyckoff Bot';
        display: block;
        font-size: 0.75rem;
        color: var(--accent-green-light);
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    /* ===== METRIC CARDS ===== */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    
    .metric-value.positive {
        color: var(--accent-green-light);
    }
    
    .metric-value.negative {
        color: var(--accent-red);
    }
    
    .metric-value.neutral {
        color: var(--accent-blue);
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* ===== EVENT BADGES ===== */
    .event-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .event-sc { background: #1f3a5f; color: #58a6ff; border: 1px solid #58a6ff; }
    .event-bc { background: #3d1f5f; color: #a371f7; border: 1px solid #a371f7; }
    .event-sp { background: #1f4d2e; color: #3fb950; border: 1px solid #3fb950; }
    .event-ut { background: #5f1f1f; color: #f85149; border: 1px solid #f85149; }
    .event-sos { background: #2d4a1f; color: #7ee787; border: 1px solid #7ee787; }
    .event-sow { background: #5f3a1f; color: #db6d28; border: 1px solid #db6d28; }
    
    /* ===== PHASE INDICATOR ===== */
    .phase-indicator {
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-card) 100%);
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--accent-blue);
        border-radius: 0 12px 12px 0;
        padding: 1.25rem;
        margin: 1rem 0;
    }
    
    .phase-indicator.accumulation {
        border-left-color: var(--accent-green-light);
    }
    
    .phase-indicator.distribution {
        border-left-color: var(--accent-red);
    }
    
    .phase-indicator h4 {
        margin: 0 0 0.5rem 0;
        color: var(--text-primary);
        font-weight: 600;
    }
    
    .phase-indicator p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 0.9rem;
    }
    
    /* ===== CONTEXT PANEL ===== */
    .context-panel {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .context-item {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    
    .context-item .similarity {
        display: inline-block;
        background: var(--accent-green);
        color: white;
        padding: 0.15rem 0.5rem;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* ===== BUTTONS ===== */
    .stButton > button {
        background: var(--gradient-blue);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(88, 166, 255, 0.3);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Primary action button */
    .primary-btn > button {
        background: var(--gradient-gold) !important;
        font-size: 1rem;
        padding: 0.75rem 2rem;
    }
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--bg-secondary);
        border-radius: 12px;
        padding: 0.25rem;
        border: 1px solid var(--border-color);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--text-secondary);
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }
    
    /* ===== INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--accent-blue);
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2);
    }
    
    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
    }
    
    /* ===== DIVIDER ===== */
    hr {
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 1.5rem 0;
    }
    
    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }
    
    /* ===== QUICK ACTION BUTTONS ===== */
    .quick-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .quick-btn {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        color: var(--text-secondary);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .quick-btn:hover {
        background: var(--bg-card);
        border-color: var(--accent-blue);
        color: var(--text-primary);
    }
    
    /* ===== TRADE SIGNALS ===== */
    .signal-buy {
        background: linear-gradient(135deg, #1f4d2e 0%, #2d5a3c 100%);
        border: 1px solid var(--accent-green);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--accent-green-light);
        font-weight: 600;
    }
    
    .signal-sell {
        background: linear-gradient(135deg, #4d1f1f 0%, #5a2d2d 100%);
        border: 1px solid var(--accent-red);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--accent-red);
        font-weight: 600;
    }
    
    .signal-neutral {
        background: linear-gradient(135deg, #1f3a5f 0%, #2d4a6f 100%);
        border: 1px solid var(--accent-blue);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--accent-blue);
        font-weight: 600;
    }
    
    /* ===== LOADING ANIMATION ===== */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .loading {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    /* ===== TRADE TABLE ===== */
    .trade-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }
    
    .trade-table th {
        background: var(--bg-tertiary);
        color: var(--text-secondary);
        padding: 0.75rem;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
    }
    
    .trade-table td {
        padding: 0.75rem;
        border-bottom: 1px solid var(--border-color);
        color: var(--text-primary);
    }
    
    .trade-table tr:hover {
        background: var(--bg-tertiary);
    }
    
    /* ===== FOOTER ===== */
    .footer {
        text-align: center;
        padding: 2rem;
        color: var(--text-muted);
        font-size: 0.85rem;
        border-top: 1px solid var(--border-color);
        margin-top: 2rem;
    }
</style>
"""

# Component HTML templates
HEADER_HTML = """
<div class="main-header">
    <h1>📈 Wyckoff Trader</h1>
    <p>AI-Powered Trading Analysis using Richard Wyckoff's Methodology</p>
</div>
"""

def metric_card(value, label, trend="neutral"):
    """Generate metric card HTML."""
    return f"""
    <div class="metric-card">
        <div class="metric-value {trend}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """

def event_badge(event_type, count):
    """Generate event badge HTML."""
    names = {
        'SC': 'Selling Climax',
        'BC': 'Buying Climax', 
        'SP': 'Spring',
        'UT': 'Upthrust',
        'SOS': 'Sign of Strength',
        'SOW': 'Sign of Weakness'
    }
    return f'<span class="event-badge event-{event_type.lower()}">{names.get(event_type, event_type)}: {count}</span>'

def phase_indicator(phase_text, phase_type="neutral"):
    """Generate phase indicator HTML."""
    return f"""
    <div class="phase-indicator {phase_type}">
        <h4>📊 Current Market Phase</h4>
        <p>{phase_text}</p>
    </div>
    """

def chat_message(message, is_user=False):
    """Generate chat message HTML."""
    css_class = "user-message" if is_user else "bot-message"
    return f'<div class="{css_class}">{message}</div>'

def context_item(question, answer, similarity):
    """Generate context item HTML."""
    return f"""
    <div class="context-item">
        <span class="similarity">{similarity:.0%} match</span>
        <div><strong>Q:</strong> {question[:100]}...</div>
        <div><strong>A:</strong> {answer[:150]}...</div>
    </div>
    """
