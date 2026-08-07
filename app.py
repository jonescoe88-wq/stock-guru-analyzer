import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Guru Stock Analyzer", layout="centered")

st.title("📊 Investor's Checklist Stock Analyzer")
st.write("Input a stock ticker to scrub the internet and evaluate its optimal holding time-frame.")

# User input field
ticker_symbol = st.text_input("Enter Stock Ticker (e.g., AAPL, BA, MSFT):", "").upper()

if ticker_symbol:
    with st.spinner(f"Scrubbing live data for {ticker_symbol}..."):
        ticker = yf.Ticker(ticker_symbol)
        
        try:
            info = ticker.info
            financials = ticker.financials
            cashflow = ticker.cashflow
            history = ticker.history(period="1y")
            hist_20y = ticker.history(period="20y")
            
            if financials.shape[1] < 2 or cashflow.shape[1] < 2:
                st.error("Insufficient historical financial data available for this ticker.")
                st.stop()
                
            # ==========================================
            # 1. CORE DATA CRITERIA EVALUATION
            # ==========================================
            results = {}
            
            # Growth
            rev_growth = (financials.iloc[0]['Total Revenue'] - financials.iloc[1]['Total Revenue']) / financials.iloc[1]['Total Revenue']
            results['Revenue Growth (>10%)'] = (rev_growth > 0.10, f"{rev_growth:.1%}")
            
            net_inc_current = financials.iloc[0]['Net Income']
            net_inc_prev = financials.iloc[1]['Net Income']
            eps_growth_yoy = (net_inc_current - net_inc_prev) / abs(net_inc_prev) if net_inc_prev != 0 else 0
            results['EPS Growth (>12%)'] = (eps_growth_yoy > 0.12, f"{eps_growth_yoy:.1%}")
            
            # Cash Flow
            fcf = cashflow.iloc[0]['Free Cash Flow'] if 'Free Cash Flow' in cashflow.index else 0
            rev = financials.iloc[0]['Total Revenue']
            fcf_margin = fcf / rev if rev else 0
            results['FCF Margin (>10%)'] = (fcf_margin > 0.10, f"{fcf_margin:.1%}")
            
            # Stability
            current_ratio = info.get('currentRatio', 0)
            results['Current Ratio (>1.5)'] = (current_ratio > 1.5, f"{current_ratio:.2f}" if current_ratio else "N/A")
            
            # Valuation
            pe_ratio = info.get('trailingPE', None)
            results['P/E Ratio (<20)'] = (pe_ratio < 20 if pe_ratio else False, f"{pe_ratio:.1f}" if pe_ratio else "N/A")
            
            # Tally scores
            long_term_score = sum([1 for passed, _ in results.values() if passed])
            total_metrics = len(results)
            
            # ==========================================
            # 2. SHORT-TERM TECHNICAL LAYER
            # ==========================================
            close_prices = history['Close']
            ma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            ma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
            rs = gain / (loss if loss != 0 else 1)
            rsi = 100 - (100 / (1 + rs))
            
            short_term_bullish = current_price > ma_50 and rsi < 70

            # ==========================================
            # 3. CRITICAL DECISION BANNER (FIRST TO STATE)
            # ==========================================
            st.markdown("---")
            st.header("🎯 AGENT STRATEGY VERDICT")
            
            # Logic defining the definitive framework
            if long_term_score >= 3: # Fundamentally Sound
                st.success("### 🟢 RECOMMENDATION: LONG-TERM INVESTING HOLD")
                st.metric(label="Suggested Holding Duration", value="3 to 10+ Years")
                st.info(f"**Justification:** This asset clears the majority of quality thresholds ({long_term_score}/{total_metrics}). It possesses the structural stability, margins, and health required to anchor a long-term compound investment account.")
            
            elif long_term_score < 3 and short_term_bullish: # Broken fundamentals but high momentum
                st.warning("### 🟡 RECOMMENDATION: SHORT-TERM MOMENTUM TRADE ONLY")
                st.metric(label="Suggested Holding Duration", value="2 to 6 Weeks (Strict Stop-Loss)")
                st.info(f"**Justification:** This asset heavily fails fundamental quality checkmarks ({long_term_score}/{total_metrics}) and is structurally weak. However, technical indicators display clear short-term price strength. Play the near-term momentum window, but do not treat this as a safe long-term asset.")
                
            else: # Bad fundamentals + no technical momentum
                st.error("### 🔴 RECOMMENDATION: DO NOT ENTER (AVOID ASSET)")
                st.metric(label="Suggested Holding Duration", value="0 Days (Immediate Skip)")
                st.info(f"**Justification:** The company completely fails core long-term fundamentals and displays zero near-term price momentum or buying trends. Avoid entirely.")
            
            # ==========================================
            # 4. EXPANDABLE METRIC DETAILS
            # ==========================================
            st.markdown("---")
            with st.expander("📋 View Full Breakdown Checklist Metrics"):
                for metric, (passed, value) in results.items():
                    status = "✅ PASS" if passed else "❌ FAIL"
                    st.write(f"**{metric}**: {value} — {status}")
                
                st.write(f"**Current Price:** ${current_price:.2f} (50 MA: ${ma_50:.2f})")
                st.write(f"**14-Day RSI Momentum Indicator:** {rsi:.1f}")

            # ==========================================
            # 5. DYNAMIC HISTORICAL RETURN PERFORMANCE
            # ==========================================
            if len(hist_20y) >= 252:
                years = len(hist_20y) / 252.3
                stock_true_cagr = (hist_20y['Close'].iloc[-1] / hist_20y['Close'].iloc[0]) ** (1 / years) - 1
                
                rolling_max = hist_20y['Close'].cummax()
                max_crash = ((hist_20y['Close'] - rolling_max) / rolling_max).min()
                
                st.markdown("---")
                st.subheader("💰 20-Year Historical Risk Simulator")
                st.caption(f"Simulating a $1,000 initial investment using the true historical footprint of **{ticker_symbol}**.")
                
                principal = 1000.0
                v1 = principal * (1 + stock_true_cagr)**1
                v5 = principal * (1 + stock_true_cagr)**5
                v10 = principal * (1 + stock_true_cagr)**10
                
                c1, c2, c3 = st.columns(3)
                with c1: st.metric(label="1 Year Value", value=f"${v1:,.2f}", delta=f"+${v1 - principal:,.2f}")
                with c2: st.metric(label="5 Year Value", value=f"${v5:,.2f}", delta=f"+${v5 - principal:,.2f}")
                with c3: st.metric(label="10 Year Value", value=f"${v10:,.2f}", delta=f"+${v10 - principal:,.2f}")
                
                st.warning(f"⚠️ **True Risk Assessment:** While the historical compound performance averaged **{stock_true_cagr:.1%}** annually, holding this exact stock meant surviving a devastating peak-to-trough drop of **{max_crash:.1%}** at its worst point.")

        except Exception as e:
            st.error(f"Error parsing market metrics: {e}")