# Stock Tracker

Python tool for tracking stock buys and sells from **Trading 212 CSV exports**, aligned with **Irish CGT rules**.

## Features
- FIFO tracking of buys and sells  
- Per-lot cost basis and remaining quantity  
- Supports fractional shares, partial sells, and stock splits  
- Calculates realised gains and unrealised value / ROI  

## Design
- **Broker EUR totals are the source of truth**  
  Trading 212 `Total (EUR)` is used for all historical buys and sells  
- **Broker FX rates are reference-only**  
  Stored for audit, not reused in calculations  
- **Live valuation uses USD → EUR FX**  
  Applied consistently for unrealised value only  

## Scope
- Accounting and tracking tool  
- No broker API integration  
- Not a tax filing system  

## Status
Core tracking logic implemented. CSV ingestion and persistence in progress.
