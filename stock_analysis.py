"""
Wyckoff Stock Analysis Module
Pattern detection, backtesting, and visualization
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================
# CONFIGURATION
# ============================================

STOCK_CONFIG = {
    "default_period": "1y",
    "volume_spike_threshold": 2.0,
    "price_change_threshold": 0.03,
    "support_lookback": 20,
    "resistance_lookback": 20,
}

# Popular stocks for selection
STOCK_LIST = {
    "Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
    "Finance": ["JPM", "BAC", "GS", "V", "MA"],
    "ETFs": ["SPY", "QQQ", "IWM", "DIA", "XLF"],
    "Crypto-Related": ["COIN", "MSTR"],
    "Other": ["TSLA", "AMD", "NFLX", "DIS"]
}


# ============================================
# DATA FETCHING
# ============================================

def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch stock data using yfinance.
    
    Args:
        ticker: Stock symbol
        period: Time period (1mo, 3mo, 6mo, 1y, 2y)
        
    Returns:
        DataFrame with OHLCV data
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    
    if df.empty:
        raise ValueError(f"No data found for {ticker}")
    
    # Standardize column names
    df.columns = [c.lower() for c in df.columns]
    
    # Add technical indicators
    df['returns'] = df['close'].pct_change()
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    df['price_ma_20'] = df['close'].rolling(20).mean()
    df['price_ma_50'] = df['close'].rolling(50).mean()
    df['atr'] = calculate_atr(df, 14)
    
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    return atr


def get_stock_info(ticker: str) -> Dict:
    """Get basic stock information."""
    stock = yf.Ticker(ticker)
    info = stock.info
    
    return {
        'name': info.get('longName', ticker),
        'sector': info.get('sector', 'N/A'),
        'industry': info.get('industry', 'N/A'),
        'market_cap': info.get('marketCap', 0),
        'pe_ratio': info.get('trailingPE', 'N/A'),
        'dividend_yield': info.get('dividendYield', 0),
        'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
        'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
    }


# ============================================
# WYCKOFF PATTERN DETECTION
# ============================================

def detect_wyckoff_events(df: pd.DataFrame, config: dict = STOCK_CONFIG) -> pd.DataFrame:
    """
    Detect Wyckoff events in price data.
    
    Events detected:
    - SC: Selling Climax
    - BC: Buying Climax
    - SP: Spring
    - UT: Upthrust
    - SOS: Sign of Strength
    - SOW: Sign of Weakness
    - LPS: Last Point of Support
    - LPSY: Last Point of Supply
    """
    df = df.copy()
    
    vol_threshold = config['volume_spike_threshold']
    price_threshold = config['price_change_threshold']
    lookback = config['support_lookback']
    
    # Initialize columns
    df['event'] = ''
    df['event_strength'] = 0.0
    
    # Calculate support/resistance
    df['support'] = df['low'].rolling(lookback).min()
    df['resistance'] = df['high'].rolling(lookback).max()
    df['range_mid'] = (df['support'] + df['resistance']) / 2
    
    # Detect events
    for i in range(lookback + 5, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Recent price action
        recent_high = df['high'].iloc[i-5:i].max()
        recent_low = df['low'].iloc[i-5:i].min()
        avg_volume = df['volume'].iloc[i-20:i].mean()
        
        event = ''
        strength = 0.0
        
        # Selling Climax: High volume + big drop + closes off lows
        if (row['volume_ratio'] > vol_threshold and 
            row['returns'] < -price_threshold and
            row['close'] > row['low'] + (row['high'] - row['low']) * 0.3):
            event = 'SC'
            strength = min(row['volume_ratio'] / vol_threshold, 2.0)
        
        # Buying Climax: High volume + big rise near highs
        elif (row['volume_ratio'] > vol_threshold and 
              row['returns'] > price_threshold and
              row['close'] > df['close'].iloc[i-lookback:i].mean() * 1.05):
            event = 'BC'
            strength = min(row['volume_ratio'] / vol_threshold, 2.0)
        
        # Spring: Breaks below support then recovers
        elif (row['low'] < prev['support'] * 0.99 and 
              row['close'] > prev['support'] and
              row['volume_ratio'] < 1.5):
            event = 'SP'
            strength = 1.0 + (1.5 - row['volume_ratio'])
        
        # Upthrust: Breaks above resistance then fails
        elif (row['high'] > prev['resistance'] * 1.01 and 
              row['close'] < prev['resistance'] and
              row['volume_ratio'] < 1.5):
            event = 'UT'
            strength = 1.0 + (1.5 - row['volume_ratio'])
        
        # Sign of Strength: Rally breaks resistance on volume
        elif (row['close'] > prev['resistance'] and
              row['returns'] > price_threshold * 0.5 and
              row['volume_ratio'] > 1.3):
            event = 'SOS'
            strength = row['volume_ratio']
        
        # Sign of Weakness: Drop breaks support on volume
        elif (row['close'] < prev['support'] and
              row['returns'] < -price_threshold * 0.5 and
              row['volume_ratio'] > 1.3):
            event = 'SOW'
            strength = row['volume_ratio']
        
        # Last Point of Support: Pullback on low volume after SOS
        elif (df['event'].iloc[i-10:i].str.contains('SOS').any() and
              row['returns'] < 0 and
              row['volume_ratio'] < 0.8 and
              row['close'] > prev['support']):
            event = 'LPS'
            strength = 1.0 - row['volume_ratio']
        
        # Last Point of Supply: Rally on low volume after SOW
        elif (df['event'].iloc[i-10:i].str.contains('SOW').any() and
              row['returns'] > 0 and
              row['volume_ratio'] < 0.8 and
              row['close'] < prev['resistance']):
            event = 'LPSY'
            strength = 1.0 - row['volume_ratio']
        
        df.iloc[i, df.columns.get_loc('event')] = event
        df.iloc[i, df.columns.get_loc('event_strength')] = strength
    
    return df


def identify_phase(df: pd.DataFrame) -> Dict:
    """
    Identify current Wyckoff phase and provide analysis.
    
    Returns:
        Dict with phase info, bias, and description
    """
    recent = df.tail(30)
    events = recent[recent['event'] != '']['event'].value_counts()
    
    # Price analysis
    price_trend = (recent['close'].iloc[-1] / recent['close'].iloc[0] - 1) * 100
    volume_trend = recent['volume'].iloc[-10:].mean() / recent['volume'].iloc[:10].mean()
    
    # Determine phase
    if 'SC' in events.index or 'SP' in events.index:
        if price_trend > 2:
            phase = "Phase C/D"
            phase_name = "Accumulation - Test/Markup"
            bias = "bullish"
            description = "Spring or test detected with upward price action. Watch for Sign of Strength to confirm markup."
        else:
            phase = "Phase A/B"
            phase_name = "Accumulation - Stopping/Building"
            bias = "neutral"
            description = "Selling pressure appears exhausted. Building cause for potential markup."
    
    elif 'BC' in events.index or 'UT' in events.index:
        if price_trend < -2:
            phase = "Phase C/D"
            phase_name = "Distribution - Test/Markdown"
            bias = "bearish"
            description = "Upthrust or failed test detected with downward price action. Watch for Sign of Weakness."
        else:
            phase = "Phase A/B"
            phase_name = "Distribution - Stopping/Building"
            bias = "neutral"
            description = "Buying pressure appears exhausted. Building cause for potential markdown."
    
    elif 'SOS' in events.index:
        phase = "Phase D/E"
        phase_name = "Markup"
        bias = "bullish"
        description = "Sign of Strength confirmed. Look for Last Point of Support entries."
    
    elif 'SOW' in events.index:
        phase = "Phase D/E"
        phase_name = "Markdown"
        bias = "bearish"
        description = "Sign of Weakness confirmed. Avoid longs, consider shorts on rallies."
    
    else:
        if abs(price_trend) < 3:
            phase = "Phase B"
            phase_name = "Trading Range"
            bias = "neutral"
            description = "Price consolidating. Wait for Spring/Upthrust or SOS/SOW for direction."
        elif price_trend > 3:
            phase = "Trending"
            phase_name = "Uptrend"
            bias = "bullish"
            description = "Price in uptrend. Look for re-accumulation patterns."
        else:
            phase = "Trending"
            phase_name = "Downtrend"
            bias = "bearish"
            description = "Price in downtrend. Look for accumulation patterns at support."
    
    return {
        'phase': phase,
        'phase_name': phase_name,
        'bias': bias,
        'description': description,
        'price_change': price_trend,
        'volume_trend': volume_trend,
        'events_detected': events.to_dict()
    }


# ============================================
# BACKTESTING
# ============================================

def backtest_wyckoff_strategy(df: pd.DataFrame) -> Dict:
    """
    Backtest Wyckoff-based trading strategy.
    
    Rules:
    - Entry: After Spring (SP), LPS, or SOS
    - Exit: After UT, LPSY, SOW, or 5% stop loss
    """
    df = df.copy()
    
    trades = []
    position = None
    entry_price = 0
    entry_date = None
    
    for i in range(len(df)):
        row = df.iloc[i]
        event = row['event']
        price = row['close']
        date = df.index[i]
        
        # Entry signals
        if position is None:
            if event in ['SP', 'LPS', 'SOS']:
                position = 'long'
                entry_price = price
                entry_date = date
                trades.append({
                    'type': 'entry',
                    'signal': event,
                    'date': date,
                    'price': price
                })
        
        # Exit signals
        elif position == 'long':
            exit_reason = None
            
            # Stop loss (5%)
            if price < entry_price * 0.95:
                exit_reason = 'stop_loss'
            
            # Wyckoff exit signals
            elif event in ['UT', 'LPSY', 'SOW']:
                exit_reason = event
            
            # Take profit (15%)
            elif price > entry_price * 1.15:
                exit_reason = 'take_profit'
            
            if exit_reason:
                pnl = (price / entry_price - 1) * 100
                trades.append({
                    'type': 'exit',
                    'signal': exit_reason,
                    'date': date,
                    'price': price,
                    'pnl': pnl,
                    'entry_price': entry_price,
                    'entry_date': entry_date,
                    'holding_days': (date - entry_date).days
                })
                position = None
    
    # Calculate metrics
    exits = [t for t in trades if t['type'] == 'exit']
    
    if not exits:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'avg_return': 0,
            'max_win': 0,
            'max_loss': 0,
            'avg_holding_days': 0,
            'trades': trades
        }
    
    pnls = [t['pnl'] for t in exits]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    return {
        'total_trades': len(exits),
        'win_rate': len(wins) / len(exits) * 100 if exits else 0,
        'total_return': sum(pnls),
        'avg_return': np.mean(pnls),
        'max_win': max(pnls) if pnls else 0,
        'max_loss': min(pnls) if pnls else 0,
        'avg_holding_days': np.mean([t['holding_days'] for t in exits]),
        'profit_factor': abs(sum(wins) / sum(losses)) if losses else float('inf'),
        'trades': trades
    }


# ============================================
# VISUALIZATION
# ============================================

def create_wyckoff_chart(df: pd.DataFrame, ticker: str, show_events: bool = True) -> go.Figure:
    """
    Create interactive Plotly chart with Wyckoff annotations.
    """
    # Create subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f'{ticker} Price Action', 'Volume', 'Volume Ratio')
    )
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#3fb950',
            decreasing_line_color='#f85149'
        ),
        row=1, col=1
    )
    
    # Moving averages
    if 'price_ma_20' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['price_ma_20'],
                mode='lines',
                name='MA 20',
                line=dict(color='#58a6ff', width=1)
            ),
            row=1, col=1
        )
    
    if 'price_ma_50' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['price_ma_50'],
                mode='lines',
                name='MA 50',
                line=dict(color='#a371f7', width=1)
            ),
            row=1, col=1
        )
    
    # Support/Resistance
    if 'support' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['support'],
                mode='lines',
                name='Support',
                line=dict(color='#3fb950', width=1, dash='dash')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['resistance'],
                mode='lines',
                name='Resistance',
                line=dict(color='#f85149', width=1, dash='dash')
            ),
            row=1, col=1
        )
    
    # Wyckoff event markers
    if show_events:
        event_configs = {
            'SC': {'color': '#58a6ff', 'symbol': 'triangle-down', 'name': 'Selling Climax'},
            'BC': {'color': '#a371f7', 'symbol': 'triangle-up', 'name': 'Buying Climax'},
            'SP': {'color': '#3fb950', 'symbol': 'star', 'name': 'Spring'},
            'UT': {'color': '#f85149', 'symbol': 'x', 'name': 'Upthrust'},
            'SOS': {'color': '#7ee787', 'symbol': 'arrow-up', 'name': 'Sign of Strength'},
            'SOW': {'color': '#ffa657', 'symbol': 'arrow-down', 'name': 'Sign of Weakness'},
            'LPS': {'color': '#56d364', 'symbol': 'circle', 'name': 'Last Point of Support'},
            'LPSY': {'color': '#f78166', 'symbol': 'circle', 'name': 'Last Point of Supply'},
        }
        
        for event_type, config in event_configs.items():
            event_df = df[df['event'] == event_type]
            if not event_df.empty:
                fig.add_trace(
                    go.Scatter(
                        x=event_df.index,
                        y=event_df['high'] * 1.02,
                        mode='markers+text',
                        name=config['name'],
                        marker=dict(
                            size=12,
                            color=config['color'],
                            symbol=config['symbol'],
                            line=dict(width=1, color='white')
                        ),
                        text=event_type,
                        textposition='top center',
                        textfont=dict(size=10, color=config['color'])
                    ),
                    row=1, col=1
                )
    
    # Volume bars
    colors = ['#f85149' if row['close'] < row['open'] else '#3fb950' 
              for _, row in df.iterrows()]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        ),
        row=2, col=1
    )
    
    # Volume MA
    if 'volume_ma' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['volume_ma'],
                mode='lines',
                name='Vol MA',
                line=dict(color='#d29922', width=1)
            ),
            row=2, col=1
        )
    
    # Volume ratio
    if 'volume_ratio' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['volume_ratio'],
                mode='lines',
                name='Vol Ratio',
                line=dict(color='#58a6ff', width=1),
                fill='tozeroy',
                fillcolor='rgba(88, 166, 255, 0.1)'
            ),
            row=3, col=1
        )
        
        # Add threshold line
        fig.add_hline(y=2.0, line_dash="dash", line_color="#d29922", 
                      annotation_text="High Volume", row=3, col=1)
    
    # Layout
    fig.update_layout(
        title=dict(
            text=f'<b>{ticker}</b> - Wyckoff Analysis',
            font=dict(size=20, color='#e6edf3')
        ),
        template='plotly_dark',
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(family='Inter, sans-serif', color='#e6edf3'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(22, 27, 34, 0.8)'
        ),
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # Update axes
    fig.update_xaxes(
        gridcolor='#30363d',
        showgrid=True,
        zeroline=False
    )
    
    fig.update_yaxes(
        gridcolor='#30363d',
        showgrid=True,
        zeroline=False
    )
    
    return fig


def create_backtest_chart(df: pd.DataFrame, backtest_results: Dict, ticker: str) -> go.Figure:
    """Create chart showing backtest trades."""
    fig = go.Figure()
    
    # Price line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['close'],
            mode='lines',
            name='Price',
            line=dict(color='#58a6ff', width=2)
        )
    )
    
    # Entry/Exit markers
    trades = backtest_results['trades']
    
    entries = [t for t in trades if t['type'] == 'entry']
    exits = [t for t in trades if t['type'] == 'exit']
    
    if entries:
        fig.add_trace(
            go.Scatter(
                x=[t['date'] for t in entries],
                y=[t['price'] for t in entries],
                mode='markers',
                name='Entry',
                marker=dict(
                    size=15,
                    color='#3fb950',
                    symbol='triangle-up',
                    line=dict(width=2, color='white')
                ),
                text=[f"Entry: {t['signal']}<br>${t['price']:.2f}" for t in entries],
                hovertemplate='%{text}<extra></extra>'
            )
        )
    
    if exits:
        colors = ['#3fb950' if t['pnl'] > 0 else '#f85149' for t in exits]
        fig.add_trace(
            go.Scatter(
                x=[t['date'] for t in exits],
                y=[t['price'] for t in exits],
                mode='markers',
                name='Exit',
                marker=dict(
                    size=15,
                    color=colors,
                    symbol='triangle-down',
                    line=dict(width=2, color='white')
                ),
                text=[f"Exit: {t['signal']}<br>${t['price']:.2f}<br>PnL: {t['pnl']:.1f}%" for t in exits],
                hovertemplate='%{text}<extra></extra>'
            )
        )
    
    fig.update_layout(
        title=f'<b>{ticker}</b> - Backtest Results',
        template='plotly_dark',
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(family='Inter, sans-serif', color='#e6edf3'),
        height=400,
        showlegend=True,
        legend=dict(orientation='h', y=1.1)
    )
    
    return fig


# ============================================
# MAIN ANALYZER CLASS
# ============================================

class StockAnalyzer:
    """Complete stock analysis with Wyckoff detection."""
    
    def __init__(self, config: dict = STOCK_CONFIG):
        self.config = config
        self.cache = {}
    
    def analyze(self, ticker: str, period: str = "1y") -> Dict:
        """
        Complete analysis of a stock.
        
        Returns dict with:
        - data: DataFrame with OHLCV and events
        - info: Stock information
        - phase: Current Wyckoff phase
        - backtest: Backtest results
        - chart: Plotly figure
        - backtest_chart: Backtest Plotly figure
        """
        cache_key = f"{ticker}_{period}"
        
        # Fetch data
        df = fetch_stock_data(ticker, period)
        
        # Get stock info
        try:
            info = get_stock_info(ticker)
        except:
            info = {'name': ticker}
        
        # Detect Wyckoff events
        df = detect_wyckoff_events(df, self.config)
        
        # Identify phase
        phase = identify_phase(df)
        
        # Run backtest
        backtest = backtest_wyckoff_strategy(df)
        
        # Create charts
        chart = create_wyckoff_chart(df, ticker)
        backtest_chart = create_backtest_chart(df, backtest, ticker)
        
        result = {
            'ticker': ticker,
            'data': df,
            'info': info,
            'phase': phase,
            'backtest': backtest,
            'chart': chart,
            'backtest_chart': backtest_chart
        }
        
        self.cache[cache_key] = result
        return result


# ============================================
# QUICK TEST
# ============================================

if __name__ == "__main__":
    print("🧪 Testing Stock Analyzer...")
    
    analyzer = StockAnalyzer()
    result = analyzer.analyze("AAPL", "6mo")
    
    print(f"\n📊 {result['info'].get('name', 'AAPL')}")
    print(f"   Phase: {result['phase']['phase_name']}")
    print(f"   Bias: {result['phase']['bias']}")
    print(f"   Events: {result['phase']['events_detected']}")
    print(f"\n📈 Backtest Results:")
    print(f"   Trades: {result['backtest']['total_trades']}")
    print(f"   Win Rate: {result['backtest']['win_rate']:.1f}%")
    print(f"   Total Return: {result['backtest']['total_return']:.2f}%")
