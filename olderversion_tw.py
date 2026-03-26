main
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import threading
import queue
import time
from datetime import datetime
from collections import deque

# Import local modules
from twitch_listener import TwitchBot
from analysis import Analyzer
from config import Config

# Validate config
Config.validate()

# Global thread-safe queue for incoming messages
message_queue = queue.Queue()

# Data storage (rolling window of last 100 seconds)
HISTORY_LENGTH = 100
time_series = deque(maxlen=HISTORY_LENGTH)
sentiment_series = deque(maxlen=HISTORY_LENGTH)
volume_series = deque(maxlen=HISTORY_LENGTH)

# Initialize with zeros
now = datetime.now()
for i in range(HISTORY_LENGTH):
    time_series.append(now)
    sentiment_series.append(0)
    volume_series.append(0)

# Initialize Analyzer
analyzer = Analyzer()

# Initialize Dash App
app = dash.Dash(__name__)
app.title = f"Twitch Riot Detector: {Config.CHANNEL}"

# ============================================
# LAYOUT
# ============================================
app.layout = html.Div(
    style={
        'backgroundColor': '#0e0e10',
        'color': '#efeff1',
        'minHeight': '100vh',
        'padding': '20px',
        'fontFamily': 'Arial, sans-serif'
    },
    children=[
        # Header
        html.H1(
            f"🔴 Twitch Riot Detector: {Config.CHANNEL}",
            style={
                'textAlign': 'center',
                'color': '#9147ff',
                'marginBottom': '30px'
            }
        ),
        
        # Graphs Container
        html.Div([
            # Sentiment Graph
            html.Div([
                html.H3("📊 Live Sentiment", style={'textAlign': 'center'}),
                dcc.Graph(id='live-sentiment-graph', animate=False)
            ], style={'width': '48%', 'display': 'inline-block'}),
            
            # Volume Graph
            html.Div([
                html.H3("⚡ Chat Velocity (Msg/sec)", style={'textAlign': 'center'}),
                dcc.Graph(id='live-volume-graph', animate=False)
            ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
        ], style={'marginBottom': '30px'}),
        
        # Alert Box
        html.Div(
            id='alert-box',
            style={
                'textAlign': 'center',
                'fontSize': '28px',
                'fontWeight': 'bold',
                'marginTop': '20px',
                'padding': '20px',
                'borderRadius': '10px',
                'minHeight': '60px'
            }
        ),
        
        # Stats Bar
        html.Div(id='stats-bar', style={
            'textAlign': 'center',
            'marginTop': '20px',
            'fontSize': '18px',
            'color': '#adadb8'
        }),
        
        # Interval Component (triggers update every 1 second)
        dcc.Interval(
            id='interval-component',
            interval=1000,  # 1 second
            n_intervals=0
        )
    ]
)


# ============================================
# BACKGROUND THREAD
# ============================================
def start_twitch_listener():
    """Run Twitch IRC bot in background thread."""
    try:
        bot = TwitchBot(
            channel=Config.CHANNEL.lstrip('#'),
            token=Config.TMI_TOKEN,
            msg_queue=message_queue
        )
        bot.connect()
    except Exception as e:
        print(f"❌ Bot thread error: {e}")


# ============================================
# CALLBACKS
# ============================================
@app.callback(
    [
        Output('live-sentiment-graph', 'figure'),
        Output('live-volume-graph', 'figure'),
        Output('alert-box', 'children'),
        Output('alert-box', 'style'),
        Output('stats-bar', 'children')
    ],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    """Main update function called every second."""
    
    # 1. Collect all new messages from queue
    new_messages = []
    while not message_queue.empty():
        try:
            msg = message_queue.get_nowait()
            new_messages.append(msg)
        except queue.Empty:
            break
    
    # 2. Analyze this batch
    current_time = datetime.now()
    
    if new_messages:
        # Calculate average sentiment
        sentiments = [analyzer.get_sentiment(m['message']) for m in new_messages]
        avg_sentiment = sum(sentiments) / len(sentiments)
        volume = len(new_messages)
        
        # Check for hype/toxic
        hype_count = sum(1 for m in new_messages if analyzer.is_hype(m['message']))
        toxic_count = sum(1 for m in new_messages if analyzer.is_toxic(m['message']))
    else:
        avg_sentiment = 0
        volume = 0
        hype_count = 0
        toxic_count = 0
    
    # 3. Update rolling windows
    time_series.append(current_time)
    sentiment_series.append(avg_sentiment)
    volume_series.append(volume)
    
    # 4. Create visualizations
    
    # Sentiment Graph
    fig_sentiment = go.Figure(
        data=[go.Scatter(
            x=list(time_series),
            y=list(sentiment_series),
            mode='lines+markers',
            line=dict(
                color='#1db954' if avg_sentiment >= 0 else '#ff4444',
                width=3
            ),
            marker=dict(size=4),
            fill='tozeroy',
            fillcolor='rgba(29, 185, 84, 0.2)' if avg_sentiment >= 0 else 'rgba(255, 68, 68, 0.2)'
        )],
        layout=go.Layout(
            paper_bgcolor='#18181b',
            plot_bgcolor='#18181b',
            font={'color': '#efeff1'},
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(
                range=[-1, 1],
                title='Sentiment',
                gridcolor='#2f2f35'
            ),
            margin={'l': 50, 'b': 30, 't': 10, 'r': 10},
            hovermode='closest'
        )
    )
    
    # Volume Graph
    fig_volume = go.Figure(
        data=[go.Bar(
            x=list(time_series),
            y=list(volume_series),
            marker=dict(
                color=list(volume_series),
                colorscale='Viridis',
                showscale=False
            )
        )],
        layout=go.Layout(
            paper_bgcolor='#18181b',
            plot_bgcolor='#18181b',
            font={'color': '#efeff1'},
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(
                title='Messages/sec',
                gridcolor='#2f2f35'
            ),
            margin={'l': 50, 'b': 30, 't': 10, 'r': 10}
        )
    )
    
    # 5. Alert Logic
    alert_text = ""
    alert_style = {
        'textAlign': 'center',
        'fontSize': '28px',
        'fontWeight': 'bold',
        'marginTop': '20px',
        'padding': '20px',
        'borderRadius': '10px',
        'minHeight': '60px'
    }
    
    # Calculate recent metrics
    recent_volume = sum(list(volume_series)[-10:]) / 10
    recent_sentiment = sum(list(sentiment_series)[-10:]) / 10
    
    if recent_volume > 15:  # High chat velocity
        alert_text = "🔥 HYPE MOMENT DETECTED! Chat is going WILD! 🔥"
        alert_style['backgroundColor'] = '#ff6b35'
        alert_style['color'] = 'white'
    elif recent_sentiment < -0.5 and recent_volume > 5:
        alert_text = "⚠️ TOXICITY SPIKE! Negative sentiment rising! ⚠️"
        alert_style['backgroundColor'] = '#ff4444'
        alert_style['color'] = 'white'
    elif recent_sentiment > 0.5 and recent_volume > 5:
        alert_text = "💚 Positive vibes in chat! 💚"
        alert_style['backgroundColor'] = '#1db954'
        alert_style['color'] = 'white'
    else:
        alert_text = "✓ Chat activity normal"
        alert_style['backgroundColor'] = '#18181b'
        alert_style['color'] = '#adadb8'
    
    # 6. Stats summary
    total_messages = sum(volume_series)
    avg_overall_sentiment = sum(sentiment_series) / len(sentiment_series) if sentiment_series else 0
    
    stats_text = f"Total Messages: {int(total_messages)} | Avg Sentiment: {avg_overall_sentiment:.2f} | Current Volume: {volume} msg/s"
    
    return fig_sentiment, fig_volume, alert_text, alert_style, stats_text


# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting Twitch Riot Detector")
    print("=" * 50)
    
    # Start Twitch listener in background thread
    listener_thread = threading.Thread(target=start_twitch_listener, daemon=True)
    listener_thread.start()
    
    print(f"✓ Bot connected to {Config.CHANNEL}")
    print("✓ Starting dashboard server...")
    print("=" * 50)
    
    # Start Dash server
    app.run(debug=False, host='0.0.0.0', port=8050)
    

   # twitchlistner
   import socket
import select
import time
import re

class TwitchBot:
    """
    Connects to Twitch IRC and streams chat messages.
    Uses anonymous connection (no auth required).
    """
    
    def __init__(self, channel, token, msg_queue):
        self.server = 'irc.chat.twitch.tv'
        self.port = 6667
        self.channel = f"#{channel.lstrip('#').lower()}"
        
        # For anonymous read-only: use justinfan12345
        self.nick = "justinfan12345"
        self.token = token if token else None
        
        self.queue = msg_queue
        self.sock = None
        self.running = True

    def connect(self):
        """Establish connection to Twitch IRC."""
        self.sock = socket.socket()
        
        try:
            print(f"🔌 Connecting to {self.server}:{self.port}...")
            self.sock.connect((self.server, self.port))
            
            # Anonymous auth (no password needed)
            if self.token:
                self.sock.send(f"PASS oauth:{self.token}\n".encode('utf-8'))
            self.sock.send(f"NICK {self.nick}\n".encode('utf-8'))
            self.sock.send(f"JOIN {self.channel}\n".encode('utf-8'))
            
            print(f"✓ Connected to {self.channel}")
            self.listen()
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            raise

    def listen(self):
        """Main loop: read messages from IRC."""
        buffer = ""
        
        while self.running:
            try:
                # Non-blocking socket read with timeout
                ready_to_read, _, _ = select.select([self.sock], [], [], 1.0)
                
                if ready_to_read:
                    response = self.sock.recv(2048).decode('utf-8', errors='ignore')
                    
                    if not response:
                        print("⚠️ Connection closed by server")
                        break
                    
                    buffer += response
                    lines = buffer.split('\r\n')
                    buffer = lines.pop()  # Keep incomplete line
                    
                    for line in lines:
                        if line.strip():
                            self.process_line(line)
                            
            except Exception as e:
                print(f"❌ Error reading socket: {e}")
                break
        
        print("🛑 Listener stopped")

    def process_line(self, line):
        """Parse IRC messages and extract chat data."""
        
        # Respond to PING to keep connection alive
        if line.startswith('PING'):
            self.sock.send("PONG :tmi.twitch.tv\n".encode('utf-8'))
            return
        
        # Parse PRIVMSG (chat messages)
        # Format: :username!username@username.tmi.twitch.tv PRIVMSG #channel :message
        match = re.search(r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.*)", line)
        
        if match:
            username = match.group(1)
            message = match.group(2).strip()
            
            # Push to queue for main thread
            self.queue.put({
                'username': username,
                'message': message,
                'timestamp': time.time()
            })
            
            # Debug print (optional)
            # print(f"[{username}] {message}")

    def disconnect(self):
        """Clean shutdown."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

            #analysis.py
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import collections
import statistics

class Analyzer:
    """
    Sentiment and toxicity analysis for Twitch chat messages.
    Uses VADER with custom Twitch emote lexicon.
    """

    def __init__(self, window_size=50):
        self.analyzer = SentimentIntensityAnalyzer()
        self._inject_twitch_lexicon()
        
        # Rolling window for trend analysis
        self.sentiment_window = collections.deque(maxlen=window_size)
        self.hype_window = collections.deque(maxlen=window_size)

    def _inject_twitch_lexicon(self):
        """Add Twitch-specific emotes to VADER's lexicon."""
        twitch_emotes = {
            'pog': 1.5, 'pogchamp': 1.5, 'poggers': 1.2,
            'kappa': -0.3, 'kappapride': 0.5,
            'lul': 0.1, 'lulw': 0.1, 'omegalul': 0.2,
            'biblethump': -0.8, 'pepehands': -0.8,
            'monkas': -0.5, 'monkaw': -0.8,
            'residentsleeper': -1.0,
            'kreygasm': 1.0, 'seemsgood': 0.8,
            '4head': 0.5, 'failfish': -1.0,
            '<3': 1.5, 'heyguys': 1.0,
            'notlikethis': -1.0, 'blessrng': 0.5,
            'kekw': 0.3, 'pepega': -0.2,
            'sadge': -0.7, 'copium': -0.4,
            'hopium': 0.6, 'gigachad': 1.3,
            'trash': -1.2, 'cringe': -0.9,
            'hype': 1.4, 'toxic': -1.5
        }
        self.analyzer.lexicon.update(twitch_emotes)

    def get_sentiment(self, message):
        """
        Analyze sentiment of a message.
        Returns compound score between -1 (negative) and 1 (positive).
        """
        if not message:
            return 0
        
        scores = self.analyzer.polarity_scores(message.lower())
        compound = scores['compound']
        
        # Update sliding window
        self.sentiment_window.append(compound)
        
        return compound

    def is_hype(self, message):
        """Detect if message indicates high excitement/hype."""
        sentiment = self.get_sentiment(message)
        hype_score = abs(sentiment)
        
        self.hype_window.append(hype_score)
        
        # Hype threshold: absolute sentiment > 0.7
        return hype_score > 0.7

    def is_toxic(self, message):
        """Detect potentially toxic messages."""
        sentiment = self.get_sentiment(message)
        
        # Toxic if strongly negative
        if sentiment < -0.6:
            return True
        
        # Also check for toxic keywords
        toxic_words = ['trash', 'toxic', 'cringe', 'hate', 'kys', 'kill yourself']
        message_lower = message.lower()
        
        return any(word in message_lower for word in toxic_words)

    def get_avg_sentiment(self):
        """Get average sentiment over the window."""
        return statistics.mean(self.sentiment_window) if self.sentiment_window else 0

    def get_avg_hype(self):
        """Get average hype level over the window."""
        return statistics.mean(self.hype_window) if self.hype_window else 0

#config
import os
import sys
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Config:
    """Central configuration loader with validation."""
    TMI_TOKEN = os.getenv("TMI_TOKEN")
    CLIENT_ID = os.getenv("CLIENT_ID")
    BOT_NICK = os.getenv("BOT_NICK", "justinfan12345")
    CHANNEL = os.getenv("CHANNEL", "shroud")
    
    # Twitch IRC Server Details 
    SERVER = 'irc.chat.twitch.tv'
    PORT = 6667

    @staticmethod
    def validate():
        """Ensure critical credentials exist before starting."""
        if not Config.TMI_TOKEN:
            print("WARNING: TMI_TOKEN not set. Using anonymous mode.")
        if not Config.CHANNEL:
            print("ERROR: CHANNEL must be set in .env")
            sys.exit(1)
        
        # Ensure channel has hash prefix
        if not Config.CHANNEL.startswith('#'):
            Config.CHANNEL = '#' + Config.CHANNEL
        
        print(f"✓ Config loaded: Channel={Config.CHANNEL}")

# Expose as module-level constants
CHANNEL = Config.CHANNEL
TMI_TOKEN = Config.TMI_TOKEN