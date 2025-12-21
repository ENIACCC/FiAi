from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import Watchlist, AIAnalysisLog, AIModelConfig, UserProfile, WatchlistGroup, Event
from .serializers import AIAnalysisLogSerializer, AIModelConfigSerializer, UserSerializer, ChangePasswordSerializer, WatchlistGroupSerializer, EventSerializer
from rest_framework import viewsets, generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
import random
import datetime
import akshare as ak
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db.models import Count
import requests
from django.utils.dateparse import parse_datetime

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

class AIProviderError(Exception):
    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

def deepseek_chat_completion(api_key: str, base_url: str, model: str, messages: list, temperature: float = 0.2, max_tokens: int = 2048) -> str:
    url = (base_url or "https://api.deepseek.com").rstrip("/") + "/chat/completions"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    if resp.status_code >= 400:
        if resp.status_code in (401, 403):
            raise AIProviderError(code="invalid_api_key", message="AI 鉴权失败，请检查 API Key 是否正确", status_code=resp.status_code)
        if resp.status_code == 429:
            raise AIProviderError(code="rate_limited", message="AI 服务请求过于频繁，请稍后重试", status_code=resp.status_code)
        if resp.status_code >= 500:
            raise AIProviderError(code="provider_error", message="AI 服务暂时不可用，请稍后重试", status_code=resp.status_code)
        raise AIProviderError(code="provider_error", message=f"AI 服务返回错误 (HTTP {resp.status_code})", status_code=resp.status_code)
    data = resp.json()
    return data["choices"][0]["message"]["content"]

def _get_user_ai_config(user_id: int):
    profile, _ = UserProfile.objects.get_or_create(user_id=user_id)
    cfg = None
    if getattr(profile, "active_ai_model_id", None):
        cfg = AIModelConfig.objects.filter(id=profile.active_ai_model_id, user_id=user_id).first()
    provider = (cfg.provider if cfg and cfg.provider else profile.ai_provider or "deepseek")
    base_url = (cfg.base_url if cfg and cfg.base_url else profile.ai_base_url or "https://api.deepseek.com")
    model = (cfg.model if cfg and cfg.model else profile.ai_model or "deepseek-chat")
    api_key = (cfg.api_key if cfg and cfg.api_key else profile.ai_api_key)
    return {"provider": provider, "base_url": base_url, "model": model, "api_key": api_key, "active_id": getattr(profile, "active_ai_model_id", None)}

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

class AIModelConfigsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user_id=request.user.id)
        qs = AIModelConfig.objects.filter(user_id=request.user.id).order_by("-updated_at")[:100]
        return Response(
            {
                "status": "success",
                "data": {
                    "active_ai_model_id": profile.active_ai_model_id,
                    "items": AIModelConfigSerializer(qs, many=True).data,
                },
            }
        )

    def post(self, request):
        provider = (request.data.get("provider") or "deepseek").strip()
        base_url = (request.data.get("base_url") or "https://api.deepseek.com").strip()
        model = (request.data.get("model") or "deepseek-chat").strip()
        api_key = request.data.get("api_key")
        set_active = request.data.get("set_active", True)

        if api_key is None:
            return Response({"status": "error", "message": "API Key 不能为空"}, status=400)
        api_key = str(api_key).strip()
        if not api_key:
            return Response({"status": "error", "message": "API Key 不能为空"}, status=400)
        profile, _ = UserProfile.objects.get_or_create(user_id=request.user.id)

        cfg, created = AIModelConfig.objects.get_or_create(
            user_id=request.user.id,
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
        )

        if set_active:
            profile.active_ai_model_id = cfg.id
            profile.ai_provider = cfg.provider
            profile.ai_base_url = cfg.base_url
            profile.ai_model = cfg.model
            profile.ai_api_key = api_key
            profile.save()

        resp_payload = {"data": AIModelConfigSerializer(cfg).data}
        if created:
            return Response({"status": "success", **resp_payload}, status=201)
        return Response(
            {
                "status": "info",
                "code": "duplicate",
                "message": "该模型配置已存在，请勿重复添加",
                **resp_payload,
            },
            status=200,
        )

class AIModelConfigDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, cfg_id):
        cfg = AIModelConfig.objects.filter(id=cfg_id, user_id=request.user.id).first()
        if not cfg:
            return Response({"status": "error", "message": "Not found"}, status=404)
        profile, _ = UserProfile.objects.get_or_create(user_id=request.user.id)
        was_active = bool(profile.active_ai_model_id and str(profile.active_ai_model_id) == str(cfg.id))
        cfg.delete()

        if was_active:
            next_cfg = AIModelConfig.objects.filter(user_id=request.user.id).order_by("-updated_at").first()
            if next_cfg:
                profile.active_ai_model_id = next_cfg.id
                profile.ai_provider = next_cfg.provider
                profile.ai_base_url = next_cfg.base_url
                profile.ai_model = next_cfg.model
                profile.ai_api_key = next_cfg.api_key
            else:
                profile.active_ai_model_id = None
                profile.ai_api_key = None
            profile.save()

        return Response({"status": "success"})

class AIModelConfigSelectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cfg_id):
        cfg = AIModelConfig.objects.filter(id=cfg_id, user_id=request.user.id).first()
        if not cfg:
            return Response({"status": "error", "message": "Not found"}, status=404)
        profile, _ = UserProfile.objects.get_or_create(user_id=request.user.id)
        profile.active_ai_model_id = cfg.id
        profile.ai_provider = cfg.provider
        profile.ai_base_url = cfg.base_url
        profile.ai_model = cfg.model
        if getattr(cfg, "api_key", None):
            profile.ai_api_key = cfg.api_key
        profile.save()
        return Response({"status": "success"})

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

class WatchlistCountView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_id = request.user.id
        default_count = Watchlist.objects.filter(user_id=user_id, group__isnull=True).count()
        # Build group counts
        group_counts = {}
        for g in WatchlistGroup.objects.filter(user_id=user_id):
            group_counts[str(g.id)] = Watchlist.objects.filter(user_id=user_id, group_id=g.id).count()
        return Response({
            "status": "success",
            "data": {
                "default": default_count,
                "groups": group_counts
            }
        })

