from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import Watchlist, AIAnalysisLog, UserProfile, WatchlistGroup
from .serializers import AIAnalysisLogSerializer, UserSerializer, ChangePasswordSerializer, WatchlistGroupSerializer
from rest_framework import viewsets, generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
import random
import datetime
import akshare as ak
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Helper functions for caching heavy data
def get_cached_stock_data():
    data = cache.get('full_stock_data')
    if data is not None and not data.empty:
        return data
    print("Fetching full stock data from Akshare...")
    try:
        df = ak.stock_zh_a_spot_em()
        cache.set('full_stock_data', df, 60) # Cache for 60s
        return df
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return pd.DataFrame()

def get_cached_etf_data():
    data = cache.get('full_etf_data')
    if data is not None and not data.empty:
        return data
    print("Fetching full ETF data from Akshare...")
    try:
        df = ak.fund_etf_spot_em()
        cache.set('full_etf_data', df, 60)
        return df
    except Exception as e:
        print(f"Error fetching ETF data: {e}")
        return pd.DataFrame()

class UserInfoView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        # Ensure profile exists
        UserProfile.objects.get_or_create(user_id=self.request.user.id)
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Allow partial update
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.data.get('old_password')):
                user.set_password(serializer.data.get('new_password'))
                user.save()
                return Response({'status': 'success', 'message': 'Password updated successfully'})
            return Response({'status': 'error', 'message': 'Incorrect old password'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AIAnalysisLogViewSet(viewsets.ModelViewSet):
    queryset = AIAnalysisLog.objects.all()
    serializer_class = AIAnalysisLogSerializer
    permission_classes = [AllowAny]

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({"status": "error", "message": "Username and password are required"}, status=400)
        
        # Password strength validation
        if len(password) < 6:
            return Response({"status": "error", "message": "密码长度不能少于6位"}, status=400)
        if not any(char.isdigit() for char in password) or not any(char.isalpha() for char in password):
            return Response({"status": "error", "message": "密码需包含字母和数字"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"status": "error", "message": "Username already exists"}, status=400)
        
        try:
            user = User.objects.create(
                username=username,
                password=make_password(password)
            )
            
            # Create token for auto login
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "status": "success", 
                "message": "User created successfully",
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

class MarketIndexView(APIView):
    def get(self, request):
        # Try to get from cache first
        cached_data = cache.get('market_index_data')
        if cached_data:
            return Response({
                "status": "success",
                "data": cached_data,
                "message": "Cached data"
            })

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
                    try:
                        change_abs = float(item['涨跌额'])
                    except Exception:
                        change_abs = round(price * change / 100, 2)
                    
                    indices.append({
                        "title": name,
                        "value": price,
                        "change": round(change, 2),
                        "change_abs": round(change_abs, 2),
                        "is_up": change > 0
                    })
            
            if not indices:
                 raise Exception("No index data found from Akshare")

            # Cache for 60 seconds
            cache.set('market_index_data', indices, 60)

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
        cached_data = cache.get('top_gainers_data')
        if cached_data:
            return Response({
                "status": "success", 
                "data": cached_data,
                "message": "Cached data"
            })

        try:
            # Fetch real-time A-share quotes
            df = get_cached_stock_data()
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

                # Helper to safely get float
                def get_float(val):
                    try:
                        if pd.isna(val): return 0.0
                        return float(val)
                    except:
                        return 0.0

                data.append({
                    "name": row['名称'],
                    "code": ts_code, 
                    "value": round(get_float(row['涨跌幅']), 2),
                    "price": get_float(row['最新价'])
                })
            
            # Cache for 60 seconds
            cache.set('top_gainers_data', data, 60)

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

class TopIndustriesView(APIView):
    def get(self, request):
        cached_data = cache.get('top_industries_data')
        if cached_data:
            return Response({
                "status": "success",
                "data": cached_data,
                "message": "Cached data"
            })

        try:
            # Use correct function for industry board summary
            df = ak.stock_board_industry_name_em()
            if df.empty:
                raise Exception("No industry data available")

            top_industries = df.sort_values(by='涨跌幅', ascending=False).head(10)

            data = []
            for _, row in top_industries.iterrows():
                # Helper to safely get float
                def get_float(val):
                    try:
                        if pd.isna(val): return 0.0
                        return float(val)
                    except:
                        return 0.0

                data.append({
                    "name": row['板块名称'],
                    "code": row['板块代码'],
                    "value": round(get_float(row['涨跌幅']), 2),
                    "market_cap": get_float(row['总市值'])
                })

            # Cache for 60 seconds
            cache.set('top_industries_data', data, 60)

            return Response({
                "status": "success",
                "data": data,
                "message": "Top industries from Akshare"
            })
        except Exception as e:
            print(f"TopIndustries Error: {e}")
            return Response({
                "status": "error",
                "data": [],
                "message": f"Data fetch failed: {str(e)}"
            })

class StockDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        
        # Optimization: If query is a symbol (6 digits), use specific API
        if query and query.isdigit() and len(query) == 6:
            try:
                # Use stock_individual_info_em for detailed info
                timeout_param = request.query_params.get('timeout')
                try:
                    timeout_val = float(timeout_param) if timeout_param is not None else None
                except:
                    timeout_val = None
                df_info = ak.stock_individual_info_em(symbol=query, timeout=timeout_val)
                
                # Convert to dict
                info_dict = {}
                for _, row in df_info.iterrows():
                    info_dict[row['item']] = row['value']
                
                # Determine suffix
                raw_code = query
                if raw_code.startswith(('6', '9', '5')):
                    ts_code = f"{raw_code}.SH"
                elif raw_code.startswith(('0', '2', '3', '1')):
                    ts_code = f"{raw_code}.SZ"
                elif raw_code.startswith(('8', '4')):
                    ts_code = f"{raw_code}.BJ"
                else:
                    ts_code = raw_code
                
                # Construct record
                # Note: Some real-time fields might be missing in this API, using defaults or available fields
                record = {
                    "ts_code": ts_code,
                    "symbol": raw_code,
                    "name": info_dict.get('股票简称', ''),
                    "price": info_dict.get('最新', 0),
                    "change_pct": 0, # This API does not provide change percentage
                    "volume": 0, # This API does not provide volume
                    "turnover_rate": 0, 
                    "pe": 0,
                    "market_cap": info_dict.get('总市值', 0),
                    # Extra fields from individual info
                    "total_shares": info_dict.get('总股本', 0),
                    "circulating_shares": info_dict.get('流通股', 0),
                    "industry": info_dict.get('行业', ''),
                    "listing_date": info_dict.get('上市时间', ''),
                    "circulating_market_cap": info_dict.get('流通市值', 0)
                }
                
                return Response({"status": "success", "data": [record]})
                
            except Exception as e:
                print(f"Individual info fetch failed for {query}: {e}")
                # Fallback to general search if specific fetch fails
        
        try:
            # Parallel fetch for Stock and ETF data
            df_stocks = pd.DataFrame()
            df_etfs = pd.DataFrame()
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_stocks = executor.submit(get_cached_stock_data)
                future_etfs = executor.submit(get_cached_etf_data)
                
                df_stocks = future_stocks.result()
                df_etfs = future_etfs.result()
            
            # Prepare columns
            stock_cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '市盈率-动态', '总市值']
            etf_cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '总市值']
            
            # Normalize Stock DF
            df_s = df_stocks[stock_cols].copy()
            df_s.rename(columns={'市盈率-动态': 'pe'}, inplace=True)
            
            # Normalize ETF DF
            if not df_etfs.empty:
                # Ensure columns exist (sometimes API changes)
                available_etf_cols = [c for c in etf_cols if c in df_etfs.columns]
                df_e = df_etfs[available_etf_cols].copy()
                df_e['pe'] = None
                # Filter out empty or all-NA columns before concat to avoid FutureWarning
                df_e = df_e.dropna(axis=1, how='all')
                if df_e.empty:
                     df = df_s
                else:
                    df = pd.concat([df_s, df_e], ignore_index=True)
            else:
                df = df_s

            # Filter by query if present
            if query:
                # Filter by code or name
                # Ensure columns are string
                df['代码'] = df['代码'].astype(str)
                df['名称'] = df['名称'].astype(str)
                df = df[df['代码'].str.contains(query, case=False) | df['名称'].str.contains(query, case=False)]
            
            # Return all stocks so frontend can filter/search locally or display full list
            # The payload is roughly 1-2MB which is acceptable for modern networks
            df_subset = df
            
            # Replace NaN with None for valid JSON serialization
            # Note: df.where(pd.notnull(df), None) might not work for all types
            # Use explicit replacement
            df_subset = df_subset.replace({pd.NA: None, float('nan'): None})
            # Also handle numpy nan
            import numpy as np
            df_subset = df_subset.replace({np.nan: None})
            
            records = []
            for _, row in df_subset.iterrows():
                raw_code = str(row['代码'])
                if raw_code.startswith('6') or raw_code.startswith('9') or raw_code.startswith('5'):
                    ts_code = f"{raw_code}.SH"
                elif raw_code.startswith('0') or raw_code.startswith('2') or raw_code.startswith('3') or raw_code.startswith('1'):
                    ts_code = f"{raw_code}.SZ"
                elif raw_code.startswith('8') or raw_code.startswith('4'):
                    ts_code = f"{raw_code}.BJ"
                else:
                    ts_code = raw_code
                
                # Helper to safely get value or None
                def get_val(val):
                    if pd.isna(val): return None
                    return val

                records.append({
                    "ts_code": ts_code,
                    "symbol": raw_code,
                    "name": row['名称'],
                    "price": get_val(row['最新价']),
                    "change_pct": get_val(row['涨跌幅']),
                    "volume": get_val(row['成交量']),
                    "turnover_rate": get_val(row['换手率']),
                    "pe": get_val(row.get('pe')), 
                    "market_cap": get_val(row['总市值'])
                })
            
            return Response({"status": "success", "data": records})
            
        except Exception as e:
            print(f"Akshare StockList error: {e}")
            return Response({
                "status": "error", 
                "data": [],
                "message": f"Data fetch failed: {str(e)}"
            })

