"""
================================================================================
WYCKOFF TRADER - AI-Powered Trading Analysis
================================================================================
Streamlit app combining:
- Part I: Wyckoff ChatBot (RAG + Fine-tuned LLaMA)
- Part II: Stock Analysis with Wyckoff pattern detection

Run: streamlit run app.py
================================================================================
"""

import streamlit as st
import time
from datetime import datetime

# Import custom modules
from styles import CUSTOM_CSS, HEADER_HTML, metric_card, event_badge, phase_indicator, chat_message, context_item
from stock_analysis import StockAnalyzer, STOCK_LIST

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Wyckoff Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = None

if 'analyzer' not in st.session_state:
    st.session_state.analyzer = StockAnalyzer()

if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None


# ============================================
# LAZY LOADING
# ============================================

@st.cache_resource(show_spinner=False)
def load_chatbot():
    """Load chatbot with caching."""
    from chatbot import WyckoffChatbot
    bot = WyckoffChatbot()
    bot.initialize()
    return bot


# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h1 style="font-size: 1.8rem; background: linear-gradient(135deg, #f7931a, #ffcc00); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            📈 Wyckoff Trader
        </h1>
        <p style="color: #8b949e; font-size: 0.9rem;">AI-Powered Trading Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigate",
        ["💬 AI ChatBot", "📊 Stock Analysis", "📚 Wyckoff Guide"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Settings
    with st.expander("⚙️ Settings", expanded=False):
        use_rag = st.toggle("Use RAG Retrieval", value=True, help="Enable context retrieval for better answers")
        top_k = st.slider("Context Items", 1, 5, 3, help="Number of similar Q&As to retrieve")
        st.session_state.use_rag = use_rag
        st.session_state.top_k = top_k
    
    st.markdown("---")
    
    # Info
    st.markdown("""
    <div style="padding: 1rem; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">
        <h4 style="color: #e6edf3; margin-bottom: 0.5rem;">About</h4>
        <p style="color: #8b949e; font-size: 0.85rem; margin: 0;">
            Built with Fine-tuned LLaMA 2 + RAG for Wyckoff methodology analysis.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ============================================
# PAGE 1: AI CHATBOT
# ============================================

def chatbot_page():
    # Header
    st.markdown(HEADER_HTML, unsafe_allow_html=True)
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <span style="font-size: 1.5rem;">🤖</span>
                <h3>Wyckoff Trading Assistant</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            if st.session_state.chat_history:
                for msg in st.session_state.chat_history:
                    if msg['role'] == 'user':
                        st.markdown(f"""
                        <div class="user-message">{msg['content']}</div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="bot-message">{msg['content']}</div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="text-align: center; padding: 3rem; color: #8b949e;">
                    <p style="font-size: 1.2rem;">👋 Welcome to Wyckoff Trader!</p>
                    <p>Ask me anything about Richard Wyckoff's trading methodology.</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Input area
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_input, col_btn = st.columns([5, 1])
        
        with col_input:
            user_input = st.text_input(
                "Ask a question",
                placeholder="e.g., What is a Spring in Wyckoff methodology?",
                label_visibility="collapsed",
                key="chat_input"
            )
        
        with col_btn:
            send_btn = st.button("Send 📤", use_container_width=True, type="primary")
        
        # Process input
        if (send_btn or user_input) and user_input:
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input
            })
            
            # Get response
            with st.spinner("🔍 Analyzing..."):
                try:
                    if st.session_state.chatbot is None:
                        st.session_state.chatbot = load_chatbot()
                    
                    use_rag = st.session_state.get('use_rag', True)
                    top_k = st.session_state.get('top_k', 3)
                    
                    answer, context = st.session_state.chatbot.ask(
                        user_input, 
                        use_rag=use_rag, 
                        top_k=top_k
                    )
                    
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': answer,
                        'context': context
                    })
                    
                    st.session_state.last_context = context
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            
            st.rerun()
        
        # Clear chat button
        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat", type="secondary"):
                st.session_state.chat_history = []
                st.rerun()
    
    with col2:
        # Quick questions
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <span style="font-size: 1.2rem;">💡</span>
                <h3>Quick Questions</h3>
            </div>
        """, unsafe_allow_html=True)
        
        quick_questions = [
            "What is a Spring?",
            "Wyckoff's three laws?",
            "When to enter after SC?",
            "Accumulation vs Distribution?",
            "What is Phase C?",
            "Volume patterns in markup?"
        ]
        
        for q in quick_questions:
            if st.button(q, key=f"quick_{q}", use_container_width=True):
                st.session_state.chat_history.append({'role': 'user', 'content': q})
                
                if st.session_state.chatbot is None:
                    st.session_state.chatbot = load_chatbot()
                
                answer, context = st.session_state.chatbot.ask(q, use_rag=True)
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': answer,
                    'context': context
                })
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Retrieved context
        if st.session_state.chat_history and st.session_state.get('last_context'):
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <span style="font-size: 1.2rem;">📚</span>
                    <h3>Retrieved Context</h3>
                </div>
            """, unsafe_allow_html=True)
            
            for ctx in st.session_state.last_context:
                st.markdown(context_item(
                    ctx['question'], 
                    ctx['answer'], 
                    ctx['similarity']
                ), unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)