# Helper function to fetch single stock data
def fetch_single_stock_data(ts_code):
    try:
        # ts_code format: 000001.SZ -> 000001
        symbol = ts_code.split('.')[0]
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
        # If items < 20, use parallel individual fetch for stocks + single batch for ETFs.
        # If items >= 20, use full list fetch (efficient for large lists).
        if len(watchlist_items) < 20:
            ts_codes = [item['ts_code'] for item in watchlist_items]
            results_map = {}

            # Split into ETF and Stock symbols
            stock_symbols = []
            etf_symbols = []
            for code in ts_codes:
                sym = code.split('.')[0]
                if sym.startswith(('51', '56', '58', '15', '16', '159')):
                    etf_symbols.append(sym)
                else:
                    stock_symbols.append(code)

            # Batch fetch ETFs once
            if etf_symbols:
                try:
                    df_etf_spot = ak.fund_etf_spot_em()
                    if not df_etf_spot.empty:
                        for sym in etf_symbols:
                            row = df_etf_spot[df_etf_spot['代码'] == sym]
                            if not row.empty:
                                r = row.iloc[0]
                                ts = f"{sym}.SZ" if sym.startswith(('15','16','159')) else f"{sym}.SH"
                                results_map[ts] = {
                                    "price": r.get('最新价', 0),
                                    "change_pct": r.get('涨跌幅', 0),
                                    "volume": r.get('成交量', 0),
                                    "turnover_rate": r.get('换手率', 0),
                                    "pe": None,
                                    "market_cap": r.get('总市值', 0),
                                    "name": r.get('名称', ''),
                                    "success": True
                                }
                except Exception as e:
                    print(f"ETF spot fetch failed: {e}")
            
            # Only spawn threads when there are stock symbols to fetch
            if stock_symbols:
                with ThreadPoolExecutor(max_workers=min(len(stock_symbols), 20)) as executor:
                    # Map future to ts_code
                    future_to_code = {executor.submit(fetch_single_stock_data, code): code for code in stock_symbols}
                    
                    for future in as_completed(future_to_code):
                        data = future.result()
                        if data.get('success'):
                            results_map[data['ts_code']] = data
            
            # Merge results
            for item in watchlist_items:
                ts_code = item['ts_code']
                if ts_code in results_map:
                    stock_data = results_map[ts_code]
                    merged = {
                        "price": stock_data['price'],
                        "change_pct": stock_data['change_pct'], # Note: individual API might lack this
                        "volume": stock_data['volume'],
                        "turnover_rate": stock_data['turnover_rate'],
                        "pe": stock_data['pe'],
                        "market_cap": stock_data['market_cap']
                    }
                    if stock_data.get('name'):
                        merged["name"] = stock_data['name']
                    item.update(merged)
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
             return Response({"status": "info", "message": "已在该分组中"})

        Watchlist.objects.create(
            ts_code=ts_code, 
            user_id=request.user.id,
            name=name,
            group=group
        )
        return Response({"status": "success", "message": "已添加到自选"})

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
        return Response({"status": "success", "message": "已从自选移除"})

class AIAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        group_id = request.data.get('group_id')
        qs = Watchlist.objects.filter(user_id=request.user.id)
        if group_id:
            qs = qs.filter(group_id=group_id)
        else:
            qs = qs.filter(group__isnull=True)
        watchlist = list(qs)
        if not watchlist:
            return Response({"status": "info", "message": "自选股为空，请先添加股票。"})
        
        cfg = _get_user_ai_config(request.user.id)
        ai_model = cfg["model"]
        ai_base_url = cfg["base_url"]
        api_key = cfg["api_key"]

        if not api_key:
            return Response({
                "status": "error",
                "code": "missing_api_key",
                "message": "未配置 AI API Key"
            })
            
        group_name = "默认分组" if not group_id else (WatchlistGroup.objects.filter(id=group_id, user_id=request.user.id).first() or WatchlistGroup(name="当前分组")).name
        stock_lines = "\n".join([f"- {s.name} ({s.ts_code})" for s in watchlist])
        prompt = (
            f"请用中文对我的自选股分组「{group_name}」做一份简洁但有用的分析。\n\n"
            f"自选股清单：\n{stock_lines}\n\n"
            "要求：\n"
            "1) 输出 Markdown\n"
            "2) 逐只股票给出：短期观点、关键价位(支撑/压力)、风险点、操作建议(买入/卖出/观望)与理由\n"
            "3) 最后给出组合层面的结论与风险提示\n"
            "4) 不要编造不存在的数据来源，若缺少数据请明确说明基于常识与一般性技术面框架\n"
        )
        try:
            ai_response = deepseek_chat_completion(
                api_key=api_key,
                base_url=ai_base_url,
                model=ai_model,
                messages=[
                    {"role": "system", "content": "你是一个谨慎、专业的中文投资助手。你提供的信息仅供参考，不构成投资建议。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
        except Exception as e:
            if isinstance(e, AIProviderError):
                return Response({"status": "error", "code": e.code, "message": e.message}, status=200)
            return Response({"status": "error", "code": "ai_call_failed", "message": "AI 服务暂时不可用，请稍后重试"}, status=200)

        # Save to DB
        try:
            # We can save a summary log or individual logs per stock
            # Here we save a summary log for simplicity, or we could save individual ones.
            # Let's save a "Portfolio Analysis" log entry.
            AIAnalysisLog.objects.create(
                ts_code="PORTFOLIO",
                stock_name=f"自选股 - {group_name}",
                analysis_content=ai_response
            )
        except Exception as e:
            print(f"Failed to save AI log: {e}")

        return Response({
            "status": "success",
            "data": {
                "message": ai_response,
                "details": []
            }
        })

class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cfg = _get_user_ai_config(request.user.id)
        ai_model = cfg["model"]
        ai_base_url = cfg["base_url"]
        api_key = cfg["api_key"]

        if not api_key:
            return Response({
                "status": "error",
                "code": "missing_api_key",
                "message": "未配置 AI API Key"
            })

        messages = request.data.get('messages') or []
        stock = request.data.get('stock')

        system_content = "你是一个谨慎、专业的中文投资助手。你提供的信息仅供参考，不构成投资建议。"
        if stock:
            stock_name = stock.get('name') if isinstance(stock, dict) else None
            stock_code = None
            if isinstance(stock, dict):
                stock_code = stock.get('ts_code') or stock.get('symbol') or stock.get('code')
            if stock_name or stock_code:
                system_content = system_content + f"\n当前讨论标的：{stock_name or ''} {f'({stock_code})' if stock_code else ''}".strip()

        try:
            content = deepseek_chat_completion(
                api_key=api_key,
                base_url=ai_base_url,
                model=ai_model,
                messages=[{"role": "system", "content": system_content}] + messages,
                temperature=0.3,
                max_tokens=1024,
            )
        except Exception as e:
            if isinstance(e, AIProviderError):
                return Response({"status": "error", "code": e.code, "message": e.message}, status=200)
            return Response({"status": "error", "code": "ai_call_failed", "message": "AI 服务暂时不可用，请稍后重试"}, status=200)

        return Response({"status": "success", "data": {"message": content}})


def _compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _compute_atr_pct(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(window=window, min_periods=window).mean()
    return (atr / close.replace(0, pd.NA)) * 100


def _ema(series: pd.Series, span: int) -> pd.Series:
    s = series.astype(float)
    return s.ewm(span=span, adjust=False, min_periods=span).mean()


def _compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    dif = _ema(close, span=fast) - _ema(close, span=slow)
    dea = dif.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = dif - dea
    return dif, dea, hist


def _compute_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    llv = low.rolling(window=n, min_periods=n).min()
    hhv = high.rolling(window=n, min_periods=n).max()
    denom = (hhv - llv).replace(0, pd.NA)
    rsv = ((close - llv) / denom) * 100
    k = rsv.ewm(alpha=1 / 3, adjust=False, min_periods=n).mean()
    d = k.ewm(alpha=1 / 3, adjust=False, min_periods=n).mean()
    j = (3 * k) - (2 * d)
    return k, d, j


def _compute_boll(close: pd.Series, n: int = 20, k: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(window=n, min_periods=n).mean()
    std = close.rolling(window=n, min_periods=n).std()
    upper = mid + (k * std)
    lower = mid - (k * std)
    width = (upper - lower).replace(0, pd.NA)
    pctb = (close - lower) / width
    return mid, upper, lower, pctb


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=window, min_periods=window).mean()


def _detect_fractals(high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
    h = high.astype(float)
    l = low.astype(float)
    top = (
        (h.shift(2) < h)
        & (h.shift(1) < h)
        & (h.shift(-1) <= h)
        & (h.shift(-2) <= h)
    )
    bottom = (
        (l.shift(2) > l)
        & (l.shift(1) > l)
        & (l.shift(-1) >= l)
        & (l.shift(-2) >= l)
    )
    top = top.fillna(False)
    bottom = bottom.fillna(False)
    return top, bottom


def _build_timing_report(df: pd.DataFrame) -> dict:
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)
    dates = df["date"]

    last_date = dates.iloc[-1]
    last_close = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if df.shape[0] >= 2 else last_close
    change_pct = (last_close / prev_close - 1.0) if prev_close else 0.0

    ma20 = close.rolling(window=20, min_periods=20).mean()
    ma60 = close.rolling(window=60, min_periods=60).mean()
    ma120 = close.rolling(window=120, min_periods=120).mean()
    vma20 = volume.rolling(window=20, min_periods=20).mean()
    vol_ratio = (volume / vma20.replace(0, pd.NA)).fillna(pd.NA)

    atr_pct14 = _compute_atr_pct(high=high, low=low, close=close, window=14)
    atr20 = _compute_atr(high=high, low=low, close=close, window=20)

    dif, dea, hist = _compute_macd(close=close, fast=12, slow=26, signal=9)
    k, d, j = _compute_kdj(high=high, low=low, close=close, n=9)
    boll_mid, boll_up, boll_low, boll_pctb = _compute_boll(close=close, n=20, k=2.0)

    high20 = high.shift(1).rolling(window=20, min_periods=20).max()
    high55 = high.shift(1).rolling(window=55, min_periods=55).max()
    low10 = low.shift(1).rolling(window=10, min_periods=10).min()
    low20 = low.shift(1).rolling(window=20, min_periods=20).min()

    top_f, bottom_f = _detect_fractals(high=high, low=low)
    pivots = []
    for idx in df.index[top_f | bottom_f]:
        pivots.append(
            {
                "date": df.loc[idx, "date"],
                "type": "top" if bool(top_f.loc[idx]) else "bottom",
                "price": float(df.loc[idx, "high"] if bool(top_f.loc[idx]) else df.loc[idx, "low"]),
            }
        )
    last_pivots = pivots[-8:] if len(pivots) > 0 else []

    chan_trend = "range"
    last_fractal = None
    if last_pivots:
        last_fractal = {"type": last_pivots[-1]["type"], "date": last_pivots[-1]["date"].isoformat(), "price": last_pivots[-1]["price"]}
        bottoms = [p for p in last_pivots if p["type"] == "bottom"]
        tops = [p for p in last_pivots if p["type"] == "top"]
        if len(bottoms) >= 2 and len(tops) >= 2:
            if bottoms[-1]["price"] > bottoms[-2]["price"] and tops[-1]["price"] > tops[-2]["price"]:
                chan_trend = "up"
            elif bottoms[-1]["price"] < bottoms[-2]["price"] and tops[-1]["price"] < tops[-2]["price"]:
                chan_trend = "down"

    macd_divergence = False
    if len(last_pivots) >= 4:
        recent_bottoms = [p for p in last_pivots if p["type"] == "bottom"]
        if len(recent_bottoms) >= 2:
            b1, b2 = recent_bottoms[-2], recent_bottoms[-1]
            try:
                i1 = int(df.index[df["date"] == b1["date"]][0])
                i2 = int(df.index[df["date"] == b2["date"]][0])
                if b2["price"] < b1["price"] and float(hist.iloc[i2]) > float(hist.iloc[i1]):
                    macd_divergence = True
            except Exception:
                macd_divergence = False

    buy_reasons = []
    sell_reasons = []
    risk_controls = []

    last_ma20 = ma20.iloc[-1]
    last_ma60 = ma60.iloc[-1]
    last_vr = vol_ratio.iloc[-1] if len(vol_ratio) else pd.NA
    last_hist = hist.iloc[-1]
    last_k = k.iloc[-1]
    last_d = d.iloc[-1]
    last_pctb = boll_pctb.iloc[-1]
    last_atr_pct = atr_pct14.iloc[-1]

    trend_ok = pd.notna(last_ma20) and pd.notna(last_ma60) and (last_close > float(last_ma20)) and (float(last_ma20) > float(last_ma60))
    if trend_ok:
        buy_reasons.append("均线多头：收盘价 > MA20 > MA60")
    else:
        sell_reasons.append("均线转弱：未形成 收盘价 > MA20 > MA60")

    macd_strengthening = False
    if df.shape[0] >= 2 and pd.notna(last_hist) and pd.notna(hist.iloc[-2]):
        macd_strengthening = float(last_hist) > 0 and float(last_hist) >= float(hist.iloc[-2])
    if macd_strengthening:
        buy_reasons.append("MACD 动能增强：柱体为正且走强")
    elif pd.notna(last_hist) and float(last_hist) < 0:
        sell_reasons.append("MACD 动能偏弱：柱体为负")

    kdj_strengthening = False
    if df.shape[0] >= 2 and pd.notna(last_k) and pd.notna(last_d) and pd.notna(k.iloc[-2]):
        kdj_strengthening = float(last_k) > float(last_d) and float(last_k) >= float(k.iloc[-2])
    if kdj_strengthening:
        buy_reasons.append("KDJ 偏强：K > D 且 K 上行")
    elif pd.notna(last_k) and pd.notna(last_d) and float(last_k) < float(last_d):
        sell_reasons.append("KDJ 偏弱：K < D")

    if pd.notna(last_pctb):
        if float(last_pctb) > 0.8:
            buy_reasons.append("BOLL 偏强：价格靠近上轨（趋势强化可能）")
        elif float(last_pctb) < 0.2:
            sell_reasons.append("BOLL 偏弱：价格靠近下轨（弱势/超跌）")

    if pd.notna(high20.iloc[-1]) and last_close > float(high20.iloc[-1]):
        buy_reasons.append("海龟入场：突破前 20 日高点")
    if pd.notna(low10.iloc[-1]) and last_close < float(low10.iloc[-1]):
        sell_reasons.append("海龟止损/退出：跌破前 10 日低点")

    if chan_trend == "up":
        buy_reasons.append("缠论（简化）趋势：笔/分型结构偏上行")
    elif chan_trend == "down":
        sell_reasons.append("缠论（简化）趋势：笔/分型结构偏下行")
    else:
        risk_controls.append("缠论（简化）结构：可能处于震荡，降低仓位或等待确认")

    if macd_divergence:
        buy_reasons.append("MACD 底背离（简化）：创新低但动能回升")

    if pd.notna(last_vr):
        if float(last_vr) >= 1.5:
            buy_reasons.append("量能放大：成交量 / 20日均量 ≥ 1.5")
        elif float(last_vr) <= 0.7:
            risk_controls.append("量能偏弱：成交量显著低于均量，突破可信度降低")

    if pd.notna(last_atr_pct) and float(last_atr_pct) >= 8:
        risk_controls.append("波动较高：ATR% 偏大，建议更严止损/更小仓位")

    if pd.notna(atr20.iloc[-1]):
        n = float(atr20.iloc[-1])
        risk_controls.append(f"海龟风控参考：N(ATR20)≈{n:.3f}，可用 2N 作为初始止损距离")

    buy_bias = len(buy_reasons) >= 3 and len(sell_reasons) == 0
    sell_bias = len(sell_reasons) >= 2 and not buy_bias

    return {
        "as_of": last_date.isoformat(),
        "snapshot": {
            "close": last_close,
            "change_pct": float(change_pct),
            "volume": float(volume.iloc[-1]),
            "vol_ratio_20": float(last_vr) if pd.notna(last_vr) else None,
            "atr_pct_14": float(last_atr_pct) if pd.notna(last_atr_pct) else None,
        },
        "indicators": {
            "ma": {
                "ma20": float(last_ma20) if pd.notna(last_ma20) else None,
                "ma60": float(last_ma60) if pd.notna(last_ma60) else None,
                "ma120": float(ma120.iloc[-1]) if pd.notna(ma120.iloc[-1]) else None,
            },
            "macd": {
                "dif": float(dif.iloc[-1]) if pd.notna(dif.iloc[-1]) else None,
                "dea": float(dea.iloc[-1]) if pd.notna(dea.iloc[-1]) else None,
                "hist": float(last_hist) if pd.notna(last_hist) else None,
                "divergence": bool(macd_divergence),
            },
            "kdj": {
                "k": float(last_k) if pd.notna(last_k) else None,
                "d": float(last_d) if pd.notna(last_d) else None,
                "j": float(j.iloc[-1]) if pd.notna(j.iloc[-1]) else None,
            },
            "boll": {
                "mid": float(boll_mid.iloc[-1]) if pd.notna(boll_mid.iloc[-1]) else None,
                "upper": float(boll_up.iloc[-1]) if pd.notna(boll_up.iloc[-1]) else None,
                "lower": float(boll_low.iloc[-1]) if pd.notna(boll_low.iloc[-1]) else None,
                "pctb": float(last_pctb) if pd.notna(last_pctb) else None,
            },
            "turtle": {
                "high20": float(high20.iloc[-1]) if pd.notna(high20.iloc[-1]) else None,
                "high55": float(high55.iloc[-1]) if pd.notna(high55.iloc[-1]) else None,
                "low10": float(low10.iloc[-1]) if pd.notna(low10.iloc[-1]) else None,
                "low20": float(low20.iloc[-1]) if pd.notna(low20.iloc[-1]) else None,
            },
            "chanlun": {
                "trend": chan_trend,
                "last_fractal": last_fractal,
            },
        },
        "decision": {
            "buy_bias": bool(buy_bias),
            "sell_bias": bool(sell_bias),
            "buy_reasons": buy_reasons[:12],
            "sell_reasons": sell_reasons[:12],
            "risk_controls": risk_controls[:12],
            "notice": [
                "技术分析与交易系统无法保证不亏损；请结合风险承受能力与仓位管理",
                "该结果用于研究复盘，不构成任何投资建议",
            ],
        },
    }


def _summary_forward_returns(forward_returns: pd.Series) -> dict:
    s = forward_returns.dropna()
    if s.empty:
        return {"n": 0}
    s = s.astype(float)
    win_rate = float((s > 0).mean())
    return {
        "n": int(s.shape[0]),
        "win_rate": win_rate,
        "avg": float(s.mean()),
        "median": float(s.median()),
        "p10": float(s.quantile(0.10)),
        "p90": float(s.quantile(0.90)),
        "min": float(s.min()),
        "max": float(s.max()),
    }


def _build_signal_explanations(df: pd.DataFrame) -> list[dict]:
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)

    ma_fast = close.rolling(window=20, min_periods=20).mean()
    ma_slow = close.rolling(window=60, min_periods=60).mean()
    atr_pct = _compute_atr_pct(high=high, low=low, close=close, window=14)
    rsi14 = _compute_rsi(close=close, window=14)
    dif, dea, hist = _compute_macd(close=close, fast=12, slow=26, signal=9)
    k, d, j = _compute_kdj(high=high, low=low, close=close, n=9)
    boll_mid, boll_up, boll_low, boll_pctb = _compute_boll(close=close, n=20, k=2.0)

    s1_entry = (close > ma_fast) & (close.shift(1) <= ma_fast.shift(1)) & (ma_fast > ma_slow)

    high20 = close.shift(1).rolling(window=20, min_periods=20).max()
    vol_q80 = volume.rolling(window=60, min_periods=60).quantile(0.8)
    s2_entry = (close > high20) & (volume > vol_q80)

    s3_entry = (rsi14 < 30) & (rsi14.shift(1) >= 30)

    turtle_high20 = high.shift(1).rolling(window=20, min_periods=20).max()
    turtle_low10 = low.shift(1).rolling(window=10, min_periods=10).min()
    vma20 = volume.rolling(window=20, min_periods=20).mean()
    vol_ratio = (volume / vma20.replace(0, pd.NA))
    s5_entry = (
        (close > ma_fast)
        & (ma_fast > ma_slow)
        & (hist > 0)
        & (hist >= hist.shift(1))
        & (k > d)
        & (close > turtle_high20)
        & (vol_ratio >= 1.2)
    )

    templates = [
        ("S1", "趋势跟随", s1_entry),
        ("S2", "突破+成交量确认", s2_entry),
        ("S3", "均值回归（超卖）", s3_entry),
        ("S5", "多因子确认（海龟+均线+量价+MACD+KDJ）", s5_entry),
    ]

    horizons = [5, 10, 20]
    forward = {h: (close.shift(-h) / close - 1) for h in horizons}

    out = []
    last_row = df.iloc[-1]
    last_date = last_row["date"]
    last_close = float(last_row["close"])
    last_ma_fast = ma_fast.iloc[-1]
    last_ma_slow = ma_slow.iloc[-1]
    last_atr = atr_pct.iloc[-1]
    last_rsi = rsi14.iloc[-1]
    last_hist = hist.iloc[-1]
    last_k = k.iloc[-1]
    last_d = d.iloc[-1]
    last_pctb = boll_pctb.iloc[-1]
    last_turtle_high20 = turtle_high20.iloc[-1]
    last_turtle_low10 = turtle_low10.iloc[-1]
    last_vr = vol_ratio.iloc[-1] if len(vol_ratio) else pd.NA

    for template, name, entry in templates:
        entry_idx = df.index[entry.fillna(False)]
        last_trigger_date = None
        if len(entry_idx) > 0:
            last_trigger_date = df.loc[entry_idx[-1], "date"]

        triggered = bool(entry.fillna(False).iloc[-1])

        sample = {}
        for h in horizons:
            sample[str(h)] = _summary_forward_returns(forward[h][entry.fillna(False)])

        trigger_factors = []
        evidence = []
        risks = []
        invalidation = []

        if template == "S1":
            trigger_factors = [
                "收盘价上穿 MA20 且 MA20 > MA60",
                "仅作研究参考，不构成买卖建议",
            ]
            evidence = [
                f"收盘价: {last_close:.2f}",
                f"MA20: {float(last_ma_fast):.2f}" if pd.notna(last_ma_fast) else "MA20: -",
                f"MA60: {float(last_ma_slow):.2f}" if pd.notna(last_ma_slow) else "MA60: -",
                f"ATR% (14): {float(last_atr):.2f}%" if pd.notna(last_atr) else "ATR% (14): -",
            ]
            risks = [
                "震荡市容易出现反复止损/假突破",
                "短样本或低流动性标的统计不可靠",
            ]
            invalidation = [
                "收盘价跌破 MA20",
                "MA20 回落至 MA60 下方",
            ]
        elif template == "S2":
            trigger_factors = [
                "收盘价突破近 20 日高点",
                "成交量高于近 60 日的 80% 分位",
                "仅作研究参考，不构成买卖建议",
            ]
            evidence = [
                f"收盘价: {last_close:.2f}",
                f"近20日高点(前一日窗口): {float(high20.iloc[-1]):.2f}" if pd.notna(high20.iloc[-1]) else "近20日高点: -",
                f"成交量: {float(volume.iloc[-1]):.0f}",
                f"成交量80分位(60日): {float(vol_q80.iloc[-1]):.0f}" if pd.notna(vol_q80.iloc[-1]) else "成交量80分位: -",
            ]
            risks = [
                "假突破风险高，需关注回落与成交量衰减",
                "若处于高波动阶段，突破后的回撤可能显著",
            ]
            invalidation = [
                "价格回落至突破位下方并持续",
                "突破后成交量快速衰减且价格无延续",
            ]
        else:
            if template == "S3":
                trigger_factors = [
                    "RSI(14) 下穿 30（进入超卖区）",
                    "仅作研究参考，不构成买卖建议",
                ]
                evidence = [
                    f"收盘价: {last_close:.2f}",
                    f"RSI(14): {float(last_rsi):.2f}" if pd.notna(last_rsi) else "RSI(14): -",
                    f"ATR% (14): {float(last_atr):.2f}%" if pd.notna(last_atr) else "ATR% (14): -",
                ]
                risks = [
                    "单边下跌中容易越抄越亏（环境不适配）",
                    "极端事件驱动下技术指标可能失效",
                ]
                invalidation = [
                    "价格继续创新低且波动率上升",
                    "RSI 长时间滞留低位且无企稳迹象",
                ]
            else:
                trigger_factors = [
                    "海龟：突破前 20 日高点（趋势入场）",
                    "均线：收盘价 > MA20 > MA60（趋势过滤）",
                    "量价：成交量 / 20日均量 ≥ 1.2（确认）",
                    "MACD：柱体为正且走强（动能确认）",
                    "KDJ：K > D（短周期确认）",
                    "仅作研究参考，不构成买卖建议",
                ]
                evidence = [
                    f"收盘价: {last_close:.2f}",
                    f"MA20: {float(last_ma_fast):.2f}" if pd.notna(last_ma_fast) else "MA20: -",
                    f"MA60: {float(last_ma_slow):.2f}" if pd.notna(last_ma_slow) else "MA60: -",
                    f"成交量/均量20: {float(last_vr):.2f}" if pd.notna(last_vr) else "成交量/均量20: -",
                    f"MACD柱: {float(last_hist):.4f}" if pd.notna(last_hist) else "MACD柱: -",
                    f"KDJ(K/D): {float(last_k):.1f}/{float(last_d):.1f}" if pd.notna(last_k) and pd.notna(last_d) else "KDJ(K/D): -",
                    f"BOLL%: {float(last_pctb):.2f}" if pd.notna(last_pctb) else "BOLL%: -",
                    f"海龟高20: {float(last_turtle_high20):.2f}" if pd.notna(last_turtle_high20) else "海龟高20: -",
                    f"海龟低10: {float(last_turtle_low10):.2f}" if pd.notna(last_turtle_low10) else "海龟低10: -",
                ]
                risks = [
                    "突破策略在震荡阶段容易出现假突破",
                    "多因子越多越可能降低触发频率，需关注样本数量",
                    "强趋势末端追高可能导致回撤扩大",
                ]
                invalidation = [
                    "跌破前 10 日低点（海龟退出参考）",
                    "收盘价跌破 MA20 或 MACD 柱转负",
                ]

        risk_level = "L1"
        if pd.notna(last_atr) and float(last_atr) >= 6:
            risk_level = "L2"
        if df.shape[0] < 120:
            risk_level = "L2"

        out.append(
            {
                "template": template,
                "name": name,
                "as_of": last_date.isoformat(),
                "status": "triggered" if triggered else "inactive",
                "risk_level": risk_level,
                "last_trigger_date": last_trigger_date.isoformat() if last_trigger_date is not None else None,
                "trigger_factors": trigger_factors,
                "evidence": evidence,
                "similar_samples": {
                    "horizons": sample,
                },
                "risks": risks,
                "invalidation": invalidation,
            }
        )
    return out


class SignalExplainView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        symbol = request.query_params.get("symbol")
        if not symbol:
            return Response({"status": "error", "message": "Missing symbol"}, status=400)

        raw_symbol = str(symbol).split(".")[0]
        end_date = datetime.datetime.now().date()
        start_date = end_date - datetime.timedelta(days=900)
        start_date_str = start_date.strftime("%Y%m%d")

        cache_key = f"signals:{request.user.id}:{symbol}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"status": "success", "data": cached})

        try:
            df = ak.stock_zh_a_hist(symbol=raw_symbol, period="daily", start_date=start_date_str, adjust="qfq")
        except Exception as e:
            return Response({"status": "error", "message": f"Data fetch failed: {str(e)}"}, status=500)

        if df is None or df.empty:
            return Response({"status": "error", "message": "No data"}, status=404)

        date_col = "日期" if "日期" in df.columns else ("date" if "date" in df.columns else None)
        if not date_col:
            return Response({"status": "error", "message": "Unsupported data format"}, status=500)

        col_map = {
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "volume": "成交量",
        }
        missing = [k for k, v in col_map.items() if v not in df.columns]
        if missing:
            return Response({"status": "error", "message": "Missing columns"}, status=500)

        work = df[[date_col, col_map["open"], col_map["close"], col_map["high"], col_map["low"], col_map["volume"]]].copy()
        work.rename(
            columns={
                date_col: "date",
                col_map["open"]: "open",
                col_map["close"]: "close",
                col_map["high"]: "high",
                col_map["low"]: "low",
                col_map["volume"]: "volume",
            },
            inplace=True,
        )
        work["date"] = pd.to_datetime(work["date"]).dt.date
        work.sort_values("date", inplace=True)
        work.dropna(subset=["close", "high", "low", "volume"], inplace=True)
        if work.shape[0] < 80:
            return Response({"status": "error", "message": "Not enough data"}, status=422)

        signals = _build_signal_explanations(work)
        timing_report = _build_timing_report(work)
        payload = {"symbol": symbol, "signals": signals, "timing_report": timing_report}
        cache.set(cache_key, payload, 30)
        return Response({"status": "success", "data": payload})


def _parse_date(value: str | None):
    if not value:
        return None
    v = str(value).strip()
    if not v:
        return None
    try:
        if len(v) == 8 and v.isdigit():
            return datetime.datetime.strptime(v, "%Y%m%d").date()
        return datetime.date.fromisoformat(v[:10])
    except Exception:
        return None


def _max_drawdown(equity: pd.Series) -> float:
    s = equity.dropna().astype(float)
    if s.empty:
        return 0.0
    peak = s.cummax()
    dd = (s / peak) - 1.0
    return float(dd.min())


def _sharpe_ratio(daily_returns: pd.Series) -> float:
    r = daily_returns.dropna().astype(float)
    if r.empty:
        return 0.0
    vol = float(r.std())
    if vol == 0.0:
        return 0.0
    return float((r.mean() / vol) * (252 ** 0.5))


def _build_daily_ohlcv(raw_symbol: str, start_date: datetime.date | None, end_date: datetime.date | None):
    today = datetime.datetime.now().date()
    s = start_date or (today - datetime.timedelta(days=1100))
    start_str = s.strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(symbol=raw_symbol, period="daily", start_date=start_str, adjust="qfq")
    if df is None or df.empty:
        return None

    date_col = "日期" if "日期" in df.columns else ("date" if "date" in df.columns else None)
    if not date_col:
        return None

    col_map = {
        "open": "开盘",
        "close": "收盘",
        "high": "最高",
        "low": "最低",
        "volume": "成交量",
    }
    for v in col_map.values():
        if v not in df.columns:
            return None

    work = df[[date_col, col_map["open"], col_map["high"], col_map["low"], col_map["close"], col_map["volume"]]].copy()
    work.rename(
        columns={
            date_col: "date",
            col_map["open"]: "open",
            col_map["high"]: "high",
            col_map["low"]: "low",
            col_map["close"]: "close",
            col_map["volume"]: "volume",
        },
        inplace=True,
    )
    work["date"] = pd.to_datetime(work["date"]).dt.date
    work.sort_values("date", inplace=True)
    work.dropna(subset=["open", "high", "low", "close"], inplace=True)
    if end_date:
        work = work[work["date"] <= end_date]
    if start_date:
        work = work[work["date"] >= start_date]
    if work.empty:
        return None
    return work.reset_index(drop=True)


def _generate_signals(df: pd.DataFrame, template: str, params: dict) -> tuple[pd.Series, pd.Series]:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    high = df["high"].astype(float) if "high" in df.columns else close
    low = df["low"].astype(float) if "low" in df.columns else close
    if template == "S1":
        ma_fast = int(params.get("ma_fast", 20))
        ma_slow = int(params.get("ma_slow", 60))
        fast = close.rolling(window=ma_fast, min_periods=ma_fast).mean()
        slow = close.rolling(window=ma_slow, min_periods=ma_slow).mean()
        entry = (close > fast) & (close.shift(1) <= fast.shift(1)) & (fast > slow)
        exit_ = (close < fast)
        return entry, exit_
    if template == "S2":
        breakout_n = int(params.get("breakout_n", 20))
        vol_window = int(params.get("vol_window", 60))
        vol_quantile = float(params.get("vol_quantile", 0.8))
        high_n = close.shift(1).rolling(window=breakout_n, min_periods=breakout_n).max()
        vol_q = volume.rolling(window=vol_window, min_periods=vol_window).quantile(vol_quantile)
        entry = (close > high_n) & (volume > vol_q)
        exit_ = close < close.rolling(window=10, min_periods=10).mean()
        return entry, exit_
    if template == "S3":
        rsi_window = int(params.get("rsi_window", 14))
        rsi_entry = float(params.get("rsi_entry", 30))
        rsi_exit = float(params.get("rsi_exit", 50))
        rsi = _compute_rsi(close=close, window=rsi_window)
        entry = (rsi < rsi_entry) & (rsi.shift(1) >= rsi_entry)
        exit_ = rsi >= rsi_exit
        return entry, exit_
    if template == "S5":
        entry_n = int(params.get("entry_n", 20))
        exit_n = int(params.get("exit_n", 10))
        ma_fast = int(params.get("ma_fast", 20))
        ma_slow = int(params.get("ma_slow", 60))
        vol_ratio_th = float(params.get("vol_ratio_th", 1.2))
        atr_pct_max = float(params.get("atr_pct_max", 10.0))

        fast_ma = close.rolling(window=ma_fast, min_periods=ma_fast).mean()
        slow_ma = close.rolling(window=ma_slow, min_periods=ma_slow).mean()
        dif, dea, hist = _compute_macd(close=close, fast=12, slow=26, signal=9)
        k, d, j = _compute_kdj(high=high, low=low, close=close, n=9)

        vma20 = volume.rolling(window=20, min_periods=20).mean()
        vol_ratio = (volume / vma20.replace(0, pd.NA))
        atr_pct14 = _compute_atr_pct(high=high, low=low, close=close, window=14)

        breakout_high = high.shift(1).rolling(window=entry_n, min_periods=entry_n).max()
        exit_low = low.shift(1).rolling(window=exit_n, min_periods=exit_n).min()

        entry = (
            (close > breakout_high)
            & (close > fast_ma)
            & (fast_ma > slow_ma)
            & (hist > 0)
            & (hist >= hist.shift(1))
            & (k > d)
            & (vol_ratio >= vol_ratio_th)
            & (atr_pct14 <= atr_pct_max)
        )
        exit_ = (close < exit_low) | (close < fast_ma) | (hist < 0)
        return entry, exit_
    raise ValueError("Unsupported template")


def _event_effective_dates(
    user_id: int,
    symbol: str,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    event_types: list[str] | None,
    license_whitelist: list[str] | None,
) -> set[datetime.date]:
    qs = Event.objects.filter(user_id=user_id, symbol=symbol)
    if event_types:
        qs = qs.filter(event_type__in=event_types)

    if start_date:
        qs = qs.filter(market_effective_time__date__gte=start_date)
    if end_date:
        qs = qs.filter(market_effective_time__date__lte=end_date)

    allowed = set((license_whitelist or ["unknown", "ok", "licensed"]))
    out: set[datetime.date] = set()
    for ev in qs.only("market_effective_time", "license_status"):
        status = (ev.license_status or "unknown").strip() or "unknown"
        if status not in allowed:
            continue
        if ev.market_effective_time:
            out.add(ev.market_effective_time.date())
    return out


def _run_backtest_daily(
    df: pd.DataFrame,
    template: str,
    params: dict,
    initial_cash: float,
    commission_rate: float,
    stamp_duty_rate: float,
    slippage_bps: float,
    lot_size: int,
    event_entry_dates: set[datetime.date] | None = None,
):
    if template != "S4":
        entry_sig, exit_sig = _generate_signals(df=df, template=template, params=params)
        entry_sig = entry_sig.fillna(False)
        exit_sig = exit_sig.fillna(False)
    else:
        dates = df["date"]
        entry_sig = dates.apply(lambda d: d in (event_entry_dates or set()))
        exit_sig = pd.Series([False] * len(df))

    cash = float(initial_cash)
    shares = 0
    entry_price = None
    entry_date = None
    hold_remaining = None

    equity_rows = []
    trades = []

    def exec_buy(price: float, date_val):
        nonlocal cash, shares, entry_price, entry_date
        exec_price = price * (1.0 + (slippage_bps / 10000.0))
        max_shares = int(cash / (exec_price * (1.0 + commission_rate)))
        if lot_size > 1:
            max_shares = (max_shares // lot_size) * lot_size
        if max_shares <= 0:
            return
        cost = exec_price * max_shares
        fee = cost * commission_rate
        cash = cash - cost - fee
        shares = max_shares
        entry_price = exec_price
        entry_date = date_val

    def exec_sell(price: float, date_val):
        nonlocal cash, shares, entry_price, entry_date
        if shares <= 0:
            return
        exec_price = price * (1.0 - (slippage_bps / 10000.0))
        proceeds = exec_price * shares
        fee = proceeds * commission_rate
        tax = proceeds * stamp_duty_rate
        cash = cash + proceeds - fee - tax
        pnl = None
        ret = None
        if entry_price is not None:
            pnl = (exec_price - entry_price) * shares - fee - tax
            ret = (exec_price / entry_price) - 1.0
        trades.append(
            {
                "entry_date": entry_date.isoformat() if entry_date is not None else None,
                "entry_price": float(entry_price) if entry_price is not None else None,
                "exit_date": date_val.isoformat(),
                "exit_price": float(exec_price),
                "shares": int(shares),
                "pnl": float(pnl) if pnl is not None else None,
                "return_pct": float(ret) if ret is not None else None,
            }
        )
        shares = 0
        entry_price = None
        entry_date = None

    for i in range(len(df)):
        row = df.iloc[i]
        date_val = row["date"]
        o = float(row["open"])
        c = float(row["close"])
        position_value = float(shares) * c
        equity = cash + position_value
        equity_rows.append(
            {
                "date": date_val.isoformat(),
                "equity": float(equity),
                "cash": float(cash),
                "position_value": float(position_value),
                "shares": int(shares),
            }
        )

        if i + 1 >= len(df):
            continue
        next_open = float(df.iloc[i + 1]["open"])
        next_date = df.iloc[i + 1]["date"]

        if template == "S4" and shares > 0 and hold_remaining is not None:
            hold_remaining = int(hold_remaining) - 1
            if hold_remaining <= 0:
                exec_sell(price=next_open, date_val=next_date)
                hold_remaining = None
                continue

        if shares > 0 and bool(exit_sig.iloc[i]):
            exec_sell(price=next_open, date_val=next_date)
            continue

        if shares == 0 and bool(entry_sig.iloc[i]):
            exec_buy(price=next_open, date_val=next_date)
            if template == "S4":
                try:
                    hold_days = int(params.get("hold_days", 5))
                except Exception:
                    hold_days = 5
                hold_remaining = max(1, hold_days)

    if shares > 0:
        last = df.iloc[-1]
        exec_sell(price=float(last["close"]), date_val=last["date"])

    equity_df = pd.DataFrame(equity_rows)
    equity_series = equity_df["equity"].astype(float)
    daily_returns = equity_series.pct_change()
    dd = _max_drawdown(equity_series)
    total_return = float(equity_series.iloc[-1] / float(initial_cash) - 1.0) if len(equity_series) else 0.0
    n_days = int(equity_series.shape[0])
    cagr = float((1.0 + total_return) ** (252.0 / n_days) - 1.0) if n_days > 0 else 0.0
    sharpe = _sharpe_ratio(daily_returns=daily_returns)
    calmar = float(cagr / abs(dd)) if dd != 0 else 0.0

    trade_returns = pd.Series([t.get("return_pct") for t in trades if t.get("return_pct") is not None], dtype=float)
    win_rate = float((trade_returns > 0).mean()) if not trade_returns.empty else 0.0

    metrics = {
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": dd,
        "sharpe": sharpe,
        "calmar": calmar,
        "trades": int(len(trades)),
        "win_rate": win_rate,
        "end_equity": float(equity_series.iloc[-1]) if len(equity_series) else float(initial_cash),
    }
    return metrics, equity_rows, trades


def _metrics_from_equity_rows(
    equity_rows: list[dict],
    base_equity: float,
):
    if not equity_rows:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "calmar": 0.0,
            "end_equity": float(base_equity),
            "days": 0,
        }

    equity_series = pd.Series([float(r.get("equity", 0.0)) for r in equity_rows], dtype=float)
    daily_returns = equity_series.pct_change()
    dd = _max_drawdown(equity_series)
    end_equity = float(equity_series.iloc[-1])
    total_return = float(end_equity / float(base_equity) - 1.0) if base_equity else 0.0
    n_days = int(equity_series.shape[0])
    cagr = float((1.0 + total_return) ** (252.0 / n_days) - 1.0) if n_days > 0 else 0.0
    sharpe = _sharpe_ratio(daily_returns=daily_returns)
    calmar = float(cagr / abs(dd)) if dd != 0 else 0.0
    return {
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": dd,
        "sharpe": sharpe,
        "calmar": calmar,
        "end_equity": end_equity,
        "days": n_days,
    }


class BacktestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        symbol = (request.data or {}).get("symbol")
        template = ((request.data or {}).get("template") or "S1").strip()
        params = (request.data or {}).get("params") or {}

        if not symbol:
            return Response({"status": "error", "message": "Missing symbol"}, status=400)

        start_date = _parse_date((request.data or {}).get("start_date"))
        end_date = _parse_date((request.data or {}).get("end_date"))
        oos_start_date = _parse_date((request.data or {}).get("oos_start_date"))
        if (request.data or {}).get("start_date") and start_date is None:
            return Response({"status": "error", "message": "Invalid start_date"}, status=400)
        if (request.data or {}).get("end_date") and end_date is None:
            return Response({"status": "error", "message": "Invalid end_date"}, status=400)
        if (request.data or {}).get("oos_start_date") and oos_start_date is None:
            return Response({"status": "error", "message": "Invalid oos_start_date"}, status=400)

        try:
            initial_cash = float((request.data or {}).get("initial_cash") or 100000.0)
            commission_rate = float((request.data or {}).get("commission_rate") or 0.0003)
            stamp_duty_rate = float((request.data or {}).get("stamp_duty_rate") or 0.001)
            slippage_bps = float((request.data or {}).get("slippage_bps") or 5.0)
            lot_size = int((request.data or {}).get("lot_size") or 100)
        except Exception:
            return Response({"status": "error", "message": "Invalid numeric parameters"}, status=400)

        raw_symbol = str(symbol).split(".")[0]
        try:
            df = _build_daily_ohlcv(raw_symbol=raw_symbol, start_date=start_date, end_date=end_date)
        except Exception as e:
            return Response({"status": "error", "message": f"Data fetch failed: {str(e)}"}, status=500)

        if df is None or df.empty or df.shape[0] < 120:
            return Response({"status": "error", "message": "Not enough data"}, status=422)

        event_dates = None
        if template == "S4":
            raw_types = params.get("event_types") or params.get("event_type")
            event_types = None
            if isinstance(raw_types, str) and raw_types.strip():
                event_types = [raw_types.strip()]
            elif isinstance(raw_types, list):
                event_types = [str(x).strip() for x in raw_types if str(x).strip()]

            raw_whitelist = params.get("license_whitelist")
            license_whitelist = None
            if isinstance(raw_whitelist, list):
                license_whitelist = [str(x).strip() for x in raw_whitelist if str(x).strip()]

            try:
                event_dates = _event_effective_dates(
                    user_id=request.user.id,
                    symbol=str(symbol),
                    start_date=start_date,
                    end_date=end_date,
                    event_types=event_types,
                    license_whitelist=license_whitelist,
                )
            except Exception as e:
                return Response({"status": "error", "message": f"Event fetch failed: {str(e)}"}, status=500)

        try:
            metrics, equity_curve, trades = _run_backtest_daily(
                df=df,
                template=template,
                params=params,
                initial_cash=initial_cash,
                commission_rate=commission_rate,
                stamp_duty_rate=stamp_duty_rate,
                slippage_bps=slippage_bps,
                lot_size=lot_size,
                event_entry_dates=event_dates,
            )
        except ValueError as e:
            return Response({"status": "error", "message": str(e)}, status=400)
        except Exception as e:
            return Response({"status": "error", "message": f"Backtest failed: {str(e)}"}, status=500)

        if oos_start_date is None and df.shape[0] >= 252:
            oos_start_date = df.iloc[-252]["date"]

        equity_df = pd.DataFrame(equity_curve)
        in_sample_metrics = None
        out_of_sample_metrics = None
        split_info = None
        if oos_start_date is not None and not equity_df.empty:
            split_info = {"oos_start_date": oos_start_date.isoformat()}
            in_df = equity_df[equity_df["date"] < oos_start_date.isoformat()]
            oos_df = equity_df[equity_df["date"] >= oos_start_date.isoformat()]

            in_rows = in_df.to_dict(orient="records")
            oos_rows = oos_df.to_dict(orient="records")

            in_base = float(initial_cash)
            if in_rows:
                in_base = float(initial_cash)
            oos_base = float(in_rows[-1]["equity"]) if in_rows else float(initial_cash)

            in_sample_metrics = _metrics_from_equity_rows(in_rows, base_equity=in_base)
            out_of_sample_metrics = _metrics_from_equity_rows(oos_rows, base_equity=oos_base)

        warnings = []
        maxdd = float(metrics.get("max_drawdown") or 0.0)
        if abs(maxdd) > 0.25:
            warnings.append({"level": "L3", "code": "max_drawdown_exceeded", "message": "最大回撤超过 25%，不满足验证门槛"})

        if int(metrics.get("trades") or 0) < 20:
            warnings.append({"level": "L2", "code": "too_few_trades", "message": "交易次数偏少，统计可靠性较弱"})

        if out_of_sample_metrics is not None and in_sample_metrics is not None:
            oos_sharpe = float(out_of_sample_metrics.get("sharpe") or 0.0)
            ins_sharpe = float(in_sample_metrics.get("sharpe") or 0.0)
            if ins_sharpe > 0 and oos_sharpe < ins_sharpe * 0.5:
                warnings.append({"level": "L2", "code": "oos_degraded", "message": "样本外表现显著变差，存在反过拟合风险"})

        rule_draft = {
            "symbol": symbol,
            "template": template,
            "params": params,
            "execution": {
                "frequency": "daily",
                "order": "next_open",
                "lot_size": lot_size,
                "commission_rate": commission_rate,
                "stamp_duty_rate": stamp_duty_rate,
                "slippage_bps": slippage_bps,
            },
            "validation": {
                "max_drawdown_threshold": 0.25,
                "min_trades": 20,
                "oos_start_date": split_info.get("oos_start_date") if split_info else None,
            },
        }

        payload = {
            "config": {
                "symbol": symbol,
                "template": template,
                "params": params,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "oos_start_date": oos_start_date.isoformat() if oos_start_date else None,
                "initial_cash": initial_cash,
                "commission_rate": commission_rate,
                "stamp_duty_rate": stamp_duty_rate,
                "slippage_bps": slippage_bps,
                "lot_size": lot_size,
            },
            "metrics": metrics,
            "evaluation": {
                "split": split_info,
                "in_sample": in_sample_metrics,
                "out_of_sample": out_of_sample_metrics,
                "warnings": warnings,
            },
            "rule_draft": rule_draft,
            "equity_curve": equity_curve,
            "trades": trades,
        }
        return Response({"status": "success", "data": payload})


class EventView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        symbol = request.query_params.get('symbol')
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if not symbol:
            return Response({"status": "error", "message": "Missing symbol"}, status=400)

        qs = Event.objects.filter(user_id=request.user.id, symbol=symbol)

        start_dt = parse_datetime(start) if start else None
        end_dt = parse_datetime(end) if end else None
        if start and start_dt is None:
            return Response({"status": "error", "message": "Invalid start datetime"}, status=400)
        if end and end_dt is None:
            return Response({"status": "error", "message": "Invalid end datetime"}, status=400)

        if start_dt:
            qs = qs.filter(market_effective_time__gte=start_dt)
        if end_dt:
            qs = qs.filter(market_effective_time__lte=end_dt)

        data = EventSerializer(qs[:500], many=True).data
        return Response({"status": "success", "data": data})

    def post(self, request):
        payload = dict(request.data or {})
        payload["user_id"] = request.user.id
        serializer = EventSerializer(data=payload)
        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=400)
        ev = Event.objects.create(
            user_id=request.user.id,
            symbol=serializer.validated_data["symbol"],
            title=serializer.validated_data["title"],
            event_type=serializer.validated_data.get("event_type"),
            source=serializer.validated_data.get("source"),
            source_url=serializer.validated_data.get("source_url"),
            license_status=serializer.validated_data.get("license_status"),
            evidence=serializer.validated_data.get("evidence"),
            event_time=serializer.validated_data["event_time"],
            market_effective_time=serializer.validated_data["market_effective_time"],
        )
        return Response({"status": "success", "data": EventSerializer(ev).data}, status=201)
