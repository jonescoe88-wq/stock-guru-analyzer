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
            
            # Ensure the dataframes actually contain data rows before processing
            if financials.empty or cashflow.empty:
                st.error("Yahoo Finance did not return enough fundamental statement history for this ticker. Try an established US equity (e.g., AAPL, MSFT).")
                st.stop()
                
           # ==========================================
            # 1. CORE DATA CRITERIA EVALUATION
            # ==========================================
            results = {}
            
            # Helper logic to handle messy, inconsistent index row names from Yahoo
            def get_financial_row(df, possible_names):
                # Standardize index row labels (lowercase, stripped spaces)
                clean_index = [str(idx).lower().replace(" ", "").replace("_", "") for idx in df.index]
                for name in possible_names:
                    target = name.lower().replace(" ", "").replace("_", "")
                    if target in clean_index:
                        idx_position = clean_index.index(target)
                        return df.iloc[idx_position]
                return None

            # Look up Revenue safely
            revenue_row = get_financial_row(financials, ['Total Revenue', 'TotalRevenue', 'Revenue'])
            if revenue_row is not None and len(revenue_row) >= 2:
                rev_growth = (revenue_row.iloc[0] - revenue_row.iloc[1]) / (revenue_row.iloc[1] if revenue_row.iloc[1] != 0 else 1)
                results['Revenue Growth (>10%)'] = (rev_growth > 0.10, f"{rev_growth:.1%}")
            else:
                results['Revenue Growth (>10%)'] = (False, "Data Missing")

            # Look up Net Income safely to check EPS/Income Growth
            net_inc_row = get_financial_row(financials, ['Net Income', 'NetIncome', 'Net Income Common Stockholders'])
            if net_inc_row is not None and len(net_inc_row) >= 2:
                net_inc_current = net_inc_row.iloc[0]
                net_inc_prev = net_inc_row.iloc[1]
                eps_growth_yoy = (net_inc_current - net_inc_prev) / abs(net_inc_prev) if net_inc_prev != 0 else 0
                results['EPS Growth (>12%)'] = (eps_growth_yoy > 0.12, f"{eps_growth_yoy:.1%}")
            else:
                results['EPS Growth (>12%)'] = (False, "Data Missing")
            
            # Look up Free Cash Flow safely
            fcf_row = get_financial_row(cashflow, ['Free Cash Flow', 'FreeCashFlow', 'Total Cash From Operating Activities'])
            if fcf_row is not None and revenue_row is not None:
                fcf_val = fcf_row.iloc[0]
                rev_val = revenue_row.iloc[0]
                fcf_margin = fcf_val / rev_val if rev_val != 0 else 0
                results['FCF Margin (>10%)'] = (fcf_margin > 0.10, f"{fcf_margin:.1%}")
            else:
                results['FCF Margin (>10%)'] = (False, "Data Missing")
            
            # Stability
            current_ratio = info.get('currentRatio', 0)
            results['Current Ratio (>1.5)'] = (current_ratio > 1.5 if current_ratio else False, f"{current_ratio:.2f}" if current_ratio else "N/A")
            
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
            # 5. HISTORICAL SIMULATION DATA ENGINE (ADAPTIVE TIME-HORIZON)
            # ==========================================
            # Fetch whatever maximum history is available, even if short
            max_hist = ticker.history(period="max")
            
            if len(max_hist) >= 5: # Needs at least a week of trading data to calculate
                total_trading_days = len(max_hist)
                years_trading = total_trading_days / 252.3
                
                # Prevent math explosion for ultra-new IPOs by capping minimum years at a fraction
                years_trading_capped = max(years_trading, 0.01) 
                
                # Calculate true annualized return since inception
                asset_true_cagr = (max_hist['Close'].iloc[-1] / max_hist['Close'].iloc[0]) ** (1 / years_trading_capped) - 1
                
                # Peak-to-trough historical drawdown
                rolling_max = max_hist['Close'].cummax()
                max_crash = ((max_hist['Close'] - rolling_max) / rolling_max).min()
                
                st.markdown("---")
                st.subheader("💰 Asset Lifespan Risk & Return Simulator")
                
                # Dynamically frame the text labels based on asset maturity
                if years_trading < 1.0:
                    st.caption(f"🚨 **New Asset Profile:** This ticker has a short public footprint of only **{total_trading_days} trading days** (~{years_trading*12:.1f} months). Performance is highly volatile.")
                else:
                    st.caption(f"Simulating a $1,000 baseline investment across the available **{years_trading:.1f}-year** lifecycle of **{ticker_symbol}**.")
                
                principal = 1000.0
                
                # Adjust projection intervals based on how long the stock has actually existed
                if years_trading < 1.0:
                    # For brand new assets, show short-term compounding metrics
                    v1 = principal * (1 + asset_true_cagr)**(1/12)
                    v2 = principal * (1 + asset_true_cagr)**(3/12)
                    v3 = principal * (1 + asset_true_cagr)**(6/12)
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric(label="Proj. 1-Month Value", value=f"${v1:,.2f}", delta=f"+${v1 - principal:,.2f}" if v1 >= principal else f"${v1 - principal:,.2f}")
                    with c2: st.metric(label="Proj. 3-Month Value", value=f"${v2:,.2f}", delta=f"+${v2 - principal:,.2f}" if v2 >= principal else f"${v2 - principal:,.2f}")
                    with c3: st.metric(label="Proj. 6-Month Value", value=f"${v3:,.2f}", delta=f"+${v3 - principal:,.2f}" if v3 >= principal else f"${v3 - principal:,.2f}")
                else:
                    # Standard annual milestones for mature assets
                    v1 = principal * (1 + asset_true_cagr)**1
                    v5 = principal * (1 + asset_true_cagr)**min(5, max(1, int(years_trading)))
                    v10 = principal * (1 + asset_true_cagr)**min(10, max(1, int(years_trading)))
                    
                    label_5y = f"{min(5, max(1, int(years_trading)))} Year Value"
                    label_10y = f"{min(10, max(1, int(years_trading)))} Year Value"
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric(label="1 Year Value", value=f"${v1:,.2f}", delta=f"+${v1 - principal:,.2f}" if v1 >= principal else f"${v1 - principal:,.2f}")
                    with c2: st.metric(label=label_5y, value=f"${v5:,.2f}", delta=f"+${v5 - principal:,.2f}" if v5 >= principal else f"${v5 - principal:,.2f}")
                    with c3: st.metric(label=label_10y, value=f"${v10:,.2f}", delta=f"+${v10 - principal:,.2f}" if v10 >= principal else f"${v10 - principal:,.2f}")
                
                st.warning(f"⚠️ **Volatility Risk Profile:** Based on its true historical footprint, the asset's annualized performance calculation trends at **{asset_true_cagr:.1%}**. However, holding this asset meant enduring a maximum peak-to-trough market drop of **{max_crash:.1%}** from its highs.")
