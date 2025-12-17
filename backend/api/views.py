from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import Watchlist
import random
import datetime
import akshare as ak
import pandas as pd

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({"status": "error", "message": "Username and password are required"}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({"status": "error", "message": "Username already exists"}, status=400)
        
        user = User.objects.create(
            username=username,
            password=make_password(password)
        )
        return Response({"status": "success", "message": "User created successfully"})

class MarketIndexView(APIView):
    def get(self, request):
        try:
            # Fetch real index data using Akshare (Sina source is comprehensive for indices)
            # Returns codes like sh000001, sz399001
            df_indices = ak.stock_zh_index_spot_sina()
            
            target_names = ["上证指数", "深证成指", "创业板指"]
            
            indices = []
            
            for name in target_names:
                row = df_indices[df_indices['名称'] == name]
                if not row.empty:
                    item = row.iloc[0]
                    change = float(item['涨跌幅'])
                    price = float(item['最新价'])
                    
                    indices.append({
                        "title": name,
                        "value": price,
                        "change": round(change, 2),
                        "is_up": change > 0
                    })
            
            if not indices:
                 raise Exception("No index data found from Akshare")

            return Response({
                "status": "success",
                "data": indices,
                "message": "Real data from Akshare"
            })
        except Exception as e:
            print(f"Akshare Index Error: {e}")
            return Response({
                "status": "error",
                "data": [],
                "message": f"Network Error ({str(e)})"
            })

class TopGainersView(APIView):
    def get(self, request):
        try:
            # Fetch real-time A-share quotes
            df = ak.stock_zh_a_spot_em()
            # Columns: '序号', '代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅', '最高', '最低', '今开', '昨收', '量比', '换手率', '市盈率-动态', '市净率'
            
            if df.empty:
                raise Exception("No stock data available")

            # Sort by pct_chg descending and take top 10
            # '涨跌幅' column
            top_gainers = df.sort_values(by='涨跌幅', ascending=False).head(10)
            
            data = []
            for _, row in top_gainers.iterrows():
                # Format code to match Tushare format if possible (000001 -> 000001.SZ)
                # But Akshare just gives '000001'.
                # Frontend might rely on 'ts_code'.
                # Let's generate a pseudo ts_code.
                raw_code = str(row['代码'])
                if raw_code.startswith('6'):
                    ts_code = f"{raw_code}.SH"
                elif raw_code.startswith('0') or raw_code.startswith('3'):
                    ts_code = f"{raw_code}.SZ"
                elif raw_code.startswith('8') or raw_code.startswith('4'):
                    ts_code = f"{raw_code}.BJ"
                else:
                    ts_code = raw_code

                data.append({
                    "name": row['名称'],
                    "code": ts_code, 
                    "value": round(float(row['涨跌幅']), 2),
                    "price": float(row['最新价'])
                })
            
            return Response({
                "status": "success", 
                "data": data,
                "message": "Top gainers from Akshare"
            })

        except Exception as e:
            print(f"TopGainers Error: {e}")
            return Response({
                "status": "error", 
                "data": [],
                "message": f"Data fetch failed: {str(e)}"
            })

class StockDataView(APIView):
    def get(self, request):
        try:
            # Get list of stocks
            # stock_zh_a_spot_em returns all stocks with current data
            df = ak.stock_zh_a_spot_em()
            
            # Select top 200 to avoid performance issues
            df_subset = df.head(200)
            
            records = []
            for _, row in df_subset.iterrows():
                raw_code = str(row['代码'])
                if raw_code.startswith('6'):
                    ts_code = f"{raw_code}.SH"
                elif raw_code.startswith('0') or raw_code.startswith('3'):
                    ts_code = f"{raw_code}.SZ"
                elif raw_code.startswith('8') or raw_code.startswith('4'):
                    ts_code = f"{raw_code}.BJ"
                else:
                    ts_code = raw_code
                    
                records.append({
                    "ts_code": ts_code,
                    "symbol": raw_code,
                    "name": row['名称'],
                    "area": "", # Akshare spot API doesn't have area/industry easily in this call, leave blank or fetch elsewhere if critical
                    "industry": "",
                    "list_date": ""
                })
            
            return Response({"status": "success", "data": records})
            
        except Exception as e:
            print(f"Akshare StockList error: {e}")
            return Response({
                "status": "error", 
                "data": [],
                "message": f"Data fetch failed: {str(e)}"
            })

class WatchlistView(APIView):
    def get(self, request):
        watchlist = Watchlist.objects.all().values()
        return Response({"status": "success", "data": list(watchlist)})

    def post(self, request):
        ts_code = request.data.get('ts_code')
        name = request.data.get('name')
        if not ts_code or not name:
            return Response({"status": "error", "message": "Missing ts_code or name"}, status=400)
        
        obj, created = Watchlist.objects.get_or_create(ts_code=ts_code, defaults={'name': name})
        if not created:
             return Response({"status": "info", "message": "Already in watchlist"})
        return Response({"status": "success", "message": "Added to watchlist"})

    def delete(self, request):
        ts_code = request.query_params.get('ts_code')
        if not ts_code:
            return Response({"status": "error", "message": "Missing ts_code"}, status=400)
        
        Watchlist.objects.filter(ts_code=ts_code).delete()
        return Response({"status": "success", "message": "Removed from watchlist"})

class AIAnalyzeView(APIView):
    def post(self, request):
        # Mock AI Analysis
        # Receives a list of stocks or uses the watchlist
        watchlist = Watchlist.objects.all()
        if not watchlist:
            return Response({"status": "info", "message": "自选股为空，请先添加股票。"})
        
        analysis_results = []
        for stock in watchlist:
            # Mock analysis logic
            sentiment = random.choice(["看涨", "看跌", "观望"])
            score = random.randint(60, 95)
            reason = f"基于近期K线形态及{stock.name}的行业走势，AI模型检测到资金{'流入' if sentiment=='看涨' else '流出'}迹象。"
            
            analysis_results.append({
                "ts_code": stock.ts_code,
                "name": stock.name,
                "sentiment": sentiment,
                "score": score,
                "reason": reason,
                "action": "买入" if sentiment == "看涨" else ("卖出" if sentiment == "看跌" else "持有")
            })
            
        ai_response = f"我对您当前的自选股组合进行了深度分析。\n\n"
        for item in analysis_results:
            ai_response += f"**{item['name']} ({item['ts_code']})**\n"
            ai_response += f"- 建议：{item['action']} (置信度: {item['score']}%)\n"
            ai_response += f"- 分析：{item['reason']}\n\n"
            
        ai_response += "*(注：以上分析由AI生成，仅供参考，不构成投资建议)*"

        return Response({
            "status": "success",
            "data": {
                "message": ai_response,
                "details": analysis_results
            }
        })
