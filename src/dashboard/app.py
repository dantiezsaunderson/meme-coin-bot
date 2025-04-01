"""
Test script for the optional Streamlit dashboard.

This script implements a simple Streamlit dashboard for the Meme Coin Signal Bot.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DATABASE_URL

# Remove sqlite:/// prefix if present
db_path = DATABASE_URL.replace('sqlite:///', '')

def load_data():
    """Load data from the database."""
    conn = sqlite3.connect(db_path)
    
    # Load tokens
    tokens_df = pd.read_sql_query("""
        SELECT 
            id, symbol, name, blockchain, 
            current_price_usd, liquidity_usd, volume_24h_usd, 
            holders_count, buy_sell_ratio,
            total_score, liquidity_score, volume_score, social_score, safety_score
        FROM tokens
        ORDER BY total_score DESC
    """, conn)
    
    # Load signals
    signals_df = pd.read_sql_query("""
        SELECT 
            s.id, t.symbol, s.signal_type, s.timestamp, s.score,
            s.price_usd, s.liquidity_usd, s.volume_24h_usd,
            s.holders_count, s.buy_sell_ratio, s.social_mentions_count,
            s.reason
        FROM signals s
        JOIN tokens t ON s.token_id = t.id
        ORDER BY s.timestamp DESC
    """, conn)
    
    # Load social mentions
    social_df = pd.read_sql_query("""
        SELECT 
            sm.id, t.symbol, sm.source, sm.author, sm.is_influencer,
            sm.timestamp, sm.sentiment_score
        FROM social_mentions sm
        JOIN tokens t ON sm.token_id = t.id
        ORDER BY sm.timestamp DESC
        LIMIT 100
    """, conn)
    
    conn.close()
    return tokens_df, signals_df, social_df

def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Meme Coin Signal Bot Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Meme Coin Signal Bot Dashboard")
    
    # Load data
    tokens_df, signals_df, social_df = load_data()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Blockchain filter
    blockchains = ["All"] + sorted(tokens_df["blockchain"].unique().tolist())
    selected_blockchain = st.sidebar.selectbox("Blockchain", blockchains)
    
    # Min score filter
    min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
    
    # Apply filters
    filtered_tokens = tokens_df
    if selected_blockchain != "All":
        filtered_tokens = filtered_tokens[filtered_tokens["blockchain"] == selected_blockchain]
    filtered_tokens = filtered_tokens[filtered_tokens["total_score"] >= min_score]
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Top Tokens", "Recent Signals", "Social Mentions"])
    
    # Tab 1: Overview
    with tab1:
        st.header("System Overview")
        
        # Create metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tokens", len(tokens_df))
        
        with col2:
            # Count signals in the last 24 hours
            last_24h = datetime.now() - timedelta(hours=24)
            recent_signals = signals_df[pd.to_datetime(signals_df["timestamp"]) > last_24h]
            st.metric("Signals (24h)", len(recent_signals))
        
        with col3:
            # Average token score
            avg_score = round(tokens_df["total_score"].mean(), 1)
            st.metric("Avg Token Score", avg_score)
        
        with col4:
            # Count tokens by blockchain
            eth_count = len(tokens_df[tokens_df["blockchain"] == "ethereum"])
            sol_count = len(tokens_df[tokens_df["blockchain"] == "solana"])
            st.metric("ETH / SOL Ratio", f"{eth_count} / {sol_count}")
        
        # Score distribution chart
        st.subheader("Score Distribution")
        fig = px.histogram(
            tokens_df, 
            x="total_score",
            nbins=20,
            color="blockchain",
            title="Token Score Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent signals chart
        st.subheader("Recent Signals")
        if not signals_df.empty:
            signals_df["date"] = pd.to_datetime(signals_df["timestamp"]).dt.date
            signal_counts = signals_df.groupby(["date", "signal_type"]).size().reset_index(name="count")
            
            fig = px.bar(
                signal_counts,
                x="date",
                y="count",
                color="signal_type",
                title="Signals by Day"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: Top Tokens
    with tab2:
        st.header("Top Tokens")
        
        if filtered_tokens.empty:
            st.info("No tokens match the selected filters.")
        else:
            # Display top tokens table
            st.dataframe(
                filtered_tokens[[
                    "symbol", "blockchain", "current_price_usd", "liquidity_usd", 
                    "volume_24h_usd", "holders_count", "total_score"
                ]].rename(columns={
                    "current_price_usd": "Price (USD)",
                    "liquidity_usd": "Liquidity (USD)",
                    "volume_24h_usd": "24h Volume (USD)",
                    "holders_count": "Holders",
                    "total_score": "Score"
                }),
                use_container_width=True
            )
            
            # Score components chart
            st.subheader("Score Components")
            top_n = min(10, len(filtered_tokens))
            top_tokens = filtered_tokens.head(top_n)
            
            score_data = pd.melt(
                top_tokens[["symbol", "liquidity_score", "volume_score", "social_score", "safety_score"]],
                id_vars=["symbol"],
                var_name="Score Component",
                value_name="Score"
            )
            
            fig = px.bar(
                score_data,
                x="symbol",
                y="Score",
                color="Score Component",
                title=f"Score Components for Top {top_n} Tokens",
                barmode="group"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: Recent Signals
    with tab3:
        st.header("Recent Signals")
        
        if signals_df.empty:
            st.info("No signals have been generated yet.")
        else:
            # Display recent signals
            st.dataframe(
                signals_df[[
                    "symbol", "signal_type", "timestamp", "score",
                    "price_usd", "liquidity_usd", "volume_24h_usd", "reason"
                ]].rename(columns={
                    "signal_type": "Signal",
                    "timestamp": "Time",
                    "score": "Score",
                    "price_usd": "Price (USD)",
                    "liquidity_usd": "Liquidity (USD)",
                    "volume_24h_usd": "24h Volume (USD)",
                    "reason": "Reason"
                }),
                use_container_width=True
            )
    
    # Tab 4: Social Mentions
    with tab4:
        st.header("Social Mentions")
        
        if social_df.empty:
            st.info("No social mentions have been recorded yet.")
        else:
            # Display social mentions
            st.dataframe(
                social_df[[
                    "symbol", "source", "author", "is_influencer",
                    "timestamp", "sentiment_score"
                ]].rename(columns={
                    "source": "Platform",
                    "author": "Author",
                    "is_influencer": "Influencer",
                    "timestamp": "Time",
                    "sentiment_score": "Sentiment"
                }),
                use_container_width=True
            )
            
            # Sentiment distribution
            st.subheader("Sentiment Distribution")
            fig = px.histogram(
                social_df,
                x="sentiment_score",
                nbins=20,
                color="source",
                title="Sentiment Score Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
