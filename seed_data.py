import datetime as dt
import pandas as pd

# Initial sample expenses for college/commuter persona
samples = [
    {"date": (dt.date.today() - dt.timedelta(days=2)).isoformat(), "item": "Chai & Samosa", "amount": 40.0, "category": "Food & Chai"},
    {"date": (dt.date.today() - dt.timedelta(days=2)).isoformat(), "item": "Metro Recharge", "amount": 200.0, "category": "Recharge & Bills"},
    {"date": (dt.date.today() - dt.timedelta(days=1)).isoformat(), "item": "Auto Rikshaw", "amount": 80.0, "category": "Travel & Commute"},
    {"date": (dt.date.today() - dt.timedelta(days=1)).isoformat(), "item": "Canteen Biryani", "amount": 160.0, "category": "Food & Chai"},
    {"date": dt.date.today().isoformat(), "item": "Rapido Bike", "amount": 65.0, "category": "Travel & Commute"},
    {"date": dt.date.today().isoformat(), "item": "Chai with Friends", "amount": 30.0, "category": "Food & Chai"},
]

pd.DataFrame(samples).to_csv("C:/Users/npoor/.gemini/antigravity/scratch/awaaz-kharcha/expenses.csv", index=False)
print("Seeded sample expenses.csv successfully.")

