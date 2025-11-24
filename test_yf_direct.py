"""Debug Yahoo Finance enrichment"""
import asyncio
import yfinance as yf

async def test_yfinance_direct():
    print("Testing yfinance directly...")
    
    loop = asyncio.get_event_loop()
    
    # Test MSFT
    print("\n=== MSFT ===")
    try:
        stock = await loop.run_in_executor(None, yf.Ticker, "MSFT")
        info = await loop.run_in_executor(None, lambda: stock.info)
        print(f"Sector: {info.get('sector', 'NOT FOUND')}")
        print(f"Industry: {info.get('industry', 'NOT FOUND')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test AAPL
    print("\n=== AAPL ===")
    try:
        stock = await loop.run_in_executor(None, yf.Ticker, "AAPL")
        info = await loop.run_in_executor(None, lambda: stock.info)
        print(f"Sector: {info.get('sector', 'NOT FOUND')}")
        print(f"Industry: {info.get('industry', 'NOT FOUND')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_yfinance_direct())