class WatchlistGroupViewSet(viewsets.ModelViewSet):
    serializer_class = WatchlistGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WatchlistGroup.objects.filter(user_id=self.request.user.id)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.id)

# Helper function to fetch single stock data
def fetch_single_stock_data(ts_code):
    try:
        # ts_code format: 000001.SZ -> 000001
        symbol = ts_code.split('.')[0]
        
        # Check if ETF (Starts with 51, 56, 58, 15, 16)
        is_etf = symbol.startswith(('51', '56', '58', '15', '16'))
        
        data = {
            "ts_code": ts_code,
            "name": "",
            "price": 0,
            "change_pct": 0,
            "volume": 0,
            "turnover_rate": 0,
            "pe": 0,
            "market_cap": 0,
            "success": False
        }

        if is_etf:
            # Use ETF History for latest snapshot (works for single ETF)
            try:
                df = ak.fund_etf_hist_em(symbol=symbol, period='daily', start_date='20240101', adjust='qfq')
                if not df.empty:
                    last_row = df.iloc[-1]
                    data.update({
                        "price": last_row['收盘'],
                        "change_pct": last_row['涨跌幅'],
                        "volume": last_row['成交量'], # This might be in lots or shares? Usually volume
                        "turnover_rate": last_row['换手率'],
                        "success": True
                    })
                    # Name is not in hist, but we might have it in watchlist name or need another call
                    # For now, let's rely on watchlist name or user-saved name if possible?
                    # Actually Watchlist model has 'name'. But enriched data overrides it? 
                    # The WatchlistView uses enriched data if available.
                    # We should try to preserve the name from Watchlist if API doesn't give it.
            except Exception as e:
                print(f"ETF fetch failed for {ts_code}: {e}")
                return {"ts_code": ts_code, "success": False}
        else:
            # Use Stock Bid/Ask for Stocks (Realtime)
            try:
                df = ak.stock_bid_ask_em(symbol=symbol)
                # df columns: item, value
                info_map = dict(zip(df['item'], df['value']))
                
                data.update({
                    "price": info_map.get('最新', 0),
                    "change_pct": info_map.get('涨幅', 0),
                    "volume": info_map.get('总手', 0),
                    "turnover_rate": info_map.get('换手', 0),
                    # PE is not available in bid_ask, accept 0 or missing
                    "success": True
                })
            except Exception as e:
                print(f"Stock fetch failed for {ts_code}: {e}")
                # Fallback to history if bid/ask fails
                try:
                    df_hist = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20240101", adjust="qfq")
                    if not df_hist.empty:
                        last_row = df_hist.iloc[-1]
                        data.update({
                            "price": last_row['收盘'],
                            "change_pct": last_row['涨跌幅'],
                            "volume": last_row['成交量'],
                            "turnover_rate": last_row['换手率'],
                            "success": True
                        })
                except:
                    return {"ts_code": ts_code, "success": False}
        
        return data

    except Exception as e:
        print(f"General fetch error for {ts_code}: {e}")
        return {"ts_code": ts_code, "success": False}

class WatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group_id = request.query_params.get('group_id')
        queryset = Watchlist.objects.filter(user_id=request.user.id)
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        else:
            queryset = queryset.filter(group__isnull=True)
            
        watchlist_items = list(queryset.values())
        
        if not watchlist_items:
             return Response({"status": "success", "data": []})

        # Fetch real-time data to enrich the watchlist
        enriched_data = []
        
        # Strategy: 
        # If items < 20, use parallel individual fetch (faster for small lists).
        # If items >= 20, use full list fetch (efficient for large lists).
        if len(watchlist_items) < 20:
            ts_codes = [item['ts_code'] for item in watchlist_items]
            results_map = {}
            
            with ThreadPoolExecutor(max_workers=min(len(ts_codes), 20)) as executor:
                # Map future to ts_code
                future_to_code = {executor.submit(fetch_single_stock_data, code): code for code in ts_codes}
                
                for future in as_completed(future_to_code):
                    data = future.result()
                    if data.get('success'):
                        results_map[data['ts_code']] = data
            
            # Merge results
            for item in watchlist_items:
                ts_code = item['ts_code']
                if ts_code in results_map:
                    stock_data = results_map[ts_code]
                    item.update({
                        "price": stock_data['price'],
                        "change_pct": stock_data['change_pct'], # Note: individual API might lack this
                        "volume": stock_data['volume'],
                        "turnover_rate": stock_data['turnover_rate'],
                        "pe": stock_data['pe'],
                        "market_cap": stock_data['market_cap']
                    })
                else:
                    # Failed to fetch, keep as None or 0
                    pass
                enriched_data.append(item)
                
            return Response({"status": "success", "data": enriched_data})

        # Fallback to Full List Fetch for larger lists
        try:
            # Parallel fetch for Stock and ETF data
            # User requested multithreading for performance
            df_stocks = pd.DataFrame()
            df_etfs = pd.DataFrame()
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_stocks = executor.submit(get_cached_stock_data)
                future_etfs = executor.submit(get_cached_etf_data)
                
                # Wait for both to complete
                df_stocks = future_stocks.result()
                df_etfs = future_etfs.result()

            # Prepare columns
            stock_cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '市盈率-动态', '总市值']
            etf_cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '总市值']
            
            # Normalize Stock DF
            df_s = df_stocks[stock_cols].copy()
            df_s.rename(columns={'市盈率-动态': 'pe'}, inplace=True)
            
            # Normalize ETF DF
            if not df_etfs.empty:
                available_etf_cols = [c for c in etf_cols if c in df_etfs.columns]
                df_e = df_etfs[available_etf_cols].copy()
                df_e['pe'] = None
                # Filter out empty or all-NA columns before concat to avoid FutureWarning
                df_e = df_e.dropna(axis=1, how='all')
                if df_e.empty:
                    df = df_s
                else:
                    df = pd.concat([df_s, df_e], ignore_index=True)
            else:
                df = df_s
            
            stock_map = {}
            for _, row in df.iterrows():
                raw_code = str(row['代码'])
                # Convert to ts_code format
                if raw_code.startswith(('6', '9', '5')):
                    ts_code = f"{raw_code}.SH"
                elif raw_code.startswith(('0', '2', '3', '1')):
                    ts_code = f"{raw_code}.SZ"
                elif raw_code.startswith(('8', '4')):
                    ts_code = f"{raw_code}.BJ"
                else:
                    ts_code = raw_code
                
                stock_map[ts_code] = row

            for item in watchlist_items:
                ts_code = item['ts_code']
                # Replace NaN with None for valid JSON serialization
                if ts_code in stock_map:
                    row = stock_map[ts_code]
                    
                    def get_val(val):
                        if pd.isna(val): return None
                        return val

                    item.update({
                        "price": get_val(row['最新价']),
                        "change_pct": get_val(row['涨跌幅']),
                        "volume": get_val(row['成交量']),
                        "turnover_rate": get_val(row['换手率']),
                        "pe": get_val(row.get('pe')),
                        "market_cap": get_val(row['总市值'])
                    })
                else:
                    item.update({
                        "price": None,
                        "change_pct": None,
                        "volume": None,
                        "turnover_rate": None,
                        "pe": None,
                        "market_cap": None
                    })
                enriched_data.append(item)
                
        except Exception as e:
            print(f"Error fetching realtime data for watchlist: {e}")
            # Fallback to DB data
            enriched_data = watchlist_items

        return Response({"status": "success", "data": enriched_data})

    def post(self, request):
        ts_code = request.data.get('ts_code')
        name = request.data.get('name')
        group_id = request.data.get('group_id')
        
        if not ts_code or not name:
            return Response({"status": "error", "message": "Missing ts_code or name"}, status=400)
        
        group = None
        if group_id:
            try:
                group = WatchlistGroup.objects.get(id=group_id, user_id=request.user.id)
            except WatchlistGroup.DoesNotExist:
                return Response({"status": "error", "message": "Invalid group_id"}, status=400)

        # Check if already exists in this group (or in null group)
        exists = Watchlist.objects.filter(
            ts_code=ts_code, 
            user_id=request.user.id,
            group=group
        ).exists()
        
        if exists:
             return Response({"status": "info", "message": "Already in this watchlist group"})

        Watchlist.objects.create(
            ts_code=ts_code, 
            user_id=request.user.id,
            name=name,
            group=group
        )
        return Response({"status": "success", "message": "Added to watchlist"})

    def delete(self, request):
        ts_code = request.query_params.get('ts_code')
        group_id = request.query_params.get('group_id') # Optional, specific to group
        
        if not ts_code:
            return Response({"status": "error", "message": "Missing ts_code"}, status=400)
        
        qs = Watchlist.objects.filter(ts_code=ts_code, user_id=request.user.id)
        if group_id:
            qs = qs.filter(group_id=group_id)
        else:
            qs = qs.filter(group__isnull=True) # Default if no group specified
            
        qs.delete()
        return Response({"status": "success", "message": "Removed from watchlist"})

class AIAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Mock AI Analysis
        # Receives a list of stocks or uses the watchlist
        watchlist = Watchlist.objects.filter(user_id=request.user.id)
        if not watchlist:
            return Response({"status": "info", "message": "自选股为空，请先添加股票。"})
        
        # Get user preferred model
        ai_model = 'DeepSeek-V3'
        # Manual lookup since relation is gone
        profile = UserProfile.objects.filter(user_id=request.user.id).first()
        if profile and profile.ai_model:
            ai_model = profile.ai_model

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
            
        ai_response = f"我对您当前的自选股组合进行了深度分析（基于模型: {ai_model}）。\n\n"
        for item in analysis_results:
            ai_response += f"**{item['name']} ({item['ts_code']})**\n"
            ai_response += f"- 建议：{item['action']} (置信度: {item['score']}%)\n"
            ai_response += f"- 分析：{item['reason']}\n\n"
            
        ai_response += "*(注：以上分析由AI生成，仅供参考，不构成投资建议)*"

        # Save to DB
        try:
            # We can save a summary log or individual logs per stock
            # Here we save a summary log for simplicity, or we could save individual ones.
            # Let's save a "Portfolio Analysis" log entry.
            AIAnalysisLog.objects.create(
                ts_code="PORTFOLIO",
                stock_name="自选股组合",
                analysis_content=ai_response
            )
        except Exception as e:
            print(f"Failed to save AI log: {e}")

        return Response({
            "status": "success",
            "data": {
                "message": ai_response,
                "details": analysis_results
            }
        })