# ============================================
# PAGE 2: STOCK ANALYSIS
# ============================================

def stock_analysis_page():
    st.markdown("""
    <div class="main-header">
        <h1>📊 Stock Analysis</h1>
        <p>Wyckoff Pattern Detection & Backtesting</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stock selection
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        # Category selection
        category = st.selectbox(
            "Category",
            list(STOCK_LIST.keys()),
            label_visibility="collapsed"
        )
        
        ticker = st.selectbox(
            "Select Stock",
            STOCK_LIST[category],
            key="stock_select"
        )
    
    with col2:
        custom = st.text_input("Custom Ticker", placeholder="NVDA")
        if custom:
            ticker = custom.upper()
    
    with col3:
        period = st.selectbox(
            "Period",
            ["3mo", "6mo", "1y", "2y"],
            index=2
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    st.markdown("---")
    
    # Run analysis
    if analyze_btn:
        with st.spinner(f"📊 Analyzing {ticker}..."):
            try:
                result = st.session_state.analyzer.analyze(ticker, period)
                st.session_state.current_analysis = result
            except Exception as e:
                st.error(f"Error analyzing {ticker}: {str(e)}")
                return
    
    # Display results
    if st.session_state.current_analysis:
        result = st.session_state.current_analysis
        
        # Stock info header
        info = result.get('info', {})
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
            <h2 style="margin: 0; color: #e6edf3;">{info.get('name', result['ticker'])}</h2>
            <span style="color: #8b949e;">({result['ticker']})</span>
            <span style="background: #21262d; padding: 0.25rem 0.75rem; border-radius: 20px; 
                font-size: 0.85rem; color: #8b949e;">{info.get('sector', 'N/A')}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics row
        phase = result['phase']
        backtest = result['backtest']
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            trend = "positive" if phase['price_change'] > 0 else "negative"
            st.markdown(metric_card(
                f"{phase['price_change']:.1f}%",
                "Price Change",
                trend
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(metric_card(
                f"{backtest['total_trades']}",
                "Total Trades",
                "neutral"
            ), unsafe_allow_html=True)
        
        with col3:
            trend = "positive" if backtest['win_rate'] > 50 else "negative"
            st.markdown(metric_card(
                f"{backtest['win_rate']:.0f}%",
                "Win Rate",
                trend
            ), unsafe_allow_html=True)
        
        with col4:
            trend = "positive" if backtest['total_return'] > 0 else "negative"
            st.markdown(metric_card(
                f"{backtest['total_return']:.1f}%",
                "Total Return",
                trend
            ), unsafe_allow_html=True)
        
        with col5:
            events_count = sum(phase['events_detected'].values()) if phase['events_detected'] else 0
            st.markdown(metric_card(
                str(events_count),
                "Events Detected",
                "neutral"
            ), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Phase indicator
        phase_type = "accumulation" if phase['bias'] == "bullish" else "distribution" if phase['bias'] == "bearish" else ""
        st.markdown(phase_indicator(
            f"<strong>{phase['phase_name']}</strong><br>{phase['description']}",
            phase_type
        ), unsafe_allow_html=True)
        
        # Main chart
        st.markdown("<br>", unsafe_allow_html=True)
        st.plotly_chart(result['chart'], use_container_width=True)
        
        # Two columns for events and trades
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <span style="font-size: 1.2rem;">🎯</span>
                    <h3>Detected Wyckoff Events</h3>
                </div>
            """, unsafe_allow_html=True)
            
            if phase['events_detected']:
                event_html = ""
                for event, count in phase['events_detected'].items():
                    event_html += event_badge(event, count)
                st.markdown(event_html, unsafe_allow_html=True)
            else:
                st.info("No significant Wyckoff events detected in this period.")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <span style="font-size: 1.2rem;">📋</span>
                    <h3>Recent Trades (Backtest)</h3>
                </div>
            """, unsafe_allow_html=True)
            
            trades = backtest['trades'][-10:]  # Last 10 trades
            
            if trades:
                for trade in trades:
                    if trade['type'] == 'entry':
                        st.markdown(f"""
                        <div class="signal-buy" style="margin-bottom: 0.5rem;">
                            🟢 Entry @ ${trade['price']:.2f} ({trade['signal']})
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        color_class = "signal-buy" if trade['pnl'] > 0 else "signal-sell"
                        icon = "🟢" if trade['pnl'] > 0 else "🔴"
                        st.markdown(f"""
                        <div class="{color_class}" style="margin-bottom: 0.5rem;">
                            {icon} Exit @ ${trade['price']:.2f} ({trade['signal']}) | PnL: {trade['pnl']:.1f}%
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No trades triggered in the backtest period.")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Backtest chart
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📈 Backtest Visualization", expanded=False):
            st.plotly_chart(result['backtest_chart'], use_container_width=True)


# ============================================
# PAGE 3: WYCKOFF GUIDE
# ============================================

def guide_page():
    st.markdown("""
    <div class="main-header">
        <h1>📚 Wyckoff Methodology Guide</h1>
        <p>Quick Reference for Wyckoff Trading Concepts</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <span style="font-size: 1.2rem;">📖</span>
                <h3>The Three Laws</h3>
            </div>
            <div style="padding: 0.5rem 0;">
                <h4 style="color: #58a6ff; margin-bottom: 0.5rem;">1. Supply and Demand</h4>
                <p style="color: #8b949e; font-size: 0.9rem; margin-bottom: 1rem;">
                    Price moves based on the balance between buyers and sellers. When demand exceeds supply, prices rise.
                </p>
                
                <h4 style="color: #3fb950; margin-bottom: 0.5rem;">2. Cause and Effect</h4>
                <p style="color: #8b949e; font-size: 0.9rem; margin-bottom: 1rem;">
                    The size of the trading range (cause) determines the extent of the subsequent move (effect).
                </p>
                
                <h4 style="color: #a371f7; margin-bottom: 0.5rem;">3. Effort vs Result</h4>
                <p style="color: #8b949e; font-size: 0.9rem;">
                    Volume (effort) should confirm price movement (result). Divergences signal potential reversals.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <span style="font-size: 1.2rem;">🎯</span>
                <h3>Key Events</h3>
            </div>
        """, unsafe_allow_html=True)
        
        events_info = {
            'SC': ('Selling Climax', 'Panic selling exhausts supply, marking potential bottom'),
            'BC': ('Buying Climax', 'Euphoric buying exhausts demand, marking potential top'),
            'SP': ('Spring', 'False breakdown below support that traps sellers'),
            'UT': ('Upthrust', 'False breakout above resistance that traps buyers'),
            'SOS': ('Sign of Strength', 'Rally that confirms accumulation'),
            'SOW': ('Sign of Weakness', 'Decline that confirms distribution'),
        }
        
        for code, (name, desc) in events_info.items():
            st.markdown(f"""
            <div style="margin-bottom: 0.75rem;">
                {event_badge(code, '')}
                <span style="color: #8b949e; font-size: 0.85rem;"> - {desc}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <span style="font-size: 1.2rem;">🔄</span>
                <h3>The Five Phases</h3>
            </div>
        """, unsafe_allow_html=True)
        
        phases = [
            ("Phase A", "Stopping Action", "The previous trend comes to a halt with climactic volume"),
            ("Phase B", "Building Cause", "Institutions accumulate/distribute while testing supply/demand"),
            ("Phase C", "Test", "Final test via Spring (accumulation) or Upthrust (distribution)"),
            ("Phase D", "Trend in Range", "Price shows clear direction with successive LPS or LPSY"),
            ("Phase E", "Trend Out of Range", "Price leaves the range and trends in the new direction"),
        ]
        
        for phase, name, desc in phases:
            st.markdown(f"""
            <div style="background: #21262d; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;
                border-left: 3px solid #58a6ff;">
                <strong style="color: #58a6ff;">{phase}</strong> - <span style="color: #e6edf3;">{name}</span>
                <p style="color: #8b949e; font-size: 0.85rem; margin: 0.25rem 0 0 0;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <span style="font-size: 1.2rem;">💡</span>
                <h3>Trading Tips</h3>
            </div>
            <ul style="color: #8b949e; font-size: 0.9rem;">
                <li style="margin-bottom: 0.5rem;">Wait for <strong style="color: #3fb950;">Springs</strong> at support for low-risk entries</li>
                <li style="margin-bottom: 0.5rem;">Volume should <strong style="color: #58a6ff;">decrease</strong> on pullbacks in healthy trends</li>
                <li style="margin-bottom: 0.5rem;">Look for <strong style="color: #a371f7;">LPS</strong> after SOS to add to positions</li>
                <li style="margin-bottom: 0.5rem;">Exit when you see <strong style="color: #f85149;">climactic volume</strong> at new highs/lows</li>
                <li style="margin-bottom: 0.5rem;">Always consider the <strong style="color: #d29922;">broader market context</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


# ============================================
# MAIN
# ============================================

def main():
    if page == "💬 AI ChatBot":
        chatbot_page()
    elif page == "📊 Stock Analysis":
        stock_analysis_page()
    else:
        guide_page()
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>🎓 GenAI Course Final Project | Wyckoff Trader v1.0</p>
        <p style="font-size: 0.75rem;">Built with LLaMA 2 + RAG + Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
